
"""Stage 8: Test risk scoring through the code review API."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.models.models import User, Project, CodeReview
from app.routes.code_reviews import router


def test_code_review_saves_risk_score():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        user = User(name="Stage Eight Student", email="stage8@example.com")
        db.add(user)
        db.flush()

        project = Project(user_id=user.id, name="Risk Score Test Project")
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
        },
        {
            "title": "Missing Input Tests",
            "category": "testing",
            "severity": "medium",
            "file_name": "test_example.py",
            "line_number": 8,
            "explanation": "Important inputs are not tested.",
            "why_it_matters": "Errors may go undetected.",
            "suggested_fix": "Add tests for invalid inputs.",
        },
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

                result = response.json()
                assert result["review_status"] == "completed"
                assert result["risk_score"] == 70
                assert result["risk_level"] == "high"
                assert result["risk_breakdown"] == {
                    "security": 30,
                    "testing": 15,
                    "maintainability": 0,
                    "performance": 0,
                }

                reviews = client.get("/code-reviews/")
                assert reviews.status_code == 200

                saved_result = reviews.json()[0]
                assert saved_result["risk_score"] == 70
                assert saved_result["risk_level"] == "high"
                assert saved_result["risk_breakdown"]["security"] == 30

        with session_factory() as db:
            saved_review = db.query(CodeReview).one()

            assert saved_review.risk_score == 70
            assert saved_review.risk_level == "high"
            assert saved_review.risk_breakdown == {
                "security": 30,
                "testing": 15,
                "maintainability": 0,
                "performance": 0,
            }

    finally:
        engine.dispose()
