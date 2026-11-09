# Stage 11 GitHub Pull Request Integration — Review Summary

**Status (2026-11-09):** tasks 11.1–11.7 are implemented and tested locally on `stage-11/github-pr-review` (from `main` `aa329b9`). Nothing is committed, pushed, migrated or verified live yet. The approved plan is in [stage-11-plan.md](../plans/stage-11-plan.md).

**What was implemented:**

- **Pull request reviews:** `POST /pull-request-reviews/` takes a public `https://github.com/{owner}/{repo}/pull/{number}` URL.
  - Before saving anything, it checks the URL, the project, the in-progress and capacity limits, the server's `GITHUB_TOKEN`, access to the pull request, its size, and whether any files are reviewable.
  - It saves the pull request and a `pending` review, returns 202, then reviews the files in a background task.
- **GitHub client** (`github_service.py`):
  - read-only, with API addresses built server-side; the user's URL is never requested;
  - private repositories are refused even if the token could read them;
  - clear errors for not found (404), rate limits (503, with the reset time), a bad token and timeouts;
  - file downloads stop at the size cap;
  - the token never appears in logs, errors or responses.
- **File selection** (`diff_service.py`, `pr_review_service.py`):
  - rejects pull requests with more than 30 changed files or 3,000 changed lines;
  - reviews the first 10 Python, JavaScript, TypeScript, Java, C or C++ files;
  - skips removed, generated, binary, unsupported and oversized files, each with a recorded reason.
  - All limits are constants in `pr_review_service.py` and `diff_service.py`.
- **Changed-line focus:**
  - The AI gets each file's changed line numbers, through a prompt addition used only for pull requests. Manual reviews send exactly the same prompt and payload as before.
  - Findings within 1 line of a change are kept.
  - Medium or high findings elsewhere are kept, at most 2 per file, and labeled `outside_diff`.
  - Low-severity findings outside the diff are dropped.
- **Context:** the Stage 9 collector now lists its import candidates (`import_candidates`). Only those that exist at the head commit are fetched, up to 40 per review.
- **Background task:** it opens its own database session and commits after each file, so progress shows while it runs.
  - If one file fails (AI, GitHub or database), the others continue.
  - The review is `completed` if at least one file was reviewed, and `failed` otherwise.
  - Any unexpected error marks the review and its pending files `failed`, and the task never raises.
  - At most 3 PR reviews run at once and at most 20 start per hour (429), and the same pull request can't be reviewed twice at the same time (409). The hourly cap bounds AI spending at 200 calls an hour without accounts.
  - If the pull request is pushed to while it's being read, the request is rejected (409), so files and diffs always come from one commit.
- **Migration `0004_pull_requests`:**
  - adds the `pull_requests` and `pull_request_files` tables;
  - adds a nullable, indexed `code_reviews.pull_request_id` and a nullable `review_issues.outside_diff`;
  - skips anything that already exists, and its downgrade removes only what it added;
  - on PostgreSQL, turns on Row Level Security and revokes `anon`/`authenticated` access to the new tables and their id sequences.
- **Frontend:**
  - New Review: a GitHub pull request tab, with URL validation that mirrors the backend.
  - Results page: the PR header (repository link, title, author, commit, size) and per-file progress. It checks for updates every 3 s while a PR review is pending, stops on completion, when the page is left, or after about 10 minutes, then says so.
  - Findings: a file filter, file-name and "Outside the diff" labels, and flagged code taken from the file's diff.
  - Changed files: each file's state and its diff.
  - Retrying a failed PR review reopens the PR tab prefilled.
- **History** (Stage 6 files, small changes approved on 2026-11-09):
  - list rows gain optional `pull_request_id`, `pr_repo`, `pr_number` and `pr_title` fields;
  - History and Home rows show `owner/repo#n · title` for PR reviews;
  - manual rows are unchanged, and every existing Stage 6 test passes without changes.
  - **Coordinate with the Stage 6 owner (bhavesh70655) before merging.**

**Tests run (2026-11-09, Windows, Python 3.12.1, Node 24):**

| Check | Result |
|---|---|
| Backend `pytest tests -q` | **230 passed, 12 skipped** (PostgreSQL-only; they run in CI). Before Stage 11: 109 passed |
| New backend tests | GitHub client and URL validation, diff parsing, file filtering and changed-line focus, and 34 endpoint and background-task tests. These include rate limits, background failures, capacity, the head-commit race, download caps, and manual-review and History regressions. All use a fake GitHub (`httpx.MockTransport`) and a mocked Anthropic client |
| Migration tests | Fresh database, old Stage 2 database, `create_all` database, a Stage 10 database upgraded with data kept, downgrade to `0003` and re-upgrade (SQLite). PostgreSQL variants, including RLS and sequence revokes, run in CI only: Docker's engine wasn't running locally |
| `alembic upgrade head` / `current` / `--sql` | Worked on a temporary SQLite file; the `0004` preview SQL is additive only |
| Frontend `npm test` | **87 passed** (was 68) |
| Production build | Passed: 95.5 KB JS gzipped (was 92.5 KB) |
| Browser check | Real backend on a temporary SQLite database with synthetic data, no AI key and no GitHub token. Checked the completed and pending PR reviews, the PR form, History rows and a 375 px-wide window (no sideways scroll). The missing-token 503 message showed correctly. Two layout fixes were made (repository name casing, squeezed finding titles) |

**Review findings:** `code-reviewer` and `security-reviewer` found no CRITICAL or HIGH issues.

| Finding | Severity | Outcome |
|---|---|---|
| The pull request can change between reading its details and its files | MEDIUM | **Fixed:** the head commit is re-checked; 409 if it moved |
| A server stop mid-review leaves it `pending` with no explanation | MEDIUM | **Fixed in the UI:** a message once checking stops. Recovery is the existing `python -m app.maintenance` command |
| Unthrottled AI and GitHub use per request | MEDIUM | **Fixed for the local/demo setup:** no duplicate in-progress reviews (409), at most 3 at once and 20 per hour (429), and the backend listens on localhost only. Per-user limits need Stage 12 accounts. Manual reviews (pre-existing) stay uncapped: set an Anthropic spend limit |
| A file missing from a truncated tree is downloaded whole | MEDIUM | **Fixed:** downloads stop at the size cap |
| `anon`/`authenticated` keep access to the new id sequences | LOW | **Fixed** in `0004` |
| Redirects allowed without a limit | LOW | **Fixed:** at most 3 |
| `*.stackdump` files could be committed | LOW | **Fixed:** added to `.gitignore` |
| Downgrade isn't idempotent | LOW | Left: PostgreSQL rolls back a failed downgrade |
| One reviewed file out of 10 still gives `completed` | LOW | Left: a notice says how many files failed, and each file's state is shown |
| Each update check returns every file's diff | LOW | Left: at most 30 files and 3,000 lines |
| A repository made private after submission isn't re-checked | LOW | Left: the window is short; use a public-only token |

**Unresolved issues:**
- Migration `0004` isn't applied to Supabase (needs approval).
- Live verification (11.8) needs approval, a `GITHUB_TOKEN`, and a small public demo PR in a team-controlled sample repository.
- The PostgreSQL migration tests haven't run yet; CI runs them when the branch is pushed.
- Background reviews run in the API process without a queue, which is fine for local use and a demo.

**Lessons for future work:** None new.
