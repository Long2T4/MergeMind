from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import Base, engine
from app.models import models  # noqa: F401 (import needed to register models with Base)
from app.routes import health, users, projects, code_reviews

# Create tables if they don't exist yet. This is fine for an early-stage
# project where the schema is still simple and changing quickly. If the
# schema stabilizes and needs versioned, reversible changes later, that's
# when adding Alembic migrations would be worth the extra complexity.
Base.metadata.create_all(bind=engine)

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
