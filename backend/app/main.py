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


app = FastAPI(title="AI Code Review Assistant API", lifespan=lifespan)


# Stage 12 (install before CORS so browser preflights/errors retain CORS headers)
from app.stage12.bootstrap import install_stage12
install_stage12(app)
# Allow the Vite dev server to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
