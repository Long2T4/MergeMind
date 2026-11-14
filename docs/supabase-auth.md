# Supabase Auth setup (Stage 12)

MergeMind uses Supabase Auth for sign-in. The browser signs in with Supabase and sends the resulting access token to the backend. The backend checks the token's signature against the project's public keys, maps it to a local user, and shows only that user's projects and reviews.

This guide covers the Supabase settings, the environment variables, and how to link accounts created before Stage 12.

## How sign-in works

1. The frontend signs in with email and password through `@supabase/supabase-js`, using the project's publishable (anon) key.
2. Every API call sends `Authorization: Bearer <access token>`.
3. The backend middleware verifies the token:
   - the signature is checked with the project's public keys from `https://<project>.supabase.co/auth/v1/.well-known/jwks.json`;
   - only asymmetric algorithms (`RS256`, `ES256`) are accepted;
   - the audience must be `authenticated` and the issuer `https://<project>.supabase.co/auth/v1`;
   - the token must have `exp`, `iat`, `sub`, `aud` and `iss`, a UUID subject, and the `authenticated` role;
   - expired, unsigned, tampered and `HS256` tokens are refused with 401.
4. Each route then loads the local user for that token and checks ownership: a user's data is everything under a project with their `user_id`. Another user's review, project or finding gets the same 404 as a missing one.

The backend needs no Supabase secret. `/health` and the API docs (`/docs`, `/openapi.json`) don't need a token. The old `/users/` endpoints are disabled (403).

## Supabase settings

Change these in the Supabase dashboard. Menu names can move as Supabase updates its dashboard.

### 1. Asymmetric JWT signing keys (required)

The backend refuses tokens signed with the legacy shared JWT secret (`HS256`). Under **Project Settings → JWT Keys**:

1. If the project still uses the legacy JWT secret, start the migration to JWT signing keys. Supabase creates an asymmetric standby key (ECC P-256 by default; RSA also works).
2. Rotate keys so the asymmetric key is the current key.
3. Check `https://<project>.supabase.co/auth/v1/.well-known/jwks.json` lists the key.

Users who signed in before the rotation get "Invalid or expired session" until they sign in again.

### 2. Email confirmation (required before anyone else uses the app)

Under **Authentication → Sign In / Providers → Email**, turn on **Confirm email**. Without it, anyone could register an address they don't own.

Set **Authentication → URL Configuration → Site URL** to the frontend's address, such as `http://localhost:5173` locally, so confirmation links open MergeMind.

### 3. Who can sign up (recommended)

Every new account can run AI reviews, which cost money. The server-wide limits (30 manual reviews and 20 pull request reviews per hour, 3 pull request reviews at once) cap the spending. However, one account can use up the hourly allowance for everyone. For a demo or a shared server, keep sign-up invite-only:

- turn off **Allow new users to sign up** under **Authentication → Sign In / Providers**;
- add people with **Authentication → Users → Invite user**.

### 4. Database access through the Data API (check before deploying)

The publishable key is public: it ships in the browser bundle. Supabase's Data API (PostgREST) accepts it, so MergeMind's tables must not be readable through that API. The migrations handle this:

- the four original app tables had Row Level Security enabled with no policies when Stage 10 checked them on 2026-11-05;
- `0003` and `0004` turn on Row Level Security for `alembic_version`, `pull_requests` and `pull_request_files`, and revoke the `anon` and `authenticated` roles' access to them;
- `0005` adds no tables.

The backend connects as the tables' owner, so Row Level Security doesn't affect it. Before deploying, confirm in **Database → Tables** or the **Security Advisor** that every MergeMind table still shows RLS enabled. Any table added later, for example in Stage 13, needs the same protection as `0004`.

## Environment variables

| File | Variable | Value |
|---|---|---|
| `backend/.env` | `SUPABASE_URL` | `https://<project>.supabase.co`: https, no path. The backend refuses to start without a valid value |
| `frontend/.env.local` | `VITE_SUPABASE_URL` | The same project URL |
| `frontend/.env.local` | `VITE_SUPABASE_ANON_KEY` | The publishable (anon) key from **Project Settings → API Keys** |
| `frontend/.env.local` | `VITE_API_BASE_URL` | Optional; defaults to `http://localhost:8000` |

Copy [`backend/.env.example`](../backend/.env.example) and [`frontend/.env.example`](../frontend/.env.example) to start. Both real files are ignored by Git.

**Never put these in a `VITE_` variable or in the repository:** the secret or `service_role` key, the legacy JWT secret, or the database password. Anything in a `VITE_` variable is visible to every visitor.

## Accounts created before Stage 12

Users created before Stage 12 have no Supabase identity. For example, user 1 owns the reviews made during Stages 1–11. MergeMind never links accounts by email: the person could be anyone who registered that address. Signing in with such an email shows **"This account needs to be linked"**, and the user's data stays unchanged.

To link an account, after confirming the person really owns it:

1. The person signs up or signs in once with Supabase. Copy their user ID (a UUID) from **Authentication → Users**.
2. From `backend/` (it uses `DATABASE_URL` from `backend/.env`), preview the link:

   ```bash
   python -m app.link_account --user-id 1 --auth-user-id <uuid>
   ```

   This is a dry run. It prints the email, the number of projects and reviews that would become theirs, and changes nothing.
3. If that's correct, run it again with `--apply`.

The command refuses to link a user who is already linked to a different Supabase account. It also refuses a Supabase account that is already linked to another user. To undo a link, set that user's `auth_user_id` back to `NULL` in the database.

## Signing out

**Log out** is at the bottom of the sidebar (inside the menu on phones). Signing out ends the Supabase session in the browser. An access token that was already issued stays valid until it expires (one hour by default), because the backend checks signatures and doesn't track sessions.

## Testing without Supabase

Automated tests never contact Supabase:
- backend tests sign their own RS256 and ES256 tokens with test keys;
- frontend tests replace the Supabase client with a stub.
