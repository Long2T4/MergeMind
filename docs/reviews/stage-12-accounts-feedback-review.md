# Stage 12: Accounts, Developer Feedback and Learning — Review Summary

**Status:** implemented and tested locally on `fix/stage-12-pr15`, **not merged**. Not verified against live Supabase: migration `0005` hasn't been applied there, and no real Supabase Auth project has been configured.

## What was implemented

Supabase Auth sign-in with per-user data, project creation and renaming, finding outcomes (open, fixed, dismissed, false positive; "fixed" is self-reported), and finding outcomes by category on the Learning page.

- **Original implementation:** bhavesh70655, PR [#15](https://github.com/Long2T4/MergeMind/pull/15) (`d5f400f`).
- **Fixes and completion:** Long Truong, in the commits after it (`3b1f571` onward). They:
  - added migration `0005`, missing from the PR;
  - replaced the PR's global query filter with explicit ownership checks in each route, which also fixed Stage 11's background reviews;
  - verified the server-wide AI limits across users, and capped manual reviews at 30 per hour;
  - tested token checks with real signed JWTs;
  - recorded who changed an outcome and when, put the outcome control on each finding card, and added outcomes by category, project renaming and the account-linking command;
  - fixed the issues found in browser testing.

## Tests run

| Suite | Result |
|---|---|
| Backend, SQLite + local PostgreSQL 16 (Docker) | 427 passed, 2 skipped (SQLite copies of PostgreSQL-only tests) |
| Backend, SQLite only (as CI runs it) | 366 passed, 63 skipped (PostgreSQL variants) |
| Frontend (Vitest) | 106 passed |
| Production build | Passed (97.8 KB gzipped JS) |
| `alembic heads` | One head: `0005_stage12_accounts_feedback` |

Stage 12 test files:
- `test_stage12_authorization.py`: two users against every route, on SQLite and PostgreSQL.
- `test_stage12_tokens.py`: real RS256/ES256 tokens; forged, tampered, `HS256`, unsigned and expired tokens refused.
- `test_stage12_first_login.py`: simultaneous first sign-ins.
- `test_stage12_limits.py`, `test_stage12_feedback.py`, `test_stage12_learning.py`, `test_stage12_startup.py`, `test_link_account.py`.
- `test_migrations.py`: the Stage 12 cases.
- Frontend: `stage12.test.jsx` and `accountShell.test.jsx`.

**Browser check (2026-11-13):** the real backend ran on a temporary migrated SQLite database, with a fake Supabase Auth server issuing real RS256 tokens, a fake GitHub and a mocked Anthropic. The check covered:
- signing up, in and out;
- creating, renaming and selecting projects;
- a manual review and a pull request review;
- saving an outcome and reloading;
- the Learning totals;
- isolation between three accounts, and the linking screen;
- layout at 1366 px and 390 px.

120 simultaneous first requests from 20 new users all succeeded. Before the fix, 6 of them failed with 409.

## Security review

Scope: every Stage 12 change to authentication, authorization, routes, the frontend sign-in and migration `0005`.

**Found and fixed during Stage 12:**

| Severity | Finding | Fix |
|---|---|---|
| HIGH | The PR filtered data through a global query hook that depended on request context. Background pull request reviews broke, and routes that skipped the hook weren't protected | Explicit ownership checks in every route (`owned_project_ids`, `get_owned_project`); two-user tests on every route |
| HIGH | New columns had no migration, so the live schema wouldn't match the models | Migration `0005` |
| HIGH | Simultaneous first requests from a new user could get 409 "requires administrator linking" | Reuse the row only when its verified auth UUID matches; email alone never claims an account |
| MEDIUM | Manual reviews had no spending cap | 30 per hour, server-wide |
| MEDIUM | A missing or invalid `SUPABASE_URL` could fail unclearly | Refuse to start, and answer 503 if it breaks at runtime; never let a request through |
| LOW | The old open `/users/` endpoints, which list every email, were still registered and blocked only by a path check in the middleware | No longer registered (Step 8); the middleware still answers 403 |

**Checked and found sound:**
- **Tokens:**
  - only asymmetric signatures, from the project's public keys;
  - audience, issuer, expiry, subject and role are enforced;
  - `HS256` and unsigned tokens are refused, so the old algorithm-confusion attacks don't work.
- **Routes:** every route except `/health` and the API docs requires the signed-in user, verified by listing the app's routes. Another user's data gets the same 404 as missing data.
- **Accounts:** never linked by email. Linking existing users is a deliberate admin command, with a dry run by default.
- **Frontend:**
  - holds only the publishable key;
  - there's no `service_role` key or secret anywhere;
  - Stage 12 adds no HTML injection. The two existing `innerHTML` uses render highlight.js output, which escapes code.
- **Secrets and data:** no secrets in the diff or tracked files. Logs contain no tokens or code.
- **Background work:** pull request reviews don't depend on request context.

**Remaining, accepted or deferred** (none blocks merging; several block deployment):

| Severity | Item | Action |
|---|---|---|
| MEDIUM (deployment) | Anyone can sign up by default, and the AI limits are shared, so one account can use the hour's allowance | Make sign-up invite-only on any shared server ([guide](../supabase-auth.md#3-who-can-sign-up-recommended)) |
| MEDIUM (deployment) | Without email confirmation, someone can register an email they don't own | Turn on **Confirm email** |
| MEDIUM (deployment) | The publishable key is public, and Supabase's Data API accepts it | Every MergeMind table must keep Row Level Security on. That was true when last checked (2026-11-05), but check again before deploying |
| LOW | An access token stays valid for up to an hour after **Log out** | Accepted; documented |
| LOW | `/docs` and `/openapi.json` are public | Accepted locally; consider turning them off in production |
| LOW | CORS allows only `http://localhost:5173` | Make the origin configurable when deploying |
| INFO | Open PR #14 (Stage 6.1, groupmate's stage) adds `/review-history/trends` with no user check. Its frontend uses plain `fetch` without the token | Not registered yet, so inert. Before it's wired up, it needs `get_current_user` and `owned_project_ids`, and `authFetch` |
| INFO | `react-router` has a moderate advisory; this predates Stage 12 and is also on `main` | Upgrade separately |

## Migration 0005 review

- **Additive only:**
  - `users.auth_user_id`: nullable, with a unique index. Both PostgreSQL and SQLite allow many unlinked users.
  - `review_issues.status_updated_at`, and `status_updated_by` (nullable, foreign key to `users`).
  - the check constraint `ck_review_issues_status`.
  - It never rewrites data.
- **Safety check first:** if any finding has a status outside the four values, it stops and changes nothing. `status` has been NOT NULL with default `open` since `0001`, so the check is a guard, not an expected failure.
- **Already-applied pieces:** anything that already exists is skipped (for example, from `create_all`). `alembic upgrade head --sql` previews it.
- **Downgrade:** removes only what `0005` added. Status values stay; who and when are lost.
- **Stage 11:** pull request findings are saved with the default `open`, so they satisfy the constraint. Pull request tables are untouched. The tests upgrade a Stage 11 database with data.
- **Stage 13:** no number is reserved. Whichever stage merges second sets its `down_revision` to the current head, and `alembic heads` must show one head. Stage 13 must:
  - write only the four statuses;
  - not reuse the `status_updated_*` names;
  - protect any new table the way `0004` does: Row Level Security on, `anon` and `authenticated` access revoked.

  No Stage 13 migration exists locally to check against.
- **Applying to Supabase:** needs team approval. Back up first, preview with `--sql`, then run `alembic upgrade head`.

## Before deployment

1. Merge Stage 12, then apply `0005` to Supabase with approval and a backup.
2. In Supabase:
   - switch to asymmetric JWT signing keys;
   - turn on **Confirm email**;
   - set the Site URL;
   - make sign-up invite-only;
   - confirm Row Level Security is on for every table.

   See [Supabase Auth setup](../supabase-auth.md).
3. Link the owner of the earlier reviews with `python -m app.link_account` (dry run first).
4. Set `SUPABASE_URL` on the server, and `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in the frontend build.
5. Make the CORS origin configurable, and decide whether `/docs` stays public.
6. Do a live sign-in check against the real Supabase project. Only the fake Auth server has been tested so far.
7. Set a monthly spend limit in the Anthropic console.

## Lessons for future work

See [growth log 2026-11-13](../growth-log/2026-11-13.md): first-sign-in races, and enforcing ownership in each route instead of a global query hook.
