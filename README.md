# MergeMind

MergeMind is an AI code review platform for students and junior developers. It reviews submitted code and explains each finding: what is wrong, why it matters, and how to fix it. Reviews are saved, so developers can revisit them and see which kinds of issues keep appearing.

MergeMind is a university senior capstone project built by a student team. It runs locally today. It has not been deployed, and it isn't ready to host private code (see [Current limitations](#current-limitations)).

> **Stage 12 (accounts, finding outcomes and learning) is described below but not merged yet.** It is in pull request [#15](https://github.com/Long2T4/MergeMind/pull/15) (branch `feature/stage-12-auth-feedback-learning`). On `main`, the app has no sign-in.

## Why MergeMind

Beginners often get no code review, or feedback that points out a problem without teaching anything. MergeMind focuses on explanation. It also tells users how much evidence supports each finding and what its scores do and don't mean.

**Target users:** students, junior developers, and anyone learning to write better code.

## Current features

- **Accounts:** sign up and sign in with email and password through Supabase Auth. Each user sees only their own projects, reviews, findings and statistics.
- **Projects:** create and rename projects. The project you select is used by default for new reviews.
- **Code review:** paste code or upload a file, then choose one of your projects and a language.
- **Pull request review:** paste a public GitHub pull request URL. MergeMind reviews the changed files one by one, focuses on the changed lines, and shows the repository, title, author, commit and each file's status. The page shows progress while files are reviewed.
- **AI findings:** each finding has a category, severity, explanation, reason it matters, suggested fix, and line reference when available.
- **Saved results:** a results page with severity counts, category filters, flagged code, and syntax-highlighted fixes.
- **Finding outcomes:** mark each finding open, fixed, dismissed or false positive. "Fixed" is self-reported, not verified. MergeMind records who changed it and when.
- **Review history:** search, status and language filters, pagination, and an issues-per-review chart. Filters stay in the URL.
- **Confidence scores:** each finding shows how much evidence supports it.
- **Merge risk scores:** each completed review gets a 0–100 score based on its findings.
- **Project-aware review:** optionally attach a JSON snapshot of project files. MergeMind finds the files directly imported by the reviewed code and gives them to the AI as context.
- **Learning page:** category counts, categories repeated across reviews, activity and per-review counts, plus your finding outcomes by category. Everything is calculated from your saved reviews.
- **Retry:** a failed review can be retried with its original code.
- **Responsive dark interface:** a sidebar layout with keyboard support and error, loading and empty states.

### What the scores mean

- **Confidence** measures supporting evidence. It isn't the probability that a finding is correct. Only AI evidence exists today, so every new finding currently scores 20/low.
- **Merge risk** is a heuristic based on findings. It isn't the probability of a failed merge. Despite the feature's "PR Risk Scoring" name, it doesn't use real pull request data yet.

## Technology

| Area | Technology |
|---|---|
| Frontend | React 18, Vite 5, React Router 6, highlight.js, custom CSS |
| Backend | Python, FastAPI, SQLAlchemy 2, Pydantic 2, Uvicorn |
| Database | PostgreSQL on Supabase |
| Sign-in | Supabase Auth (`@supabase/supabase-js` in the browser; tokens verified with PyJWT against the project's public keys) |
| AI | Anthropic Claude (`claude-haiku-4-5-20251001`), called only from the backend |
| Testing | pytest, Vitest, Testing Library, jsdom |

## Architecture

```text
React frontend (Vite, port 5173)
        |
        |  JSON over HTTP
        v
FastAPI backend (port 8000)
  auth middleware: verifies the Supabase access token on every request
  routes: health, account, projects, code_reviews, pull_request_reviews, review_history
          (each loads the signed-in user and checks project ownership)
        |
        |-- project_context_service   selects directly imported files
        |-- github_service            reads public pull requests (read-only)
        |-- pr_review_service         reviews a pull request file by file
        |-- ai_review_service         builds the prompt and parses findings
        |-- confidence_service        scores each finding's evidence
        |-- risk_score_service        scores each review
        |
        +--> PostgreSQL (Supabase) through SQLAlchemy
        +--> Anthropic API
        +--> GitHub REST API (public pull requests)
```

```text
backend/
  app/
    database/    Database connection
    models/      SQLAlchemy models and Pydantic schemas
    routes/      API endpoints
    services/    AI review, context, confidence and risk logic
    stage12/     Sign-in token checks, ownership helpers and /account routes
  tests/
frontend/
  src/
    components/  Shared UI, layout and review components
    constants/   Shared languages, categories and project defaults
    hooks/       History filters and project loading
    lib/         Highlighting, formatting and learning calculations
    pages/       Routed pages
    services/    All backend API calls
    stage12/     Sign-in screen, account context, projects, outcomes and learning
    test/        Frontend tests
docs/            Project plan, usage guides, reviews and lessons learned
```

## How a review works

1. The user submits code, with an optional project snapshot.
2. The backend checks size limits and rejects invalid input before saving anything.
3. If a snapshot was supplied, the backend selects directly imported files. It reads imports statically and never runs the code.
4. A `pending` review is saved.
5. Claude receives trusted instructions separately from the code, which is sent as untrusted JSON data.
6. The response is parsed, and categories and severities are normalized.
7. Findings are saved with confidence scores, and the review gets a risk score and a `completed` status.
8. If the AI call fails, the review is saved as `failed` and can be retried.

Selected code and context files are sent to Anthropic. Snapshots aren't saved with the review, so attach them again when retrying.

### Pull request reviews

1. The user submits a public `https://github.com/{owner}/{repo}/pull/{number}` URL. The backend builds its own GitHub API addresses from it and never requests the URL itself.
2. Before saving anything, the backend checks the project, reads the pull request with its `GITHUB_TOKEN`, rejects private, missing and oversized pull requests (over 30 changed files or 3,000 changed lines), and picks the files to review: the first 10 Python, JavaScript, TypeScript, Java, C or C++ files. Removed, generated and binary files are skipped.
3. The pull request and a `pending` review are saved, and the request returns. A background task then reviews each file at the pull request's exact head commit, with the files it directly imports as context, and saves its findings as it goes.
4. The AI is told which lines changed. Findings on or next to changed lines are kept. A few medium or high findings elsewhere in a file (at most 2) are kept and labeled "outside the diff"; others are dropped.
5. If a file fails, the others continue. The review is `completed` if at least one file was reviewed, and `failed` otherwise. MergeMind never posts anything to GitHub.

## Pages

| Route | Page |
|---|---|
| `/` | Home dashboard with statistics and recent reviews |
| `/reviews/new` | New review |
| `/reviews/:reviewId` | Review results |
| `/history` | Review history |
| `/learning` | Learning page |
| `/projects` | Create, rename and select projects |

Every page needs a sign-in. The signed-in email and **Log out** are at the bottom of the sidebar.

## API endpoints

Interactive API docs are available at `http://localhost:8000/docs` while the backend is running.

Every endpoint except `/health` and the API docs needs `Authorization: Bearer <Supabase access token>`, and returns only the signed-in user's data. See [Supabase Auth setup](docs/supabase-auth.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check (no sign-in needed) |
| GET | `/account/me` | The signed-in user; creates the local user on first sign-in |
| GET, POST | `/account/projects` | List or create your projects |
| GET, PATCH | `/account/projects/{id}` | Read or rename one of your projects |
| GET | `/account/reviews/{id}/findings` | A review's findings and their outcomes |
| PATCH | `/account/findings/{id}` | Set a finding's outcome: `open`, `fixed`, `dismissed` or `false_positive` |
| GET | `/account/learning` | Your outcome and category statistics |
| GET, POST | `/projects/` | List or create your projects (older endpoint) |
| POST | `/code-reviews/` | Create and run a review |
| POST | `/pull-request-reviews/` | Start a review of a public GitHub pull request (returns 202; poll the review for progress) |
| GET | `/code-reviews/` | List your reviews with their issues |
| GET | `/review-history/` | Paged review summaries with search and filters |
| GET | `/review-history/stats` | Totals for the same filters |
| GET | `/review-history/{id}` | One full review |

The old `/users/` endpoints are disabled: users are created from verified sign-ins.

`POST /code-reviews/` accepts `project_id`, `submitted_code`, `programming_language`, and optional `project_context`. See the [project-aware review guide](docs/project-aware-review.md) for the format and limits.

| Response | Meaning |
|---|---|
| 401 | No sign-in token, or an invalid or expired one |
| 403 | The `/users/` endpoints, or a sign-in without an email |
| 404 | The project, review or finding doesn't exist or belongs to another user, or the pull request is missing or not public |
| 409 | MergeMind already has data under this email, and an administrator must [link the account](docs/supabase-auth.md#accounts-created-before-stage-12). Also used when the same pull request is already being reviewed |
| 429 | Over a server-wide limit: 30 manual reviews per hour, or 3 pull request reviews at once and 20 per hour |
| 503 | `POST /pull-request-reviews/`: `GITHUB_TOKEN` isn't set, GitHub is unavailable, or GitHub's rate limit was reached |
| 422 | Invalid input or a request over the size limits |
| 200 with `review_status: "failed"` | The AI review failed or its answer was unusable; the review can be retried |

## Local setup

### Requirements

- Node.js 18 or newer
- Python 3.10 or newer
- A [Supabase](https://supabase.com/) project, for the database and sign-in. Set up its Auth as described in [Supabase Auth setup](docs/supabase-auth.md): asymmetric JWT signing keys are required
- An [Anthropic API key](https://console.anthropic.com/settings/keys)

### Environment variables

Copy `backend/.env.example` to `backend/.env`, and `frontend/.env.example` to `frontend/.env.local`. Both files are ignored by Git, so never commit them.

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SUPABASE_URL` | Yes | `https://<project>.supabase.co`. The backend checks sign-in tokens against this project and refuses to start without it |
| `ANTHROPIC_API_KEY` | For AI reviews | Without it, submissions save but end as `failed` |
| `GITHUB_TOKEN` | For pull request reviews | A fine-grained token with read-only access to public repositories only. Server-side; never sent to the browser |
| `AI_PROVIDER` | No | Defaults to `anthropic`, the only supported provider |
| `VITE_SUPABASE_URL` | Yes (frontend) | The same project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes (frontend) | The project's publishable (anon) key. It is public by design; never use the secret or `service_role` key here |
| `VITE_API_BASE_URL` | No | Frontend setting; defaults to `http://localhost:8000` |

### Database

In Supabase, open **Project Settings**, then **Database**, then **Connection Pooling**. Copy the Transaction mode URI (port `6543`). The direct database host can be IPv6-only and time out on many networks.

```text
DATABASE_URL=postgresql://postgres.<project_ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

The schema is managed with [Alembic](https://alembic.sqlalchemy.org/) migrations in `backend/alembic/`. The backend no longer creates tables when it starts, so apply migrations before the first run and after pulling new ones:

```bash
cd backend
alembic upgrade head        # apply migrations
alembic current             # show the database's version
alembic upgrade head --sql  # preview the SQL without running it
```

The baseline migration is safe for a database created before migrations existed. It creates only missing tables, adds only missing nullable columns (such as the Stage 7 and 8 score columns), and never drops or changes existing data. Back up a shared database before migrating it anyway.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

If the server stops in the middle of a review, that review can stay `pending`. To find such reviews, run `python -m app.maintenance` from `backend/`. It only lists them by default; add `--apply` to mark them `failed` so they can be retried. Nothing runs automatically.

### First-run data

Sign up in the app, open **Projects**, and create a project. New Review asks you to create one first if you have none.

Reviews made before Stage 12 belong to users with no sign-in. Signing in with one of those emails shows "This account needs to be linked". An administrator can link it with `python -m app.link_account`, after checking who owns the account; see [Supabase Auth setup](docs/supabase-auth.md#accounts-created-before-stage-12).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`. The backend only accepts browser requests from this address.

## Running tests

```bash
# Backend, from backend/
pip install -r requirements-dev.txt
python -m pytest tests -q

# Frontend, from frontend/
npm test
npm run build
```

Tests use SQLite, mocked AI responses, a fake GitHub and test-signed sign-in tokens, so they don't need Supabase, an Anthropic key or a GitHub token. Migration tests and the Stage 12 access and first-sign-in tests also run against PostgreSQL when `MIGRATION_TEST_DATABASE_URL` points at a disposable local database. They drop every table there and refuse any non-local address, so never point it at Supabase.

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on every pull request and push to `main`:
- backend tests on Ubuntu and Windows;
- migration tests on a throwaway PostgreSQL;
- frontend tests and the production build.

CI needs no secrets.

The full flow was verified live on 2026-11-05, against Supabase and the Anthropic API. It covered the migrations, a normal review, a review with project context, History, and the Learning data. See the [Stage 10 report](docs/reviews/stage-10-foundation-review.md#live-review-results). Pull request reviews were verified live on 2026-11-09 with [a demo pull request](https://github.com/Long2T4/mergemind-demo/pull/1); see the [Stage 11 report](docs/reviews/stage-11-github-pr-review-review.md#live-verification-results).

## Current limitations

- **Not deployed:** sign-in and per-user access exist (Stage 12), but the backend still allows only `http://localhost:5173` as a browser origin, and nothing has been tested on a server. See the [pre-deployment checklist](docs/reviews/stage-12-accounts-feedback-review.md#before-deployment). Selected code is sent to Anthropic, so don't use private code.
- **AI spending:** limits are server-wide, not per user: 30 manual reviews per hour, and for pull requests 3 at once and 20 per hour (at most 200 AI calls). One account can use up the allowance for everyone, so keep sign-up invite-only on a shared server. Also set a monthly spend limit in the Anthropic console.
- **Sessions:** after **Log out**, an access token that was already issued stays valid until it expires (one hour by default).
- **Public pull requests only:** no private repositories, OAuth or webhooks, and nothing is posted back to GitHub. Large pull requests are rejected rather than partly reviewed, and at most 10 files are reviewed.
- **Background reviews:** pull request reviews run inside the backend process, without a job queue. If the server stops mid-review, the review stays `pending`; `python -m app.maintenance` finds it.
- **No static analysis:** Semgrep and Bandit aren't integrated, so confidence doesn't yet separate strong findings from weak ones.
- **Outcomes are self-reported:** "Fixed" means the user said so; MergeMind doesn't check the code.
- **Learning page is interim:** it shows category counts and outcomes for your own reviews, not a per-developer profile. It counts the project owner, not the code's author. A repeated category doesn't prove the same mistake, and a lower count doesn't prove improvement.
- **AI findings can be wrong:** review them before acting on them. Line numbers come from the model and can be imperfect. Pull request files are sent with numbered lines, and impossible line numbers are dropped; in the live test this took exact lines from 1 of 5 to 5 of 6.
- **Direct imports only:** project context doesn't follow imports recursively.
- **Very long reviews:** if the AI's answer reaches its output limit, the review is saved as `failed` rather than partially. Submit less code and retry.

## Project status

Stages 1–11 and a frontend redesign are complete and merged. Stage 12 is implemented and tested locally; its pull request isn't merged yet.

| Stage | Title | Status |
|---|---|---|
| 1–5 | Foundation, database, submission, AI review, results UI | Complete |
| 6 | Review History | Complete |
| 7 | Confidence Scoring | Complete |
| 8 | PR Risk Scoring | Complete |
| 9 | Project-Aware Review (supplied snapshots) | Complete |
| 10 | Foundation and Stability | Complete: CI, migrations, reliability fixes, live verification |
| 11 | GitHub Pull Request Integration | Complete: verified live on a demo PR; merged (PR #13) |
| 12 | Developer Feedback and Learning | Implemented locally on top of PR #15; **not merged**. Accounts, per-user data, projects, finding outcomes and Learning outcomes. Not verified against live Supabase yet |
| 13 | Static Analysis Integration | Planned |
| 14 | Evaluation and Final Demo | Planned |

Planned work isn't available yet. It includes Semgrep and Bandit evidence, and a measured evaluation of review quality. See the full [project plan](docs/PROJECT_PLAN.md).

## Contributors

This table lists authors of the merged pull requests in Git. It doesn't capture every contribution, such as planning, testing and discussion.

| Work | Pull request | Author in Git |
|---|---|---|
| Initial project | `159a5a2` | Long Truong |
| Review History | [#1](https://github.com/Long2T4/MergeMind/pull/1) | bhavesh70655 |
| Review History fixes | [#2](https://github.com/Long2T4/MergeMind/pull/2) | Long Truong |
| Confidence Scoring | [#3](https://github.com/Long2T4/MergeMind/pull/3) | Yudith Vazquez-Jacinto |
| PR Risk Scoring | [#4](https://github.com/Long2T4/MergeMind/pull/4) | Yudith Vazquez-Jacinto |
| Frontend redesign | [#5](https://github.com/Long2T4/MergeMind/pull/5) | Long Truong |
| Project-Aware Review | [#6](https://github.com/Long2T4/MergeMind/pull/6), [#7](https://github.com/Long2T4/MergeMind/pull/7) | Akhil Sajja |
| Windows test fix | [#8](https://github.com/Long2T4/MergeMind/pull/8) | Long Truong |
