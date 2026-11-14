"""Stage 12: route-level authorization with the real middleware and routers.

Two signed-in users, A and B. Token verification is stubbed (token "A" or
"B"); real signed tokens are tested separately. GitHub is the Stage 11 fake
and Anthropic is mocked, so nothing leaves the machine.
"""
import json
import os
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite://")

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db, get_session_factory
from app.models.models import CodeReview, Project, PullRequest, PullRequestFile, ReviewIssue, User
from app.routes import code_reviews, health, projects, pull_request_reviews, review_history
from app.services import pr_review_service
from app.services.github_service import GitHubClient, get_github_client_factory
from app.stage12 import middleware
from app.stage12.bootstrap import install_stage12
from test_pull_request_reviews import AI_FINDINGS, FakeGitHub, ai_reply

PR_URL = "https://github.com/octo-org/sample-repo/pull/7"
SUBJECTS = {"A": str(uuid.uuid4()), "B": str(uuid.uuid4())}
A = {"Authorization": "Bearer A"}
B = {"Authorization": "Bearer B"}


POSTGRES_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")


@pytest.fixture(params=["sqlite", "postgresql"])
def env(request, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(middleware, "verify_token", lambda token: {
        "sub": SUBJECTS[token], "email": f"{token.lower()}@example.com", "role": "authenticated"})
    if request.param == "sqlite":
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    else:
        # Same rule as test_migrations.py: a disposable local database only.
        if not POSTGRES_URL:
            pytest.skip("Set MIGRATION_TEST_DATABASE_URL to a disposable local PostgreSQL database")
        host = POSTGRES_URL.rsplit("@", 1)[-1].lower()
        if not host.startswith(("localhost", "127.0.0.1")) or "supabase" in POSTGRES_URL.lower():
            pytest.fail("Refusing to use MIGRATION_TEST_DATABASE_URL: it is not a local database")
        engine = create_engine(POSTGRES_URL)
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    ids = {}
    with factory() as db:
        for name in ("A", "B"):
            user = User(name=name, email=f"{name.lower()}@example.com", auth_user_id=SUBJECTS[name])
            db.add(user)
            db.flush()
            project = Project(user_id=user.id, name=f"{name} project")
            db.add(project)
            db.flush()
            review = CodeReview(project_id=project.id, submitted_code=f"secret_of_{name} = 1",
                                programming_language="python", review_status="completed")
            db.add(review)
            db.flush()
            issue = ReviewIssue(review_id=review.id, category="logic", severity="high",
                                explanation=f"{name}'s finding")
            db.add(issue)
            db.flush()
            ids[name] = SimpleNamespace(user=user.id, project=project.id, review=review.id, issue=issue.id)
        db.commit()

    github = FakeGitHub()
    app = FastAPI()
    install_stage12(app)
    for module in (health, projects, code_reviews, pull_request_reviews, review_history):
        app.include_router(module.router)

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_github_client_factory] = lambda: (
        lambda: GitHubClient("ghp_test_not_real", transport=httpx.MockTransport(github.handler)))
    provider = MagicMock()
    provider.messages.create.side_effect = lambda **kwargs: ai_reply(
        AI_FINDINGS.get(json.loads(kwargs["messages"][0]["content"])["file_path"], []))
    with patch("app.services.ai_review_service.Anthropic", return_value=provider):
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, factory=factory, ids=ids, github=github, provider=provider)
    if request.param == "postgresql":
        Base.metadata.drop_all(engine)
    engine.dispose()


PROTECTED = [
    ("get", "/projects/"), ("post", "/projects/"), ("get", "/code-reviews/"), ("post", "/code-reviews/"),
    ("post", "/pull-request-reviews/"), ("get", "/review-history/"), ("get", "/review-history/stats"),
    ("get", "/review-history/1"), ("get", "/account/me"), ("get", "/account/projects"),
    ("get", "/account/learning"), ("patch", "/account/findings/1"),
]


@pytest.mark.parametrize("method, path", PROTECTED)
def test_anonymous_requests_are_rejected(env, method, path):
    response = getattr(env.client, method)(path, **({"json": {}} if method in ("post", "patch") else {}))
    assert response.status_code == 401


def test_health_stays_public(env):
    assert env.client.get("/health").status_code == 200


# --- Reading another user's data ---------------------------------------------

def test_history_list_and_stats_only_show_your_reviews(env):
    ids = env.ids
    items = env.client.get("/review-history/", headers=A).json()["items"]
    assert [item["id"] for item in items] == [ids["A"].review]
    stats = env.client.get("/review-history/stats", headers=A).json()
    assert (stats["total_reviews"], stats["total_issues"]) == (1, 1)


def test_another_users_review_is_not_found(env):
    assert env.client.get(f"/review-history/{env.ids['B'].review}", headers=A).status_code == 404
    assert env.client.get(f"/review-history/{env.ids['A'].review}", headers=A).status_code == 200


def test_code_reviews_list_works_when_signed_in_and_is_scoped(env):
    response = env.client.get("/code-reviews/", headers=A)
    assert response.status_code == 200
    body = response.json()
    assert [review["id"] for review in body] == [env.ids["A"].review]
    assert [issue["explanation"] for issue in body[0]["issues"]] == ["A's finding"]


def test_projects_only_list_your_own(env):
    assert [p["name"] for p in env.client.get("/projects/", headers=A).json()] == ["A project"]
    assert [p["name"] for p in env.client.get("/account/projects", headers=A).json()] == ["A project"]
    assert env.client.get(f"/account/projects/{env.ids['B'].project}", headers=A).status_code == 404


def test_another_users_findings_are_not_found(env):
    assert env.client.get(f"/account/reviews/{env.ids['B'].review}/findings", headers=A).status_code == 404
    learning = env.client.get("/account/learning", headers=A).json()
    assert (learning["total_reviews"], learning["total_issues"]) == (1, 1)


# --- Changing another user's data ---------------------------------------------

def test_cannot_review_code_in_another_users_project(env):
    response = env.client.post("/code-reviews/", headers=A, json={
        "project_id": env.ids["B"].project, "submitted_code": "x = 1", "programming_language": "python"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
    assert env.provider.messages.create.call_count == 0


def test_cannot_review_a_pull_request_in_another_users_project(env):
    response = env.client.post("/pull-request-reviews/", headers=A, json={
        "project_id": env.ids["B"].project, "pr_url": PR_URL})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
    assert env.github.requests == []


def test_cannot_create_a_project_for_another_user(env):
    response = env.client.post("/projects/", headers=A, json={"user_id": env.ids["B"].user, "name": "x"})
    assert response.status_code == 404
    with env.factory() as db:
        assert db.query(Project).filter(Project.name == "x").count() == 0


def test_cannot_change_another_users_finding_status(env):
    response = env.client.patch(f"/account/findings/{env.ids['B'].issue}", headers=A, json={"status": "fixed"})
    assert response.status_code == 404
    with env.factory() as db:
        assert db.get(ReviewIssue, env.ids["B"].issue).status == "open"


# --- Stage 11 pull request reviews while signed in -----------------------------

def test_a_signed_in_pull_request_review_completes_and_is_visible_to_its_owner(env):
    started = env.client.post("/pull-request-reviews/", headers=A, json={
        "project_id": env.ids["A"].project, "pr_url": PR_URL})
    assert started.status_code == 202
    review_id = started.json()["id"]

    detail = env.client.get(f"/review-history/{review_id}", headers=A).json()
    assert detail["review_status"] == "completed"
    assert detail["pull_request"]["number"] == 7
    assert {f["path"] for f in detail["pull_request"]["files"]} >= {"src/app.py", "src/util.py"}
    assert {issue["file_name"] for issue in detail["issues"]} == {"src/app.py", "src/util.py"}
    assert env.provider.messages.create.call_count == 2

    row = next(item for item in env.client.get("/review-history/", headers=A).json()["items"]
               if item["id"] == review_id)
    assert (row["pr_repo"], row["pr_number"]) == ("octo-org/sample-repo", 7)

    # User B can't see it anywhere.
    assert env.client.get(f"/review-history/{review_id}", headers=B).status_code == 404
    assert review_id not in [item["id"] for item in env.client.get("/review-history/", headers=B).json()["items"]]
    assert review_id not in [review["id"] for review in env.client.get("/code-reviews/", headers=B).json()]


def test_background_review_needs_no_request_context(env):
    with env.factory() as db:
        pr = PullRequest(owner="octo-org", repo="sample-repo", number=7, title="t", author="a",
                         html_url=PR_URL, base_sha="b" * 40, head_sha="a" * 40, source_root="",
                         changed_files_count=1, additions=2, deletions=0)
        pr.files = [PullRequestFile(path="src/util.py", status="added", additions=2, deletions=0,
                                    patch="@@ -0,0 +1,2 @@\n+def add(a, b):\n+    return a - b",
                                    language="python", review_state="pending")]
        review = CodeReview(project_id=env.ids["A"].project, submitted_code="diff", programming_language="python",
                            review_status="pending", pull_request=pr)
        db.add(review)
        db.commit()
        review_id = review.id

    pr_review_service.run_pull_request_review(
        review_id, env.factory,
        lambda: GitHubClient("ghp_test_not_real", transport=httpx.MockTransport(env.github.handler)))

    with env.factory() as db:
        assert db.get(CodeReview, review_id).review_status == "completed"
