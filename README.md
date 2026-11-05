# MergeMind

MergeMind is an AI code review platform for students and junior developers. It reviews submitted code and explains each finding: what is wrong, why it matters, and how to fix it. Reviews are saved, so developers can revisit them and see which kinds of issues keep appearing.

MergeMind is a university senior capstone project built by a student team. It runs locally today. It has not been deployed, and it isn't ready to host private code (see [Current limitations](#current-limitations)).

## Why MergeMind

Beginners often get no code review, or feedback that points out a problem without teaching anything. MergeMind focuses on explanation. It also tells users how much evidence supports each finding and what its scores do and don't mean.

**Target users:** students, junior developers, and anyone learning to write better code.

## Current features

- **Code review:** paste code or upload a file, then choose a project and language.
- **AI findings:** each finding has a category, severity, explanation, reason it matters, suggested fix, and line reference when available.
- **Saved results:** a results page with severity counts, category filters, flagged code, and syntax-highlighted fixes.
- **Review history:** search, status and language filters, pagination, and an issues-per-review chart. Filters stay in the URL.
- **Confidence scores:** each finding shows how much evidence supports it.
- **Merge risk scores:** each completed review gets a 0–100 score based on its findings.
- **Project-aware review:** optionally attach a JSON snapshot of project files. MergeMind finds the files directly imported by the reviewed code and gives them to the AI as context.
- **Learning page:** category counts, categories repeated across reviews, activity, and per-review counts, all calculated from saved reviews.
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
| AI | Anthropic Claude (`claude-haiku-4-5-20251001`), called only from the backend |
| Testing | pytest, Vitest, Testing Library, jsdom |

## Architecture

```text
React frontend (Vite, port 5173)
        |
        |  JSON over HTTP
        v
FastAPI backend (port 8000)
  routes: health, users, projects, code_reviews, review_history
        |
        |-- project_context_service   selects directly imported files
        |-- ai_review_service         builds the prompt and parses findings
        |-- confidence_service        scores each finding's evidence
        |-- risk_score_service        scores each review
        |
        +--> PostgreSQL (Supabase) through SQLAlchemy
        +--> Anthropic API
```

```text
backend/
  app/
    database/    Database connection
    models/      SQLAlchemy models and Pydantic schemas
    routes/      API endpoints
    services/    AI review, context, confidence and risk logic
  tests/
frontend/
  src/
    components/  Shared UI, layout and review components
    constants/   Shared languages, categories and project defaults
    hooks/       History filters and project loading
    lib/         Highlighting, formatting and learning calculations
    pages/       Routed pages
    services/    All backend API calls
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

## Pages

| Route | Page |
|---|---|
| `/` | Home dashboard with statistics and recent reviews |
| `/reviews/new` | New review |
| `/reviews/:reviewId` | Review results |
| `/history` | Review history |
| `/learning` | Learning page |
| `/projects` | Read-only project list |

## API endpoints

Interactive API docs are available at `http://localhost:8000/docs` while the backend is running.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET, POST | `/users/` | List or create users |
| GET, POST | `/projects/` | List or create projects |
| POST | `/code-reviews/` | Create and run a review |
| GET | `/code-reviews/` | List all reviews with their issues |
| GET | `/review-history/` | Paged review summaries with search and filters |
| GET | `/review-history/stats` | Totals for the same filters |
| GET | `/review-history/{id}` | One full review |

`POST /code-reviews/` accepts `project_id`, `submitted_code`, `programming_language`, and optional `project_context`. See the [project-aware review guide](docs/project-aware-review.md) for the format and limits.

| Response | Meaning |
|---|---|
| 404 | The project (or, for `POST /projects/`, the user) doesn't exist |
| 409 | `POST /users/` was given an email that's already taken |
| 422 | Invalid input or a request over the size limits |
| 200 with `review_status: "failed"` | The AI review failed or its answer was unusable; the review can be retried |

## Local setup

### Requirements

- Node.js 18 or newer
- Python 3.10 or newer
- A [Supabase](https://supabase.com/) project
- An [Anthropic API key](https://console.anthropic.com/settings/keys)

### Environment variables

Copy `backend/.env.example` to `backend/.env`. This file holds secrets and is ignored by Git, so never commit it.

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | For AI reviews | Without it, submissions save but end as `failed` |
| `AI_PROVIDER` | No | Defaults to `anthropic`, the only supported provider |
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

A new database has no users or projects, and the app can't create them yet. With the backend running, create one of each:

```bash
curl -X POST http://localhost:8000/users/ -H "Content-Type: application/json" -d "{\"name\":\"Test User\",\"email\":\"test@example.com\"}"

curl -X POST http://localhost:8000/projects/ -H "Content-Type: application/json" -d "{\"user_id\":1,\"name\":\"Test Project\",\"description\":\"A test project\"}"
```

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

Tests use SQLite and mocked AI responses, so they don't need Supabase or an Anthropic key. Migration tests also run against PostgreSQL when `MIGRATION_TEST_DATABASE_URL` points at a disposable local database. They drop every table there and refuse any non-local address, so never point it at Supabase.

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on every pull request and push to `main`:
- backend tests on Ubuntu and Windows;
- migration tests on a throwaway PostgreSQL;
- frontend tests and the production build.

CI needs no secrets.

The full flow was verified live on 2026-11-05, against Supabase and the Anthropic API. It covered the migrations, a normal review, a review with project context, History, and the Learning data. See the [Stage 10 report](docs/reviews/stage-10-foundation-review.md#live-review-results).

## Current limitations

- **No authentication:** every endpoint is open, and anyone who can reach the API can read all reviews. Don't host this version or use it with private code.
- **No GitHub integration:** MergeMind can't read pull requests or repositories yet. Project context comes from a manually supplied JSON snapshot.
- **No static analysis:** Semgrep and Bandit aren't integrated, so confidence doesn't yet separate strong findings from weak ones.
- **No developer feedback:** findings can't be marked fixed, dismissed or false positive.
- **Learning page is interim:** it shows category data, not per-developer progress. A repeated category doesn't prove the same mistake, and a lower count doesn't prove improvement.
- **AI findings can be wrong:** review them before acting on them. Line numbers come from the model and may be inaccurate.
- **Direct imports only:** project context doesn't follow imports recursively.
- **Very long reviews:** if the AI's answer reaches its output limit, the review is saved as `failed` rather than partially. Submit less code and retry.

## Project status

Stages 1–10 and a frontend redesign are complete. Stage 11 is next.

| Stage | Title | Status |
|---|---|---|
| 1–5 | Foundation, database, submission, AI review, results UI | Complete |
| 6 | Review History | Complete |
| 7 | Confidence Scoring | Complete |
| 8 | PR Risk Scoring | Complete |
| 9 | Project-Aware Review (supplied snapshots) | Complete |
| 10 | Foundation and Stability | Complete: CI, migrations, reliability fixes, live verification |
| 11 | GitHub Pull Request Integration | Planned |
| 12 | Developer Feedback and Learning | Planned |
| 13 | Static Analysis Integration | Planned |
| 14 | Evaluation and Final Demo | Planned |

Planned work isn't available yet. It includes reviews of public GitHub PR URLs, accounts with per-user data, finding outcomes, Semgrep and Bandit evidence, and a measured evaluation of review quality. See the full [project plan](docs/PROJECT_PLAN.md).

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
