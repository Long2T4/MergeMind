"""Collect direct local dependencies from caller-supplied project files.

No source code is executed and no files or URLs are opened. This service is
independent of GitHub and the AI provider so both can use it later.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping


JS_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
# Keep strings/templates opaque and discard comments before looking for import
# keywords. In particular, an example import inside a string is not an import.
JS_TOKENS = re.compile(
    r'''//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|[\w$]+|[^\s]'''
)


@dataclass(frozen=True)
class ContextFile:
    path: str
    content: str


@dataclass(frozen=True)
class ProjectContext:
    files: tuple[ContextFile, ...]
    unresolved_imports: tuple[str, ...]
    omitted_files: tuple[str, ...]

    @property
    def total_chars(self) -> int:
        return sum(len(file.content) for file in self.files)


def _project_path(path: str) -> str:
    """Accept only non-empty, repository-relative paths, with POSIX separators."""
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("Project paths must be non-empty strings without null bytes")
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if normalized.startswith("/") or ":" in parts[0] or ".." in parts:
        raise ValueError("Project paths must be relative and cannot contain '..'")
    result = str(PurePosixPath(normalized))
    if result == ".":
        raise ValueError("Project paths must name a file or directory")
    return result


def _python_imports(path: str, code: str, source_root: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Unfinished code is common during review. Do not guess its imports.
        return
    imports = sorted(
        (node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))),
        key=lambda node: (node.lineno, node.col_offset),
    )
    root = PurePosixPath(source_root)
    for node in imports:
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = root.joinpath(*alias.name.split("."))
                yield alias.name, [f"{base}.py", f"{base}/__init__.py"]
            continue
        if node.level:
            parents = PurePosixPath(path).parent.parts
            # A relative import cannot climb above the configured source root.
            if len(parents) - node.level + 1 < len(root.parts):
                yield "." * node.level + (node.module or ""), []
                continue
            base = PurePosixPath(*parents[:len(parents) - node.level + 1])
        else:
            base = root
        if node.module:
            base = base.joinpath(*node.module.split("."))
        for alias in node.names:
            label = "." * node.level + (node.module or "")
            label += f" import {alias.name}"
            candidates = []
            if alias.name != "*":
                child = base / alias.name
                candidates.extend([f"{child}.py", f"{child}/__init__.py"])
            if node.module:
                candidates.extend([f"{base}.py", f"{base}/__init__.py"])
            yield label, candidates


def _js_specifiers(code: str):
    tokens = [token for token in JS_TOKENS.findall(code) if not token.startswith(("//", "/*"))]

    def quoted(token):
        # Escaped module specifiers and template literals are deliberately not
        # resolved. These are static path hints, not a JavaScript interpreter.
        return len(token) >= 2 and token[0] in "\"'" and "\\" not in token

    for index, token in enumerate(tokens):
        following = tokens[index + 1: index + 5]
        if index and tokens[index - 1] == ".":
            continue
        if token == "require" and len(following) >= 3:
            if following[0] == "(" and quoted(following[1]) and following[2] == ")":
                yield following[1][1:-1]
        elif token in {"import", "export"} and following:
            if token == "import" and quoted(following[0]):
                yield following[0][1:-1]
            elif following[0] != "(" and (token == "import" or following[0] in {"{", "*", "type"}):
                for cursor in range(index + 1, len(tokens) - 1):
                    if tokens[cursor] in {";", "import", "export"}:
                        break
                    if tokens[cursor] == "from" and quoted(tokens[cursor + 1]):
                        yield tokens[cursor + 1][1:-1]
                        break


def _js_imports(path: str, code: str):
    for specifier in _js_specifiers(code):
        if not specifier.startswith(("./", "../")):
            continue  # npm packages and aliases require caller/build configuration.
        parts = list(PurePosixPath(path).parent.parts)
        for part in specifier.split("/"):
            if part == "..":
                if not parts:
                    parts = None
                    break
                parts.pop()
            elif part not in {"", "."}:
                parts.append(part)
        if not parts:
            yield specifier, []
            continue
        base = PurePosixPath(*parts)
        if base.suffix:
            candidates = [str(base)] if base.suffix in JS_EXTENSIONS else []
        else:
            extensions = JS_EXTENSIONS
            if PurePosixPath(path).suffix in {".ts", ".tsx"}:
                extensions = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
            candidates = [f"{base}{extension}" for extension in extensions]
            candidates += [f"{base}/index{extension}" for extension in extensions]
        yield specifier, candidates


def collect_project_context(
    file_path: str,
    source_code: str,
    project_files: Mapping[str, str],
    *,
    source_root: str = "",
    max_files: int = 8,
    max_chars: int = 24_000,
) -> ProjectContext:
    """Select complete directly imported files, in source import order.

    ``source_root`` is the Python import root relative to the repository (for
    example ``backend``). Unresolved Python imports can also be external
    packages: they are diagnostics, not proof that a dependency is missing.
    Oversized files are omitted whole so the caller never receives cut code.
    The character budget counts file contents, not future prompt formatting.
    """
    path = _project_path(file_path)
    root = _project_path(source_root) if source_root else ""
    if not isinstance(source_code, str):
        raise ValueError("Source code must be text")
    if root and not path.startswith(root + "/"):
        raise ValueError("The reviewed file must be inside source_root")
    for limit in (max_files, max_chars):
        if type(limit) is not int or limit < 1:
            raise ValueError("Context limits must be positive integers")

    supplied = {}
    for name, content in project_files.items():
        name = _project_path(name)
        if not isinstance(content, str):
            raise ValueError("Project file contents must be text")
        if name in supplied:
            raise ValueError(f"Duplicate normalized project path: {name}")
        supplied[name] = content

    suffix = PurePosixPath(path).suffix
    if suffix == ".py":
        imports = _python_imports(path, source_code, root)
    elif suffix in JS_EXTENSIONS:
        imports = _js_imports(path, source_code)
    else:
        raise ValueError("Supported source files are Python, JavaScript and TypeScript")

    selected, unresolved, omitted = [], [], []
    seen = {path}
    remaining = max_chars
    for label, candidates in imports:
        match = next((candidate for candidate in candidates if candidate in supplied), None)
        if match is None:
            if label not in unresolved:
                unresolved.append(label)
            continue
        if match in seen:
            continue
        seen.add(match)
        content = supplied[match]
        if len(selected) >= max_files or len(content) > remaining:
            omitted.append(match)
            continue
        selected.append(ContextFile(match, content))
        remaining -= len(content)
    return ProjectContext(tuple(selected), tuple(unresolved), tuple(omitted))
