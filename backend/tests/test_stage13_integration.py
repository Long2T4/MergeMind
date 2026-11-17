
"""Stage 13: Integration tests for Claude, Semgrep, and Bandit reviews."""

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
from auth_helpers import act_as


def create_test_app():
    """Create an isolated database and authenticated test application."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        user = User(
            name="Stage Thirteen Student",
            email="stage13@example.com",
        )
        db.add(user)
        db.flush()

        project = Project(
            user_id=user.id,
            name="Stage 13 Security Test",
        )
        db.add(project)
        db.commit()

        owner_id = user.id
        project_id = project.id

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    act_as(app, owner_id)

    return app, engine, session_factory, project_id


def sample_ai_finding():
    """Return a finding detected by Claude."""

    return {
        "title": "Unsafe eval",
        "category": "security",
        "severity": "medium",
        "file_name": "example.py",
        "line_number": 2,
        "explanation": "Unsafe execution of user input.",
        "why_it_matters": "Potential code injection.",
        "suggested_fix": "Avoid eval.",
    }


def sample_semgrep_finding():
    """Return the same vulnerability detected by Semgrep."""

    return {
        **sample_ai_finding(),
        "title": "Unsafe Eval",
    }


def sample_bandit_finding():
    """Return a separate security issue detected by Bandit."""

    return {
        "title": "B602: subprocess call with shell=True",
        "category": "security",
        "severity": "high",
        "line_number": 4,
        "explanation": (
            "subprocess call with shell=True identified."
        ),
        "why_it_matters": (
            "Bandit identified a potential Python security issue."
        ),
        "suggested_fix": (
            "Avoid passing untrusted input to shell commands."
        ),
    }


def test_manual_review_combines_ai_and_semgrep():
    """Matching findings should save combined confidence evidence."""

    app, engine, session_factory, project_id = create_test_app()

    try:
        with (
            patch(
                "app.routes.code_reviews.review_code",
                return_value=[sample_ai_finding()],
            ),
            patch(
                "app.routes.code_reviews.collect_security_findings",
                return_value={
                    "semgrep": [sample_semgrep_finding()],
                    "semgrep_status": "completed",
                    "bandit": [],
                    "bandit_status": "completed",
                },
            ) as mock_security,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/code-reviews/",
                    json={
                        "project_id": project_id,
                        "submitted_code": "result = eval(input())",
                        "programming_language": "python",
                    },
                )

                assert response.status_code == 200
                assert response.json()["review_status"] == "completed"

                mock_security.assert_called_once_with(
                    "result = eval(input())",
                    "python",
                )

                reviews = client.get("/code-reviews/")
                assert reviews.status_code == 200

                issues = reviews.json()[0]["issues"]

                assert len(issues) == 1
                assert issues[0]["confidence_score"] == 50
                assert issues[0]["confidence_level"] == "medium"
                assert issues[0]["confidence_evidence"] == {
                    "ai": True,
                    "semgrep": True,
                }

        with session_factory() as db:
            saved_issue = db.query(ReviewIssue).one()

            assert saved_issue.confidence_score == 50
            assert saved_issue.confidence_evidence == {
                "ai": True,
                "semgrep": True,
            }

    finally:
        engine.dispose()


def test_manual_review_survives_semgrep_failure():
    """Semgrep failure should not prevent a Claude review."""

    app, engine, session_factory, project_id = create_test_app()

    try:
        with (
            patch(
                "app.routes.code_reviews.review_code",
                return_value=[sample_ai_finding()],
            ),
            patch(
                "app.routes.code_reviews.collect_security_findings",
                return_value={
                    "semgrep": [],
                    "semgrep_status": "failed",
                    "bandit": [],
                    "bandit_status": "completed",
                },
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/code-reviews/",
                    json={
                        "project_id": project_id,
                        "submitted_code": "result = eval(input())",
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
                assert issues[0]["confidence_evidence"] == {
                    "ai": True,
                }

        with session_factory() as db:
            saved_issue = db.query(ReviewIssue).one()

            assert saved_issue.confidence_score == 20
            assert saved_issue.confidence_evidence == {
                "ai": True,
            }

    finally:
        engine.dispose()


def test_manual_review_saves_bandit_findings():
    """Bandit findings should be saved with Bandit confidence evidence."""

    app, engine, session_factory, project_id = create_test_app()

    try:
        with (
            patch(
                "app.routes.code_reviews.review_code",
                return_value=[],
            ),
            patch(
                "app.routes.code_reviews.collect_security_findings",
                return_value={
                    "semgrep": [],
                    "semgrep_status": "completed",
                    "bandit": [sample_bandit_finding()],
                    "bandit_status": "completed",
                },
            ) as mock_security,
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/code-reviews/",
                    json={
                        "project_id": project_id,
                        "submitted_code": (
                            "import subprocess\n"
                            "subprocess.run('echo test', shell=True)"
                        ),
                        "programming_language": "python",
                    },
                )

                assert response.status_code == 200
                assert response.json()["review_status"] == "completed"

                mock_security.assert_called_once()

                reviews = client.get("/code-reviews/")
                assert reviews.status_code == 200

                issues = reviews.json()[0]["issues"]

                assert len(issues) == 1
                assert issues[0]["title"].startswith("B602:")
                assert issues[0]["category"] == "security"
                assert issues[0]["severity"] == "high"
                assert issues[0]["confidence_evidence"] == {
                    "bandit": True,
                }

        with session_factory() as db:
            saved_issue = db.query(ReviewIssue).one()

            assert saved_issue.title.startswith("B602:")
            assert saved_issue.confidence_evidence == {
                "bandit": True,
            }

    finally:
        engine.dispose()
