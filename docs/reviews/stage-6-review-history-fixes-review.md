# Stage 6 Review History Fixes — Review Summary

**What was implemented**: Bug fixes to the merged Stage 6 history feature
(`308bbd5`), no rebuild and no schema changes:

- The History language filter now uses the stored values via
  `frontend/src/constants/languages.js` (`cpp`, `c` and `other` work).
- Opening a History review now loads it from a new
  `GET /review-history/{id}`, with loading, not-found, and error-with-retry
  states, instead of looking it up in the stale `/code-reviews/` list.
- Filters and page survive going to the detail view and back, and the back
  button says "Back to Review History".
- Search is debounced (300 ms) and treats `%`/`_` literally
  (`icontains(autoescape=True)`).
- Stats follow the active filters, using 2 aggregate queries instead of 4.
- The list returns lightweight summaries (`code_preview`, `issue_count`,
  `high_severity_count`) instead of full code and issues.
- `pytest` was added to `backend/requirements-dev.txt`.

**Tests run**:

- `pytest tests/test_review_history.py`: 9 passed (3 original, 1 updated
  for the summary shape, 6 new regression tests). The 6 new tests failed
  before the fix.
- A smoke test of the full `app.main` app on in-memory SQLite, with the AI
  call stubbed: submit → history → detail → stats all OK, and `/stats` is
  not shadowed by `/{id}`.
- `vite build` succeeds.
- Manual browser QA against a throwaway SQLite database (never Supabase)
  passed:
  - a stale-list review opens;
  - search, status and page survive detail and back;
  - the debounce sent no requests for partial terms;
  - C++ and C filters work;
  - not-found and API-error states display correctly.
- There is no frontend test runner in the repo.

**Review findings**:

- `code-reviewer`: no CRITICAL, HIGH or MEDIUM. One LOW fixed: a search
  typed less than 300 ms before opening a review was lost.
- `security-reviewer`: no CRITICAL or HIGH. Its two MEDIUMs (the detail
  endpoint makes id enumeration easy without auth; unbounded substring
  scans) both come from the known no-auth / no-size-limit gap and are
  documented in `docs/PROJECT_PLAN.md` rather than fixed here. One LOW fixed
  (the stats "completed" count was case-sensitive). Other LOWs are deferred:
  an `offset` upper bound and language/status allowlists.

**Unresolved issues**:

- No authentication or per-user isolation (app-wide; out of scope).
- Feedback status updates remain Stage 9.
- The Stage 7 definition conflicts between two sections of
  `docs/PROJECT_PLAN.md` and needs team confirmation.
- The list response shape changed (no `submitted_code`/`issues` per item).
  `ReviewHistory.jsx` was its only consumer.

**Lessons for future work**: Duplicated value lists drift; see
[growth-log 2026-10-26](../growth-log/2026-10-26.md).
