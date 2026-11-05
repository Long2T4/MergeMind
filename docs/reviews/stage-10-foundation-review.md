# Stage 10 Foundation and Stability — Review Summary

**Status:** local work is complete on branch `stage-10/foundation` (2026-11-05). **Stage 10 is not complete yet.** Three things remain:
1. the first GitHub Actions run, including the PostgreSQL migration tests;
2. applying the migrations to Supabase;
3. one live review with Anthropic.

Nothing has been committed, pushed or run against Supabase or Anthropic.

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

**Read-only Supabase inspection (2026-11-05):**
- PostgreSQL 17.6, reached through the pooler.
- The live schema matches the models exactly; the only differences are the three missing indexes.
- `null_status` is 0, and `risk_breakdown` and `confidence_evidence` are `json`.
- There's no `alembic_version` table yet. All four app tables have Row Level Security enabled with no policies.
- Two reviews have been stuck on `pending` for more than 30 minutes. They were left untouched.
- A read-only JSON export of all four tables (1 user, 1 project, 12 reviews, 27 issues) is saved outside the repo.
  - The models declare the same indexes.
  - `main.py` no longer calls `create_all`.
  - `alembic upgrade head --sql` previews the SQL without a database.
- **10.6 Docs:** README setup, migrations, tests, CI, error codes and limitations; plan status; this report; the [Stage 10 plan](../plans/stage-10-plan.md).

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
- The first CI run hasn't happened.
- Migrations haven't been applied to Supabase.
- Live verification hasn't been run.
- Backend tests show 174 deprecation warnings (Pydantic `Config`, `datetime.utcnow`). They're harmless, but worth cleaning up later.
- A database must now be migrated before the app can use it. Without that, `/health` works but data routes fail with "no such table". The README documents this.

**Lessons for future work:** none new beyond the existing growth log.

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
4. Apply: `alembic upgrade head`. Then confirm `alembic current` shows `0002_review_indexes (head)`.
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
