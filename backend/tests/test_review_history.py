"""FastAPI endpoint tests: run from backend/: pytest tests/test_review_history.py -q

Uses in-memory SQLite, not Supabase, and never calls the AI service.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.models.models import User, Project, CodeReview, ReviewIssue
from app.routes.review_history import router


def make_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        user = User(name="Stage Six Student", email="stage6@example.com")
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, name="History Project")
        db.add(project)
        db.flush()
        review = CodeReview(
            project_id=project.id,
            submitted_code="print('hello')",
            programming_language="python",
            review_status="completed",
        )
        db.add(review)
        db.flush()
        db.add(ReviewIssue(
            review_id=review.id,
            category="Security",
            severity="high",
            explanation="Example security finding",
            status="open",
        ))
        db.commit()
    finally:
        db.close()

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine


def test_history_list_and_filters():
    client, engine = make_client()
    try:
        result = client.get("/review-history/")
        assert result.status_code == 200
        body = result.json()
        assert body["total"] == 1
        assert body["items"][0]["programming_language"] == "python"
        assert len(body["items"][0]["issues"]) == 1
        assert client.get("/review-history/?language=java").json()["total"] == 0
        assert client.get("/review-history/?q=hello").json()["total"] == 1
        assert client.get("/review-history/?offset=1").json()["items"] == []
    finally:
        client.close()
        engine.dispose()


def test_history_statistics():
    client, engine = make_client()
    try:
        result = client.get("/review-history/stats")
        assert result.status_code == 200
        assert result.json() == {
            "total_reviews": 1,
            "completed_reviews": 1,
            "total_issues": 1,
            "high_severity_issues": 1,
        }
    finally:
        client.close()
        engine.dispose()


def test_invalid_page_inputs_rejected():
    client, engine = make_client()
    try:
        assert client.get("/review-history/?limit=999").status_code == 422
        assert client.get("/review-history/?offset=-2").status_code == 422
    finally:
        client.close()
        engine.dispose()
