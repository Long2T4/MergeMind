# Stage 11 GitHub Pull Request Integration — Review Summary

**Status (2026-11-09):** tasks 11.1–11.7 are done and in [PR #13](https://github.com/Long2T4/MergeMind/pull/13) (all 4 CI jobs passed; not merged). Migration `0004` is applied to Supabase ([results](#supabase-migration-results)) and **live verification passed** ([results](#live-verification-results)). Stage 11 closes when PR #13 is merged. The approved plan is in [stage-11-plan.md](../plans/stage-11-plan.md).

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
| Backend `pytest tests -q` | **245 passed, 12 skipped** (PostgreSQL-only; they run in CI). Before Stage 11: 109 passed |
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
- **AI line numbers:** in the live test, 4 of 5 findings pointed 1–3 lines too early. Fixed afterwards for pull request reviews (see [Line-number fix](#line-number-fix)), but the fix hasn't been re-verified live.
- The live test missed one minor issue (`average([])` divides by zero in `web/format.js`).
- The Stage 6 History changes still need review by bhavesh70655 before PR #13 merges.
- PostgreSQL migration tests passed in CI on PR #13 (18 passed, 2 SQLite-only skips), including RLS and sequence revokes.
- Background reviews run in the API process without a queue, which is fine for local use and a demo.

**Lessons for future work:** None new.

## Supabase migration results

Applied 2026-11-09 from PR #13's head `843254b`, with approval. `alembic upgrade head` was run once against the same Supabase project as Stage 10 (AWS us-east-2 pooler).

**Before migrating** (read-only gate; the migration would not run unless all of these passed):
- the version was `0003_protect_version_table`;
- the only schema differences from the Stage 11 models were `0004`'s 7 additions, and none of its names already existed;
- a fresh read-only export (`C:\Users\Longt\Downloads\mergemind-db-backup-2026-11-09\`, local and private, not in the repo) matched the live data file for file;
- the backend was stopped, and the migration file was unchanged since the reviewed commit.

**Migration output:** `0003_protect_version_table -> 0004_pull_requests` ran in one transaction and exited with code 0.

**After migrating** (read-only checks; all 41 passed):

| Check | Result |
|---|---|
| `alembic current` | `0004_pull_requests (head)` |
| Live schema vs models | No differences |
| New tables | `pull_requests` and `pull_request_files` exist |
| New columns | `code_reviews.pull_request_id` and `review_issues.outside_diff` are nullable and `NULL` on every existing row |
| Indexes and foreign keys | `ix_code_reviews_pull_request_id`, `ix_pull_request_files_pull_request_id`, `fk_code_reviews_pull_request_id` and the files-to-PR key exist; the Stage 10 indexes are intact |
| Security on the new tables | Row Level Security on (not forced); `anon` and `authenticated` have no table or sequence privileges |
| Existing tables | Row Level Security and API-role grants unchanged |
| Data | 1 user, 2 projects, 14 reviews and 29 issues, with checksums over the original columns identical to before |
| Stuck reviews | #1 and #2 still `pending` and byte-for-byte unchanged |

## Live verification results

Run 2026-11-09 from PR #13's head `843254b`, with approval. It used the real app code, the migrated Supabase database, the real GitHub API (read with the fine-grained, public-read-only `GITHUB_TOKEN`) and the real Anthropic API.
- **Budget:** at most 3 Anthropic calls, enforced in code with SDK retries off.
- **Data sent:** fictional code only.
- **Demo:** [Long2T4/mergemind-demo PR #1](https://github.com/Long2T4/mergemind-demo/pull/1), "Add user sign-up helpers", head `0e6000d`, 6 changed files (+28 −4). Nothing was posted to GitHub.
- **Project:** "Stage 10 verification" (id 2). The review was submitted through the real UI.

| Check | Result |
|---|---|
| Invalid URL (`/issues/1`) | **422**, no GitHub or AI calls |
| Nonexistent PR (`/pull/999`) | **404** "not found or not public", no AI calls |
| Second submission while running | **409** "already being reviewed", no GitHub or AI calls |
| Review | **#15 completed**; the page showed "1 of 3", "2 of 3", "3 of 3 done", then the results, and stopped checking |
| PR details | `Long2T4/mergemind-demo#1`, title, author `Long2T4`, commit `0e6000d`, 6 files, +28 −4 |
| Skipped files | `docs/notes.md` unsupported, `old_helpers.py` removed, `package-lock.json` generated |
| Project context | `app/users.py` was sent with `app/models.py` only; the empty-name finding depends on that file |
| Findings | 5 saved (4 high, 1 medium), each with its file name; confidence 20/low; risk 70/high |
| Outside the diff | `eval()` in `app/legacy.py` (unchanged line; the PR changed lines 7–8): kept and labeled |
| History, Home and Learning | The History row shows `Long2T4/mergemind-demo#1 · Add user sign-up helpers` with 5 issues (4H 1M 0L); Learning loads all 15 reviews |
| Anthropic usage | 3 calls, `claude-haiku-4-5-20251001`, all `end_turn`. Tokens in/out: 708/285, 911/667, 725/255 |
| Existing data | All pre-existing rows identical (checksums); reviews #1 and #2 still `pending`; new rows only for review #15 |

**Findings compared with the code:**

| File | Finding | AI line | Actual line |
|---|---|---|---|
| `app/legacy.py` | High, security: `eval()` runs arbitrary code (outside the diff) | 2 | 3 |
| `app/users.py` | High, security: SQL injection through an f-string query | 10 | 12 |
| `app/users.py` | Medium, error handling: connection never closed | 9 | 11 |
| `app/users.py` | High, logic: `register_guest()` passes an empty name that `User` rejects | 14 | 17 |
| `web/format.js` | High, logic: off-by-one loop (`<=`) | 3 | 3 |

**Missed:** `average([])` divides by zero in `web/format.js`. It's minor, since the off-by-one already breaks the function.

**Bugs found:** none in MergeMind. The only console error was a missing `favicon.ico`, which is unrelated.

**Limitation:** AI line numbers were off by 1–3 lines in 4 of 5 findings, worse than the one-line error in Stage 10. Labels came out right here, because `app/users.py` is entirely new and the `eval()` line is far from the change. Near a small change, though, a wrong line number could put a finding on the wrong side of the diff, and the flagged-code panel shows the reported line.

**Data created:** pull request 1 with 6 file rows, review #15 and its 5 findings. The demo repository stays public for Stage 14.

## Line-number fix

**Cause:** pull request files were sent to the AI as one JSON string. The model had to count `\n` escapes to find a line, and it miscounted: its raw replies said lines 10, 9 and 14 for code on lines 12, 11 and 17. MergeMind only checked that a line was between 1 and 1,000,000, never against the file, and then used it to decide inside versus outside the diff.

**Fix (pull request reviews only; manual reviews send exactly the same payload and prompt as before):**
- Each line of a pull request file is sent with its number (`  12 | query = ...`), numbered the way GitHub numbers lines (split on newlines, ignore a trailing newline and `\r`). The prompt says the prefix isn't code, `line_reference` must be one of those numbers, the model must never count lines itself, and the prefixes must not appear in suggested fixes.
- A line reference outside the file (below 1 or past its last line) is dropped before the diff check. The finding keeps no line and counts as outside the diff: kept and labeled if medium or high, dropped if low. It is never pinned to an invented line.

**Tests:** 15 new regression tests:
- numbering, including Windows line endings, a trailing newline and right-aligned numbers;
- line counts matching the numbering;
- the numbered pull request payload;
- an unchanged manual payload and prompt;
- the prompt-size limit with numbering;
- out-of-range lines dropped and never placed inside the diff;
- an end-to-end check that an imaginary line is saved without a line.

**Not yet verified live.** Whether numbering fixes the model's accuracy can only be confirmed with another Anthropic run. Re-reviewing the same demo PR would take 3 calls, and needs approval.

**Remaining risk:** a wrong line that is still inside the file is trusted. Only impossible lines are caught.
