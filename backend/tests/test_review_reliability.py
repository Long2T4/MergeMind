"""Stage 10 reliability regressions: bad input, malformed AI output, and
failures after the AI call must never leave a review stuck in "pending".

Uses in-memory SQLite (with foreign keys enforced, like PostgreSQL) and a
mocked Anthropic client. No real database or AI is used.
"""
import json
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import maintenance
from app.database.database import Base, get_db
from auth_helpers import act_as
from app.models.models import CodeReview, Project, ReviewIssue, User
from app.routes import code_reviews, projects, users


def ai_reply(payload, stop_reason="end_turn"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        user = User(name="Reliability Student", email="reliability@example.com")
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, name="Reliability project")
        owner_id = user.id
        db.add(project)
        db.commit()
        project_id = project.id

    app = FastAPI()
    for module in (code_reviews, users, projects):
        app.include_router(module.router)

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    act_as(app, owner_id)
    provider = MagicMock()
    with patch("app.services.ai_review_service.Anthropic", return_value=provider) as client_class:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield SimpleNamespace(
                client=client, factory=factory, provider=provider,
                client_class=client_class, project_id=project_id,
            )
    engine.dispose()


def submit(api, project_id=None):
    return api.client.post("/code-reviews/", json={
        "project_id": api.project_id if project_id is None else project_id,
        "submitted_code": "def add(a, b):\n    return a + b\n",
        "programming_language": "python",
    })


def statuses(api):
    with api.factory() as db:
        return [review.review_status for review in db.query(CodeReview).order_by(CodeReview.id)]


def saved_issues(api):
    with api.factory() as db:
        return db.query(ReviewIssue).order_by(ReviewIssue.id).all()


def test_missing_project_returns_404_without_saving_or_calling_ai(api):
    response = submit(api, project_id=999)

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
    assert statuses(api) == []
    api.provider.messages.create.assert_not_called()


@pytest.mark.parametrize("bad_issue", [
    {"title": "Null explanation", "category": "logic", "severity": "low", "explanation": None},
    {"title": ["not", "a", "string"], "category": "logic", "severity": "low", "explanation": "e"},
    {"title": "Numbers", "category": 7, "severity": None, "explanation": 42, "line_reference": True},
], ids=["null-explanation", "list-title", "wrong-types"])
def test_wrong_field_types_complete_instead_of_crashing(api, bad_issue):
    api.provider.messages.create.return_value = ai_reply({"issues": [bad_issue]})

    response = submit(api)

    assert response.status_code == 200
    assert response.json()["review_status"] == "completed"
    assert statuses(api) == ["completed"]
    issue = saved_issues(api)[0]
    assert isinstance(issue.explanation, str)
    assert issue.title is None or isinstance(issue.title, str)
    assert issue.category in {"logic", "code_quality"}
    assert issue.severity == "low"
    assert issue.line_number is None


def test_malformed_items_are_skipped_and_valid_ones_kept(api):
    api.provider.messages.create.return_value = ai_reply({"issues": [
        "not-an-object",
        {"title": "Real finding", "category": "security", "severity": "high", "explanation": "e"},
    ]})

    response = submit(api)

    assert response.json()["review_status"] == "completed"
    assert [issue.title for issue in saved_issues(api)] == ["Real finding"]


@pytest.mark.parametrize("reply", [
    ai_reply({"issues": ["only", "junk"]}),
    ai_reply('{"issues": [{"title": "cut off'),
    ai_reply({"issues": []}, stop_reason="max_tokens"),
    SimpleNamespace(content=[], stop_reason="end_turn"),
], ids=["all-items-malformed", "truncated-json", "hit-token-limit", "no-text-block"])
def test_unusable_ai_responses_mark_the_review_failed(api, reply):
    api.provider.messages.create.return_value = reply

    response = submit(api)

    assert response.status_code == 200
    assert response.json()["review_status"] == "failed"
    assert statuses(api) == ["failed"]
    assert saved_issues(api) == []


def test_a_failure_while_saving_findings_marks_the_review_failed(api):
    api.provider.messages.create.return_value = ai_reply({"issues": [
        {"title": "t", "category": "logic", "severity": "low", "explanation": "e"},
    ]})

    with patch("app.routes.code_reviews.calculate_risk", side_effect=RuntimeError("scoring broke")):
        response = submit(api)

    assert response.status_code == 200
    assert response.json()["review_status"] == "failed"
    assert statuses(api) == ["failed"]
    # The partial findings were rolled back with the failed save.
    assert saved_issues(api) == []


def test_fields_are_normalized_to_fit_the_schema(api):
    api.provider.messages.create.return_value = ai_reply({"issues": [
        {"title": "x" * 400, "category": " Input Validation ", "severity": "HIGH",
         "explanation": "  padded  ", "line_reference": "see line 12"},
        {"title": "Negative line", "category": "logic", "severity": "low",
         "explanation": "e", "line_reference": -3},
        {"title": "Huge line", "category": "logic", "severity": "low",
         "explanation": "e", "line_reference": 10 ** 12},
    ]})

    response = submit(api)

    assert response.json()["review_status"] == "completed"
    first, negative, huge = saved_issues(api)
    assert len(first.title) <= 255
    assert first.category == "input_validation"
    assert first.severity == "high"
    assert first.explanation == "padded"
    assert first.line_number == 12
    assert negative.line_number is None
    assert huge.line_number is None


def test_provider_is_called_with_a_timeout_and_larger_output_limit(api):
    api.provider.messages.create.return_value = ai_reply({"issues": []})

    submit(api)

    assert api.client_class.call_args.kwargs["timeout"] > 0
    assert api.provider.messages.create.call_args.kwargs["max_tokens"] >= 4096


def test_duplicate_user_email_returns_409(api):
    body = {"name": "Second", "email": "reliability@example.com"}

    response = api.client.post("/users/", json=body)

    assert response.status_code == 409


def test_project_for_missing_user_returns_404(api):
    response = api.client.post("/projects/", json={"user_id": 999, "name": "Orphan"})

    assert response.status_code == 404
    with api.factory() as db:
        assert db.query(Project).count() == 1


def test_stale_pending_cleanup_is_dry_run_by_default(api):
    now = datetime.utcnow()
    with api.factory() as db:
        for status, age in [("pending", 120), ("pending", 5), ("completed", 120)]:
            db.add(CodeReview(
                project_id=api.project_id, submitted_code="x = 1", programming_language="python",
                review_status=status, created_at=now - timedelta(minutes=age),
            ))
        db.commit()

    with api.factory() as db:
        found = maintenance.fail_stale_pending_reviews(db, older_than_minutes=30)
    assert len(found) == 1
    assert statuses(api) == ["pending", "pending", "completed"]

    with api.factory() as db:
        changed = maintenance.fail_stale_pending_reviews(db, older_than_minutes=30, apply=True)
    assert changed == found
    assert statuses(api) == ["failed", "pending", "completed"]
