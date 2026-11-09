# Stage 11 Plan: GitHub Pull Request Integration

Approved 2026-11-09. Branch: `stage-11/github-pr-review` from `main` @ `aa329b9`. The full stage definition is in [PROJECT_PLAN.md](../PROJECT_PLAN.md#stage-11-github-pull-request-integration).

## Approved decisions

1. **Background reviews with progress.** `POST /pull-request-reviews/` checks everything, saves the PR and a `pending` review, returns 202, and reviews files in a background task. The task opens its own database session and never leaves a review `pending` on an error. The frontend polls while the review is pending. Kept simple: FastAPI background tasks, no job queue.
2. **Limits (configurable constants):** reject PRs with more than 30 changed files or 3,000 changed lines; review at most 10 files, each at most 100,000 characters; fetch at most 40 imported files.
3. **Changed-line focus.** The AI is told which lines changed. Findings within 1 line of a changed line are kept. Findings outside the diff are kept only when medium or high severity, at most 2 per file, and labeled "outside the diff" (`review_issues.outside_diff`). Low-severity findings outside the diff are dropped.
4. **`GITHUB_TOKEN` is required** and server-side only: never sent to the frontend, logged, returned in a response or committed. Without it the endpoint returns 503.
5. **Stage 6 History:** small, approved changes to `review_history.py` and `ReviewHistory.jsx` to show PR information, coordinated with the teammate who owns them. Manual-review history behavior is unchanged.
6. **Live verification** uses a small public demo PR in a sample repository the team controls. Creating or changing any remote repository needs separate approval.

## Data (migration `0004_pull_requests`)

- `pull_requests`: owner, repo, number, title, author, html_url, base_sha, head_sha, changed_files_count, additions, deletions, created_at. One snapshot per review.
- `pull_request_files`: pull_request_id, path, status, additions, deletions, review_state (`pending`/`reviewed`/`skipped`/`failed`), skip_reason.
- `code_reviews.pull_request_id`: nullable, indexed. Manual reviews leave it empty.
- `review_issues.outside_diff`: nullable boolean. Empty for manual reviews.
- PostgreSQL: Row Level Security on and `anon`/`authenticated` access revoked on the new tables, as with `0003`.

## task_list

- [x] **11.1 GitHub client and URL validation:** strict `https://github.com/{owner}/{repo}/pull/{n}` parsing; API URLs built server-side; error mapping (401, 403/429 rate limit, 404 private or missing, timeout); paginated files; token never logged or returned.
- [x] **11.2 Diff parsing and file filtering:** changed line numbers from patches; skip removed, binary, generated, too large and unsupported files with a reason.
- [x] **11.3 PR context:** the Stage 9 collector reports candidate import paths; only those that exist at the head commit are fetched, within the limit. Existing collector behavior unchanged.
- [x] **11.4 Migration `0004` and models:** SQLite and PostgreSQL migration tests, including old databases and RLS.
- [x] **11.5 Endpoint and background review:** every error response; per-file findings with `file_name`; changed-line filtering and labels; progress; partial and total failures; background task exceptions; manual reviews unchanged.
- [x] **11.6 Frontend:** PR tab and form, API errors, polling with cleanup, PR header, file filter, skipped-file reasons, "outside the diff" label, History PR badge.
- [x] **11.7 Docs and review:** README, PROJECT_PLAN, Stage 11 report; `code-reviewer` and `security-reviewer`; stop for approval before commit.
- [ ] **11.8 Live verification:** separate approval. Needs migration `0004` on Supabase, a `GITHUB_TOKEN`, a demo PR, and at most 10 Anthropic calls.
