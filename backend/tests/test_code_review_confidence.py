
"""Stage 7: Test confidence scoring through the code review API."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.models.models import User, Project, ReviewIssue
from app.routes.code_reviews import router


def test_code_review_saves_confidence():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        user = User(name="Stage Seven Student", email="stage7@example.com")
        db.add(user)
        db.flush()

        project = Project(user_id=user.id, name="Confidence Test Project")
        db.add(project)
        db.commit()
        project_id = project.id

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    sample_issues = [
        {
            "title": "Possible SQL Injection",
            "category": "security",
            "severity": "high",
            "file_name": "example.py",
            "line_number": 3,
            "explanation": "User input is used directly in a query.",
            "why_it_matters": "This could allow SQL injection.",
            "suggested_fix": "Use parameterized queries.",
        }
    ]

    try:
        with patch(
            "app.routes.code_reviews.review_code",
            return_value=sample_issues,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/code-reviews/",
                    json={
                        "project_id": project_id,
                        "submitted_code": "print('hello')",
                        "programming_language": "python",
                    },
                )

                assert response.status_code == 200
                assert response.json()["review_status"] == "completed"

                reviews = client.get("/code-reviews/")
                assert reviews.status_code == 200

                issues = reviews.json()[0]["issues"]
                assert len(issues) == 1
                assert issues[0]["confidence_score"] == 20
                assert issues[0]["confidence_level"] == "low"
                assert issues[0]["confidence_evidence"] == {"ai": True}

        with session_factory() as db:
            saved_issue = db.query(ReviewIssue).one()
            assert saved_issue.confidence_score == 20
            assert saved_issue.confidence_level == "low"
            assert saved_issue.confidence_evidence == {"ai": True}

    finally:
        engine.dispose()
