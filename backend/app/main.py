from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import models  # noqa: F401 (import needed to register models with Base)
from app.routes import health, users, projects, code_reviews, pull_request_reviews, review_history

# The schema is managed by Alembic migrations (backend/alembic/), not created
# at startup: create_all() can't add columns to existing tables. Before
# running the app, apply migrations from backend/ with: alembic upgrade head

app = FastAPI(title="AI Code Review Assistant API")

# Allow the Vite dev server to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(code_reviews.router)
app.include_router(pull_request_reviews.router)
app.include_router(review_history.router)
