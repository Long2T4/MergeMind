# Project aware review integration

A review can now include a supplied project snapshot. The backend selects directly imported local Python or JavaScript/TypeScript files using the collector from PR #6 and sends only those selected files alongside the submitted code to the Anthropic review service. Findings still refer to the submitted file.

## Use the form

1. Open New Review and paste or upload the source to review.
2. Enable **Include related project files**.
3. Enter its repository-relative path, for example `src/review.py`. For Python imports rooted in a subdirectory, optionally enter that source root, for example `backend`.
4. Paste a JSON object mapping project-relative file paths to source text into **Project files JSON**, or upload that object as a `.json` file. [Example snapshot](examples/project-files.json).
5. Run the review. The results show selected paths, selected character count, unresolved imports, and files omitted by context limits.

The snapshot is a mapping, not a zip archive or a GitHub URL. For example, review `from src.models import User` at `src/review.py` with the example snapshot. `src/models.py` is selected; `src/unrelated.py` is excluded.

Context collection supports `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, and `.cjs`. The reviewed path determines import resolution. The form includes TypeScript in the shared language list. Other languages can still use the ordinary submission flow without project context.

## API contract

The existing `POST /code-reviews/` accepts an optional `project_context` object:

```json
{
  "project_id": 1,
  "submitted_code": "from src.models import User\nUser(name)\n",
  "programming_language": "python",
  "project_context": {
    "file_path": "src/review.py",
    "source_root": "",
    "files": {
      "src/models.py": "class User: pass\n",
      "src/unrelated.py": "print('unrelated')\n"
    }
  }
}
```

Omit `project_context` to preserve the existing single-file behavior. Context requests are validated before a review is stored or the AI provider is called. Invalid paths, duplicate normalized paths, unsupported source extensions, mismatched source roots, non-text files, and excessive input return HTTP 422. Python code exceeding parser recursion limits also returns HTTP 422. Unresolved imports are diagnostics, not proof that a dependency is missing. A syntactically unfinished Python file selects no context, following the collector's behavior.

The POST response includes `context_summary` (or null for ordinary submissions). Its fields are `file_path`, `selected_files`, `total_chars`, `unresolved_imports`, and `omitted_files`. On AI failure, the review is saved as failed and selection diagnostics are still returned; they do not imply a successful review.

## Limits and provider input

- Submitted code: at most 200,000 characters; language label: 1–40 characters.
- Snapshot: at most 50 files, at most 200,000 source characters in total, and at most 240 characters per path/source root. The browser rejects JSON uploads larger than 1,300,000 bytes before reading them. JSON serialization overhead can make an upload larger than its source text.
- Selected context: at most 8 files and 24,000 source characters. Whole files are omitted when they exceed selection limits; later smaller files can still fit.
- Complete serialized provider input plus reviewer instructions: at most 250,000 characters. This catches JSON escaping overhead as well. These are character limits, not a token count or a guarantee of provider acceptance. Browser string limits count UTF-16 code units and can be stricter for supplementary Unicode characters.

Trusted reviewer instructions use the provider's system field. Submitted source, language, path, and selected file contents are serialized as JSON in the user message and described as untrusted code data. The model is instructed to use related files for context and report findings only in submitted code. This separation reduces instruction confusion; it is not a guarantee against model prompt injection or incorrect findings.

Supplied files selected for context are sent to the configured AI provider. Include only files intended for that review. No snapshot code is executed by the collector.

## Storage and scope

The original submitted code, findings, and scores use the existing database flow. Project snapshots and selection diagnostics are **not persisted**. The UI carries the POST summary into the results navigation state for that submission; saved-history API responses have null context metadata. Reattach project files for retries. No database migration or unrelated history change is required.

GitHub retrieval, recursive dependency traversal, static analyzer integration, developer feedback, and context persistence are separate future work. Collector resolution limits are documented in [project-aware-context.md](project-aware-context.md).

## Verification

`backend/tests/test_project_context_integration.py` exercises the real route, collector, prompt builder, normalization, database persistence, confidence, and risk flow with an isolated SQLite database and a mocked provider client. Frontend tests cover the form, JSON uploads and errors, diagnostics, TypeScript, snapshot validation, and API serialization. See [the review summary](reviews/project-aware-integration-review.md) for the final results.
