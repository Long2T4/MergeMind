# Stage 10 Plan: Foundation and Stability

Approved 2026-11-05. Branch: `stage-10/foundation` from `main` @ `9d3f5c1`. The full stage definition is in [PROJECT_PLAN.md](../PROJECT_PLAN.md#stage-10-foundation-and-stability).

## Order

The order was changed so that code-only work comes first and the two tasks that touch Supabase run together:

10.1, then 10.3, then 10.5, then 10.2, then 10.4, then 10.6.

## task_list

- [x] **10.1 CI:** GitHub Actions for backend tests (Ubuntu and Windows), migrations on a throwaway PostgreSQL, frontend tests and the build. No secrets.
- [x] **10.3 Reliability:**
  - 404 for a missing project;
  - safe AI output normalization;
  - rollback to `failed` on save errors;
  - output limit detection and an AI timeout;
  - 409 for a duplicate email and 404 for a project's missing user;
  - a manual, dry-run-by-default stale-review command.
- [x] **10.5 Small fixes:** TypeScript highlighting, stale Stage 9 labels, the `.env.example` pooler URL.
- [x] **10.2 Migrations:** Alembic with a safe baseline and an index migration. `create_all` was removed from startup. Tested on SQLite.
- [ ] **10.4 Live verification:** needs approval; the procedure is in the [Stage 10 report](../reviews/stage-10-foundation-review.md#live-verification-procedure).
- [x] **10.6 Regression and docs:** done locally.
- [ ] **Remaining:** the first GitHub Actions run, the PostgreSQL migration tests in CI, and a PR review.

## Boundaries

- No changes to the real Supabase database or calls to the live Anthropic API without approval.
- Production review records are never changed automatically.
- No commit, push or merge without approval.
- No Stage 11 or later work.
