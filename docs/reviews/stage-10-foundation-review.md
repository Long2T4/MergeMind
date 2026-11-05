# Stage 10 Foundation and Stability — Review Summary

**Status (2026-11-05):** **Stage 10 verification is complete.** All steps passed, including the live Supabase and Anthropic checks. The stage closes when these final docs are merged.

| Step | Status |
|---|---|
| Stage 10 code | Merged into `main` in PR #10 and PR #11 (`f12dbc6`) |
| CI | All 4 jobs passed on both PRs and on `main` |
| Supabase migration | **Done:** see [Supabase migration results](#supabase-migration-results) |
| Live Anthropic review | **Done:** see [Live review results](#live-review-results) |

**What was implemented:**

- **10.1 CI** (`.github/workflows/ci.yml`):
  - backend tests on Ubuntu and Windows (Python 3.12);
  - migration tests on a throwaway PostgreSQL 16 service;
  - frontend tests and the production build (Node 22).
  - It runs on pull requests, pushes to `main` and manual triggers, with read-only permissions and no secrets.
- **10.3 Reliability:**
  - `POST /code-reviews/` returns 404 for a missing project before saving or calling the AI.
  - AI findings with wrong field types, long titles or out-of-range lines are normalized; malformed items are skipped. A response with no usable findings, a response cut off at the output limit (`max_tokens` raised from 2,000 to 4,096) or one with no text is saved as `failed`.
  - Any error while saving findings rolls back and marks the review `failed`, so it can't stay `pending`.
  - The AI client now has a 120-second timeout.
  - `POST /users/` returns 409 for a duplicate email, and `POST /projects/` returns 404 for a missing user.
  - `python -m app.maintenance` lists reviews stuck on `pending`. It's a dry run unless `--apply` is given, and it never runs automatically.
- **10.5 Small fixes:**
  - TypeScript syntax highlighting, including `ts`/`tsx` fence hints;
  - stale "Stage 9" feedback labels now say Stage 12;
  - `.env.example` uses the pooler URL format;
  - the frontend explains a missing project instead of a generic error.
- **10.2 Migrations:**
  - Alembic `0001_baseline` creates only missing tables, adds only missing nullable or defaulted columns, never drops data, and refuses to downgrade.
  - `0002_review_indexes` adds indexes on `code_reviews.project_id`, `code_reviews.created_at` and `review_issues.review_id`, skipping any that already exist.
  - `0003_protect_version_table` (PostgreSQL only): Supabase gives its `anon` and `authenticated` API roles full access to new public tables. This migration turns on Row Level Security for `alembic_version`, without FORCE, so the owner that runs migrations is unaffected. It also removes those two roles' access to that table. App table permissions aren't changed.
  - The models declare the same indexes.
  - `main.py` no longer calls `create_all`.
  - `alembic upgrade head --sql` previews the SQL without a database.

**Read-only Supabase inspection (2026-11-05):**
- PostgreSQL 17.6, reached through the pooler.
- The live schema matches the models exactly; the only differences are the three missing indexes.
- `null_status` is 0, and `risk_breakdown` and `confidence_evidence` are `json`.
- There's no `alembic_version` table yet. All four app tables have Row Level Security enabled with no policies.
- Two reviews have been stuck on `pending` for more than 30 minutes. They were left untouched.
- A read-only JSON export of all four tables (1 user, 1 project, 12 reviews, 27 issues) is saved outside the repo.

- **10.6 Docs:** README setup, migrations, tests, CI, error codes and limitations; plan status; this report; the [Stage 10 plan](../archive/stage-10-plan.md) (archived).

**Tests run (2026-11-05, Windows, Python 3.12.1, Node 24):**

| Check | Result |
|---|---|
| Backend `pytest tests -q` | **109 passed, 6 skipped.** The skips are the PostgreSQL migration variants, which need `MIGRATION_TEST_DATABASE_URL` and run in CI |
| New backend tests | 15 reliability tests (test-first: 10 failed before the fixes), 12 migration tests (6 SQLite, 6 PostgreSQL) |
| Frontend `npm test` | **68 passed** across 9 files (4 new) |
| Production build | **Passed:** 92.5 KB JS gzipped (was 89.8 KB) |
| Migrations, temporary SQLite file | Fresh database matches the models; an old Stage 2 database gains new columns with data kept; a `create_all` database upgrades cleanly; repeat upgrades are a no-op; the index migration reverses and reapplies; the baseline refuses to downgrade |
| Migration CLI | `alembic upgrade head`, `alembic current` and `--sql` preview worked on a temporary SQLite file |
| App smoke test | On a migrated temporary database: health, 409, 404s, saved `failed` review without a key, history and stats all correct |
| PostgreSQL migrations | **Not run locally:** Docker is installed but its engine wasn't running. The CI `Migrations (PostgreSQL)` job covers this |

**Review findings:** `code-reviewer` found no CRITICAL or HIGH issues and approved.
- **MEDIUM:** the README must document `alembic upgrade head`. **Fixed.**
- **MEDIUM:** fresh and upgraded databases had different `status` defaults. **Fixed.**
- **MEDIUM:** the baseline matches existing columns by name only. **Handled** with the read-only pre-migration check below, not by changing data automatically.
- **LOW:** case-sensitive duplicate emails (pre-existing) and `datetime.utcnow` deprecation warnings. **Left as is.**

**Unresolved issues:**
- Resolved since this report was first written: CI has run (all 4 jobs passed), migrations are applied to Supabase, and live verification passed. See the sections below.
- AI line numbers can be off by one (seen in live review 2). This is a known limitation of model-reported lines.
- Two reviews from before Stage 10 are still stuck on `pending`. They were left for a team decision; `python -m app.maintenance --apply` can mark them `failed`.
- The app connects to Supabase as the `postgres` role. A least-privilege role is a Stage 12 consideration.
- Backend tests show 174 deprecation warnings (Pydantic `Config`, `datetime.utcnow`). They're harmless, but worth cleaning up later.
- A database must now be migrated before the app can use it. Without that, `/health` works but data routes fail with "no such table". The README documents this.

**Lessons for future work:** none new beyond the existing growth log.

## Supabase migration results

Applied 2026-11-05 from `main` at `f12dbc6`, with team approval. `alembic upgrade head` was run once against the Supabase project (AWS us-east-2 pooler).

**Before migrating** (read-only gate; the migration would not run unless all of these passed):
- the database had never been migrated (no `alembic_version` table);
- the only schema differences from the models were the 3 planned indexes;
- all four tables matched the backup exactly (checksums).

**Migration output:** `0001_baseline`, `0002_review_indexes` and `0003_protect_version_table` ran in one transaction and exited with code 0. The baseline added nothing, because no tables or columns were missing.

**After migrating** (read-only checks; all 15 passed):

| Check | Result |
|---|---|
| `alembic current` | `0003_protect_version_table (head)` |
| Indexes | `ix_code_reviews_project_id`, `ix_code_reviews_created_at` and `ix_review_issues_review_id` all exist |
| `alembic_version` Row Level Security | Enabled, not forced |
| `anon` and `authenticated` on `alembic_version` | No SELECT, INSERT, UPDATE or DELETE access |
| App tables | Row Level Security still enabled; permissions unchanged |
| Live schema vs models | No differences |
| Data | 1 user, 1 project, 12 reviews and 27 issues, identical to the backup |
| Stuck reviews | Both `pending` reviews untouched |

**Backup:** a read-only JSON export taken before migrating is in `C:\Users\Longt\Downloads\mergemind-db-backup-2026-11-05\` (local and private, not in the repo).

## Live review results

Run 2026-11-05 from `main` at `f12dbc6`, with team approval. It went through the real app code, the real Supabase database and the real Anthropic API.
- **Budget:** at most 2 Anthropic calls, with the SDK's automatic retries turned off.
- **Data sent:** fictional code only.
- **Project:** a dedicated "Stage 10 verification" project (id 2), under the existing test user.

| Check | Result |
|---|---|
| Nonexistent project (`project_id` 999999999) | **404** "Project not found", with 0 Anthropic calls |
| Review 1: `average()` on an empty list | **#13 completed.** 1 finding: high, error_handling, "Division by zero error on empty input", line 5 (correct) |
| Review 1 scores | Confidence 20/low (`{"ai": true}`); risk 70/high (maintainability 30) |
| Review 1 in the app | Detail endpoint returns the same review; History shows it with 1 issue (1H 0M 0L) |
| Review 2: `create_user("")` with the example snapshot | **#14 completed.** 1 finding: high, logic, "Empty string passed to function that rejects empty input" |
| Review 2 scores | Confidence 20/low; risk 70/high |
| Project context | **Worked.** `context_summary` selected `src/models.py` (134 characters), with nothing unresolved or omitted. The recorded request to Anthropic contained only `src/models.py`, not `src/unrelated.py`. The finding depends on code that exists only in `src/models.py` |
| Learning page data | All 14 saved reviews loaded ("Based on all saved reviews"); both new reviews included; category totals and repeats calculated by `lib/learning.js` |
| Anthropic usage | 2 calls, both `claude-haiku-4-5-20251001`, `stop_reason: end_turn`. Tokens in/out: 588/305 and 647/292 |
| Existing data | The 2 stuck `pending` reviews were untouched, and no records were changed or deleted |

**Limitation observed:** review 2's finding says line 5, but the empty-string call is on line 6. Line numbers come from the model and can be off by a line, as the README notes.

**Data created:** project 2 and reviews 13 and 14, with their findings.

## Live verification procedure

Run this only with explicit approval. It uses the real Supabase database and one or two Anthropic calls, costing a few cents with Claude Haiku.

**Before migrating (read-only):**

1. Back up the database: use Supabase's backups, or download a schema-and-data export from the dashboard.
2. In the Supabase SQL Editor, run these **read-only** checks:
   ```sql
   SELECT table_name, column_name, data_type, is_nullable, column_default
   FROM information_schema.columns
   WHERE table_schema = 'public'
     AND table_name IN ('users', 'projects', 'code_reviews', 'review_issues')
   ORDER BY table_name, ordinal_position;

   SELECT count(*) AS null_status FROM review_issues WHERE status IS NULL;
   SELECT review_status, count(*) FROM code_reviews GROUP BY review_status;
   SELECT to_regclass('public.alembic_version') AS alembic_table;
   ```
   Expect:
   - `risk_breakdown` and `confidence_evidence` are `json`;
   - `status` is `NO` nullable;
   - `null_status` is 0;
   - `alembic_table` is empty.

   **Stop and decide with the team** if any column has a different type or nullability. The baseline won't change existing columns.

**Migrate:**

3. Preview: from `backend/`, run `alembic upgrade head --sql` and read the output.
4. Apply: `alembic upgrade head`. Then confirm `alembic current` shows `0003_protect_version_table (head)`.
5. Dry run: `python -m app.maintenance`. This lists any reviews stuck on `pending`. Don't add `--apply` without a team decision.

**Verify:**

6. Start the backend and frontend. Create a dedicated project named **Stage 10 verification** with `POST /projects/`, using an existing user id.
7. In New Review, choose that project, paste a short Python function with an obvious bug, and run the review. This is **one Anthropic call**.
8. Check that:
   - the review is `completed`;
   - findings are saved;
   - each finding shows confidence 20/low;
   - the review has a risk score;
   - it appears in History with severity counts;
   - the detail page opens;
   - the Learning page includes it.
9. Optional (a second call): run a project-context review with [`docs/examples/project-files.json`](../examples/project-files.json). Confirm only `src/models.py` is selected.
10. With no AI cost: `POST /code-reviews/` with `"project_id": 999999` should return 404.
11. Record the results, dates and review ids in this file.

**Data created:** one project and one or two reviews. They stay unless the team deletes them.
