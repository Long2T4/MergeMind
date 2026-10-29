# Project-aware context collector review

**What was implemented**: A standalone backend service selects complete,
directly imported Python or JavaScript/TypeScript modules from supplied file
text. It validates relative paths, deduplicates results and applies file and
character budgets. Usage and boundaries are in
[project-aware-context.md](../project-aware-context.md); the task list is in
[the plan](../plans/project-aware-context-plan.md).

**Tests run** (October 29, 2026, Python 3.12):

- `cd backend && python -m pytest tests/test_project_context_service.py -q`:
  45 passed, including parameterized cases.
- `cd backend && python -m pytest tests -q`: 66 passed, with 68 existing
  dependency/model deprecation warnings. Database tests use SQLite and AI
  calls are mocked; no Supabase or live AI calls were made.
- Frontend regression check using the versions imported from the existing
  npm lockfile: `pnpm test` — 48 passed across 6 files; `pnpm build` — passed.
  The temporary pnpm lockfile is not part of this change.
- Manual smoke test against MergeMind's own `code_reviews.py` selected its
  database, models, schemas, AI, confidence and risk services: 6 related
  files, 14,135 characters. Third-party imports were reported as unresolved
  diagnostics. No supplied code was executed by the collector.
- `git diff --check`: passed.

**Review findings**: Self-review checked import ordering, source-root and
relative-path handling, duplicate/oversized files, input mutation, non-code
assets and the service's lack of filesystem/network/AI side effects. No
blocking issue found within the documented scope. The repository's ECC
commands were unavailable in this environment; this task followed the
plan, implement, test and review sequence directly.

**Unresolved issues**: This is Akhil's originally assigned Project-Aware Review
foundation, not the conflicting Developer Feedback definition of Stage 9.
AI/API/UI wiring, GitHub retrieval and recursive dependency discovery remain
separate work. JavaScript extraction is a lightweight approximation, not a
full parser; its limitations are documented in the usage guide.

**Lessons for future work**: None requiring a new growth-log entry.
