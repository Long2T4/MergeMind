import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import models  # noqa: F401 (import needed to register models with Base)
from app.routes import health, projects, code_reviews, pull_request_reviews, review_history
from app.stage12.security import validate_auth_config

# The schema is managed by Alembic migrations (backend/alembic/), not created
# at startup: create_all() can't add columns to existing tables. Before
# running the app, apply migrations from backend/ with: alembic upgrade head

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Stage 12: refuse to start without a valid SUPABASE_URL, with a clear
    # message, instead of failing every signed-in request later.
    validate_auth_config()
    yield


DEFAULT_CORS_ORIGINS = ["http://localhost:5173"]  # the Vite dev server


def cors_allowed_origins() -> list[str]:
    """Browser origins allowed to call the API (Stage 14 deployment).

    CORS_ALLOWED_ORIGINS is a comma-separated list, e.g. the deployed
    frontend's https URL. A wildcard is refused: any website could then call
    the API with a signed-in user's token.
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if "*" in origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must list the frontend's origins, not *")
    return origins or DEFAULT_CORS_ORIGINS


def api_docs_enabled() -> bool:
    """/docs and /openapi.json: on by default; API_DOCS_ENABLED=false turns them off in production."""
    return os.getenv("API_DOCS_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")


_docs = api_docs_enabled()
app = FastAPI(
    title="AI Code Review Assistant API",
    lifespan=lifespan,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)


# Stage 12 (install before CORS so browser preflights/errors retain CORS headers)
from app.stage12.bootstrap import install_stage12
install_stage12(app)
# Only the frontend may call this API from a browser (localhost:5173 locally).
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
# Stage 12: users are created from verified sign-ins (GET /account/me), so the
# old open /users/ endpoints aren't registered. The middleware also answers
# /users with 403.
app.include_router(projects.router)
app.include_router(code_reviews.router)
app.include_router(pull_request_reviews.router)
app.include_router(review_history.router)
