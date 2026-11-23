# Deploying MergeMind

MergeMind **hasn't been deployed**. This guide and its configuration files are ready, and the API image was built and checked locally. Deploying needs the team's approval and accounts.

**Target layout:**
- **Frontend:** a static Vite build on Vercel ([`frontend/vercel.json`](../frontend/vercel.json)).
- **API:** a Docker container on Render ([`render.yaml`](../render.yaml), [`backend/Dockerfile`](../backend/Dockerfile)).
- **Database and sign-in:** Supabase, the existing project.

## Security rules for any public deployment

Stage 14 requires that a public deployment has a login or strict limits, and never exposes saved code or unlimited AI usage.

| Rule | How |
|---|---|
| Sign-in required | Every route except `/health` needs a Supabase sign-in (Stage 12) |
| Saved code stays private | Each user sees only their own projects, reviews and findings; others get 404 |
| Only known people sign up | Supabase: turn off **Allow new users to sign up**, invite users, and turn on **Confirm email** ([supabase-auth.md](supabase-auth.md)) |
| AI spending is capped | <ul><li>Server-wide: 30 manual reviews per hour.</li><li>Pull request reviews: 3 at once and 20 per hour.</li><li>Beginner explanations: 20 per hour and 3 at once.</li><li>Plus a monthly spending limit in the Anthropic console.</li></ul> |
| The database isn't reachable with the public key | Row Level Security on every table; check the Supabase Security Advisor |
| Only the frontend can call the API from a browser | `CORS_ALLOWED_ORIGINS` = the frontend's URL; a wildcard is refused |
| No API schema browsing | `API_DOCS_ENABLED=false` (the image's default) |
| Secrets stay out of the repository | Enter them in Render and Vercel; `render.yaml` marks them `sync: false` |

## Steps, in order

1. **Approvals.** Migrations `0005`–`0007` will change the shared Supabase database, so get team approval and take a backup first.
2. **Supabase settings:**
   - asymmetric JWT signing keys;
   - **Confirm email** on;
   - sign-up off, with an invite for each demo user;
   - the Site URL set to the frontend URL;
   - Row Level Security on for every table.
3. **Migrations.** From a machine with the Supabase `DATABASE_URL`, preview them, then apply:
   ```bash
   cd backend
   alembic upgrade head --sql   # review the SQL first
   alembic upgrade head
   ```
   The image never migrates on start.
4. **Link earlier reviews to their owner:** `python -m app.link_account` (dry run first; see [supabase-auth.md](supabase-auth.md)).
5. **API on Render:**
   1. Create a Blueprint from `render.yaml`.
   2. Enter `DATABASE_URL`, `SUPABASE_URL`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN` and `CORS_ALLOWED_ORIGINS` (the frontend URL).
   3. Deploy manually (`autoDeploy` is off).

   Use an instance that doesn't sleep: background pull request reviews run inside the process.
6. **Frontend on Vercel:**
   1. Import the repository with the root directory set to `frontend`.
   2. Set `VITE_API_BASE_URL` (the Render URL), `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (the publishable key only).
7. **Check:**
   - `https://<api>/health` returns `{"status":"ok"}`;
   - `/docs` returns 404;
   - sign in;
   - run the [demo script](demo-script.md) once, which makes about 8 AI calls.
8. **Anthropic:** set a monthly spending limit.

## What was checked locally (2026-11-23)

The image was built from `backend/Dockerfile`. Checks:
- **Migrations:** applied from the image up to `0007`.
- **Health check:** `/health` returned ok.
- **API docs:** `/docs` and `/openapi.json` returned 404.
- **CORS:** a preflight from the configured origin was allowed; one from another origin got no CORS headers.
- **Sign-in:** `/projects/` returned 401 without it.
- **Process user:** it ran as the non-root `mergemind` user.
- **Scanners:** Semgrep and Bandit both completed inside the container.
- **Configuration tests:** `backend/tests/test_deployment_config.py`, for no secret values, non-root, one worker, and no automatic migrations.

**Not checked:** Render, Vercel or Supabase themselves; nothing was deployed.

## Limits of this setup

- **One API process.** The beginner-explanation limits live in memory, and pull request reviews run in the background inside it. Don't scale to several instances without moving those limits to the database. A restart during a pull request review leaves it `pending`; `python -m app.maintenance` finds it.
- **Large image.** It's about 880 MB, mostly Semgrep.
- **Signed-out sessions.** A signed-out access token stays valid until it expires (one hour by default).

## Rollback

- **App:** redeploy the previous image on Render, or the previous deployment on Vercel.
- **Database:** each migration has a downgrade (`alembic downgrade <revision>`). A downgrade removes the columns that migration added, along with their data, so restore from the backup if needed.
