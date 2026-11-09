"""Stage 11: which pull request files to review, which lines changed, and
which findings to keep. Pure functions: no network, database or AI calls.
"""
import re
from pathlib import PurePosixPath

# Findings this many lines from a changed line still count as inside the diff
# (AI line numbers can be off by one).
LINE_TOLERANCE = 1
# Findings outside the diff are kept only if this severe, and only this many per file.
OUTSIDE_DIFF_SEVERITIES = {"high", "medium"}
MAX_OUTSIDE_DIFF_PER_FILE = 2
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Values match frontend/src/constants/languages.js (code_reviews.programming_language).
EXTENSION_LANGUAGES = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
}

GENERATED_FILE_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock",
    "cargo.lock", "composer.lock", "gemfile.lock", "go.sum", "uv.lock",
}
GENERATED_DIRECTORIES = {"dist", "build", "vendor", "node_modules", "__pycache__", ".next", "coverage"}
GENERATED_SUFFIXES = (".min.js", ".min.css", ".map", "_pb2.py", ".pb.go", ".generated.ts", ".generated.js")

_HUNK_HEADER = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def changed_lines(patch: str | None) -> set[int]:
    """New-file line numbers of added lines, plus where removed lines used to be."""
    lines: set[int] = set()
    current = None
    for row in (patch or "").splitlines():
        header = _HUNK_HEADER.match(row)
        if header:
            current = int(header.group(1))
            continue
        if current is None or row.startswith("\\"):
            continue
        if row.startswith("+"):
            lines.add(current)
            current += 1
        elif row.startswith("-"):
            lines.add(current)
        else:
            current += 1
    return lines


def language_for_path(path: str) -> str | None:
    return EXTENSION_LANGUAGES.get(PurePosixPath(path).suffix.lower())


def _is_generated(path: str) -> bool:
    pure = PurePosixPath(path.lower())
    return (
        pure.name in GENERATED_FILE_NAMES
        or any(part in GENERATED_DIRECTORIES for part in pure.parts[:-1])
        or pure.name.endswith(GENERATED_SUFFIXES)
    )


def skip_reason(changed_file: dict) -> str | None:
    """Why a changed file won't be reviewed, or None if it should be."""
    if changed_file["status"] == "removed":
        return "removed"
    if _is_generated(changed_file["path"]):
        return "generated"
    if not changed_file.get("patch"):
        # GitHub omits the patch for binary files and for very large diffs.
        changes = changed_file.get("additions", 0) + changed_file.get("deletions", 0)
        return "too_large" if changes else "binary"
    if language_for_path(changed_file["path"]) is None:
        return "unsupported"
    return None


def focus_findings(issues: list[dict], changed: set[int]) -> list[dict]:
    """Keep findings on changed lines; keep a few serious ones elsewhere, labeled.

    Returns new dicts with ``outside_diff`` set. Inside-the-diff findings keep
    their order; outside ones follow, most severe first.
    """
    inside, outside = [], []
    for issue in issues:
        line = issue.get("line_number")
        near = isinstance(line, int) and any(abs(line - number) <= LINE_TOLERANCE for number in changed)
        if near:
            inside.append({**issue, "outside_diff": False})
        elif issue.get("severity") in OUTSIDE_DIFF_SEVERITIES:
            outside.append({**issue, "outside_diff": True})
    outside.sort(key=lambda issue: _SEVERITY_RANK.get(issue.get("severity"), 3))
    return inside + outside[:MAX_OUTSIDE_DIFF_PER_FILE]
