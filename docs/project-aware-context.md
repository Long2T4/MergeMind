# Project-aware context collector

The backend now has a standalone context collector for Akhil's originally
assigned Stage 9, Project-Aware Review. It selects the contents of directly
imported local modules from a caller-supplied project snapshot. For example,
reviewing a route that imports a database model can also provide that model
as context instead of reviewing the route in isolation.

This is the context-collection foundation, not a completed project-aware AI
review flow. The existing API and frontend still submit one code snippet to
the AI. Connecting this collector to those inputs and the AI prompt remains
separate work. There are no API, database, UI or provider changes in this task.

## Run an example

From `backend/`, using the project's Python environment:

```python
from app.services.project_context_service import collect_project_context

context = collect_project_context(
    file_path="backend/app/routes/users.py",
    source_code="from app.models import User\n",
    project_files={
        "backend/app/models.py": "class User:\n    name: str\n",
        "backend/app/unrelated.py": "print('not relevant')\n",
    },
    source_root="backend",
)

assert [file.path for file in context.files] == ["backend/app/models.py"]
assert context.unresolved_imports == ()
print(context.files[0].content)
```

The caller supplies all file contents explicitly. A future upload or GitHub
adapter can produce the same `project_files` mapping; the collector itself
does not fetch repositories, read local files, execute code or call an LLM.
Models, routes and APIs are included when they are imported; the collector
does not guess files from their names or claim to understand function calls.

## Inputs and outputs

- `file_path`: repository-relative path of the code being reviewed.
- `source_code`: current submitted text, which can differ from the snapshot.
- `project_files`: mapping of repository-relative paths to file text.
- `source_root`: optional Python import root, such as `backend` or `src`.
  The reviewed file must be inside it. The default is the repository root.
- `max_files`: maximum number of selected files; default 8.
- `max_chars`: maximum total characters of selected contents; default 24,000.
  This counts characters, not UTF-8 bytes, tokens or prompt formatting.

The returned immutable `ProjectContext` contains:

- `files`: ordered `ContextFile(path, content)` records.
- `unresolved_imports`: unique import labels for which no supplied file matched.
  For Python this can include standard-library or third-party modules; it is
  not proof of a missing dependency. JavaScript package imports are ignored.
- `omitted_files`: resolved files excluded by the file/character budget.
- `total_chars`: sum of selected contents' lengths.

Selection follows import order and deduplicates files. The reviewed file is
excluded. A file that would exceed the character budget is omitted whole;
later smaller files can still fit. Paths use `/` in the result; Windows
separators are accepted. Absolute paths, parent traversal, null bytes,
duplicate normalized snapshot paths, non-text contents and invalid limits
raise `ValueError`.

## Supported resolution and limits

- Python `.py`: AST-based `import` and `from` statements, aliases, relative
  imports, modules and package `__init__.py` files. A named import resolves
  a matching submodule first, then the containing module/package. Syntax
  errors return no context instead of guessing imports from unfinished code.
- JavaScript/TypeScript `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`:
  local static imports, side-effect imports, re-exports and literal CommonJS
  `require` calls. Comments and quoted/template strings are skipped. Explicit
  code extensions, extensionless modules and directory `index` files work.
  TypeScript sources prefer `.ts`/`.tsx`; other sources prefer `.js`/`.jsx`.
- JavaScript resolution is a lightweight token-based approximation, not a full
  language parser. It does not interpret regex literals, shadowed `require`,
  template interpolation or build-specific resolution rules.
- Only direct imports are collected. There is no recursive dependency graph,
  Python runtime import-path emulation, npm resolution, TypeScript path aliases,
  `.js`-to-`.ts` rewriting, dynamic import evaluation or non-code asset loading.
- Supplied files remain untrusted source text. A future AI adapter must label
  them as code data, enforce the final prompt/token budget, and handle
  `unresolved_imports`/`omitted_files` in the review interface.

## Tests

Install `backend/requirements-dev.txt`, then run from `backend/`:

```sh
python -m pytest tests/test_project_context_service.py -q
python -m pytest tests -q
```

The collector's tests use only supplied strings. Existing API regressions use
throwaway SQLite databases and mocked AI results; no Supabase or AI key is
needed. See the task review summary for the recorded results.
