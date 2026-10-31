# AI Code Review Assistant

A semester project that helps students and beginner developers review their code
before submitting or merging it. Users submit code (or, eventually, a GitHub pull
request) and receive an AI-generated review covering bugs, security issues, bad
practices, and suggested improvements.

The application uses React/Vite, FastAPI, SQLAlchemy, Supabase PostgreSQL,
and an Anthropic review service. It supports manual code submission, saved
review results and history, confidence scoring, and finding-based risk scoring.
Optional project snapshots now provide related import context for reviews.
GitHub pull-request fetching is still future work.

## Project aware review

On New Review, enable **Include related project files**, enter the reviewed
file path, and paste or upload a JSON mapping of project file paths to source
text. MergeMind selects direct local imports and includes them in the AI
request. Ordinary single-file submissions still work without this option.

See [the integration guide](docs/project-aware-review.md) for an example,
limits, API fields, and storage behavior. Snapshots are not saved with the
review and must be attached again for retries.

## Project Structure

```
ai-code-review/
├── frontend/        # React + Vite app
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── backend/         # FastAPI app
│   └── app/
│       ├── routes/
│       ├── services/
│       ├── models/
│       └── database/
├── docs/
└── README.md
```

## Requirements

- [Node.js](https://nodejs.org/) 18+ and npm (for the frontend)
- Python 3.10+ (for the backend)
- A [Supabase](https://supabase.com/) project (free tier is fine) for the database
- An [Anthropic API key](https://console.anthropic.com/settings/keys) for the AI code review feature (Stage 4)

## Database Setup (Supabase)

This project uses Supabase-hosted PostgreSQL. You need your own connection string
in a local `.env` file that is never committed to Git.

1. Create a project at [supabase.com](https://supabase.com/).
2. In the Supabase dashboard, go to **Project Settings → Database → Connection Pooling**
   and copy the **Connection string (URI)** for **Transaction mode** (port `6543`).
   Use the pooler connection, not the direct connection — the direct host is
   IPv6-only and will time out on many networks.
3. Copy `backend/.env.example` to `backend/.env`:
   ```bash
   cd backend
   cp .env.example .env
   ```
4. Open `backend/.env` and set `DATABASE_URL` to your real connection string
   (with your actual password, no square brackets):
   ```
   DATABASE_URL=postgresql://postgres.<project_ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```

`backend/.env` is listed in `.gitignore` and should never be committed.

## AI Review Setup (Anthropic)

The AI review service (Stage 4) calls Claude to analyze submitted code. It's
kept in its own module (`backend/app/services/ai_review_service.py`) so the
rest of the app doesn't depend on any one AI provider — swapping providers
later only means changing that one file.

1. Get an API key at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).
2. Add it to `backend/.env`:
   ```
   ANTHROPIC_API_KEY=your_real_key_here
   ```

Without this key, code submissions still save to the database, but
`review_status` will be `"failed"` and no issues will be generated. The key
is never sent to or used by the frontend — all AI calls happen server-side.

## Running the Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate      # on Windows
# source venv/bin/activate # on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000. On startup it connects to
Supabase and creates any missing tables automatically.

Check http://localhost:8000/health to confirm the server is running.

## Testing the Database Endpoints

With the backend running, you can test the database using curl, the browser,
or the interactive docs at http://localhost:8000/docs.

```bash
# Create a user
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com"}'

# List users
curl http://localhost:8000/users/

# Create a project (use a real user_id from above)
curl -X POST http://localhost:8000/projects/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"name":"Test Project","description":"A test"}'

# List projects
curl http://localhost:8000/projects/
```

If records still appear after restarting the backend, they are genuinely
persisted in Supabase rather than held in memory.

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:5173. It calls the backend's
`/health` endpoint on load and displays the status. You can also paste code,
pick a language, and click "Review Code" to save a submission, run it through
the AI reviewer, and see the resulting issue count appear in the list below.

## Current Stage

**Stage 1 — Project Foundation**: basic frontend/backend scaffolding with a
working health check.

**Stage 2 — Database**: Supabase PostgreSQL connected via SQLAlchemy, with
`User`, `Project`, `CodeReview`, and `ReviewIssue` models and test endpoints
for creating/listing users and projects.

**Stage 3 — Manual Code Submission**: the frontend has a form to paste code
and pick a language. Submitting it saves a `CodeReview` row to Supabase (via
`POST /code-reviews/`) and the page lists all past submissions (via
`GET /code-reviews/`). Submissions are attached to a fixed default project
(id 1) since project management/auth UI doesn't exist yet.

**Stage 4 — AI Review Service**: submitting code now also runs it through
Claude (`backend/app/services/ai_review_service.py`), which returns
structured findings (category, severity, explanation, line number, suggested
fix). Findings are saved as `ReviewIssue` rows linked to the `CodeReview`, and
`review_status` is set to `completed` or `failed` accordingly. The AI logic is
isolated in one module so the provider can be swapped later without touching
routes or the database layer. Each finding now stores `title`,
`explanation`, and `why_it_matters` as separate fields (rather than one
merged paragraph), plus `category`, `severity`, and an optional
`line_number`.

**Stage 5 — Review Results UI**: clicking a review in the list opens a
Review Detail view — status pill, total issue count, and a severity
breakdown (high/medium/low), followed by expandable issue cards. Each card
follows a "What's wrong? → Why does it matter? → How do I fix it?" learning
flow, with a monospace line-reference chip when available. Review History and
interim Learning analytics were added in later stages;
GitHub retrieval remains future work.

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full stage roadmap
and standing future requirements (Developer Learning feature, GitHub PR
review goal) that later stages must account for.
