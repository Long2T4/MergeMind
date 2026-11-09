"""Stage 11: pull request reviews from the API through the background task.

GitHub is an in-memory fake behind httpx.MockTransport and Anthropic is a
mock, so no network, real database or AI is used.
"""
import json
import logging
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import unquote

os.environ.setdefault("DATABASE_URL", "sqlite://")

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db, get_session_factory
from app.models.models import CodeReview, Project, PullRequest, PullRequestFile, ReviewIssue, User
from app.routes import code_reviews, pull_request_reviews, review_history
from app.services import pr_review_service
from app.services.github_service import GitHubClient, get_github_client_factory

TOKEN = "ghp_test_token_not_a_real_secret"
HEAD = "a" * 40
URL = "https://github.com/octo-org/sample-repo/pull/7"
API = "/repos/octo-org/sample-repo"

APP_PY = (
    "from src.models import User\n"   # 1
    "\n"                              # 2
    "\n"                              # 3
    "def create(name):\n"             # 4  changed
    "    return User(name)\n"         # 5  changed
    "\n"                              # 6
    "\n"                              # 7
    "def legacy():\n"                 # 8
    "    return eval('1')\n"          # 9
)
UTIL_PY = "def add(a, b):\n    return a - b\n"


def changed(path, patch, status="modified", additions=2, deletions=0):
    return {"filename": path, "status": status, "additions": additions, "deletions": deletions, "patch": patch}


class FakeGitHub:
    def __init__(self):
        self.pr = {
            "number": 7, "title": "Add user creation", "html_url": URL, "user": {"login": "octo-student"},
            "base": {"sha": "b" * 40, "repo": {"private": False}}, "head": {"sha": HEAD},
            "changed_files": 6, "additions": 6, "deletions": 1,
        }
        self.files = [
            changed("src/app.py", "@@ -3,0 +4,2 @@\n+def create(name):\n+    return User(name)"),
            changed("src/util.py", "@@ -0,0 +1,2 @@\n+def add(a, b):\n+    return a - b", status="added"),
            changed("README.md", "@@ -1 +1 @@\n-old\n+new"),
            changed("package-lock.json", "@@ -1 +1 @@\n-1\n+2"),
            changed("logo.png", None, additions=0),
            changed("old.py", "@@ -1 +0,0 @@\n-x = 1", status="removed", additions=0, deletions=1),
        ]
        self.contents = {
            "src/app.py": APP_PY,
            "src/util.py": UTIL_PY,
            "src/models.py": "class User:\n    def __init__(self, name):\n        assert name\n",
            "src/unrelated.py": "unrelated-secret-marker",
            "README.md": "new", "package-lock.json": "2",
        }
        self.overrides = {}
        self.hidden_from_tree = set()
        self.requests = []

    def handler(self, request):
        self.requests.append(request)
        path = request.url.path
        for prefix, response in self.overrides.items():
            if path.startswith(prefix):
                return response
        if path == f"{API}/pulls/7":
            return httpx.Response(200, json=self.pr)
        if path == f"{API}/pulls/7/files":
            page = int(request.url.params["page"])
            return httpx.Response(200, json=self.files[(page - 1) * 100: page * 100])
        if path == f"{API}/git/trees/{HEAD}":
            return httpx.Response(200, json={"tree": [
                {"path": name, "type": "blob", "size": len(text)} for name, text in self.contents.items()
                if name not in self.hidden_from_tree]})
        if path.startswith(f"{API}/contents/"):
            assert request.url.params["ref"] == HEAD
            name = unquote(path.split("/contents/", 1)[1])
            if name in self.contents:
                return httpx.Response(200, content=self.contents[name].encode())
        return httpx.Response(404, json={"message": "Not Found"})

    def fetched(self, name):
        return any(request.url.path == f"{API}/contents/{name}" for request in self.requests)


def ai_reply(issues):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"issues": issues}))],
                           stop_reason="end_turn")


def finding(title, line, severity="high", category="logic"):
    return {"title": title, "category": category, "severity": severity, "explanation": f"{title} explained",
            "why_it_matters": "It matters", "suggested_fix": "Fix it", "line_reference": f"line {line}"}


AI_FINDINGS = {
    "src/app.py": [
        finding("Empty names reach User", 5),                          # changed line
        finding("eval is dangerous", 9, category="security"),          # outside, high: kept and labeled
        finding("Unused blank lines", 2, severity="low"),              # outside, low: dropped
    ],
    "src/util.py": [finding("add subtracts", 2, severity="medium")],
}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        user = User(name="PR Student", email="pr@example.com")
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, name="PR project")
        db.add(project)
        db.commit()
        project_id = project.id

    github = FakeGitHub()
    app = FastAPI()
    for module in (code_reviews, pull_request_reviews, review_history):
        app.include_router(module.router)

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_github_client_factory] = lambda: (
        lambda: GitHubClient(TOKEN, transport=httpx.MockTransport(github.handler)))

    provider = MagicMock()
    calls = []

    def create(**kwargs):
        payload = json.loads(kwargs["messages"][0]["content"])
        calls.append({"system": kwargs["system"], "payload": payload})
        return ai_reply(AI_FINDINGS.get(payload["file_path"], []))

    provider.messages.create.side_effect = create
    with patch("app.services.ai_review_service.Anthropic", return_value=provider):
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, factory=factory, github=github, ai=calls,
                                  provider=provider, project_id=project_id, app=app)
    engine.dispose()


def submit(env, url=URL, **extra):
    return env.client.post("/pull-request-reviews/", json={"project_id": env.project_id, "pr_url": url, **extra})


def detail(env, review_id):
    return env.client.get(f"/review-history/{review_id}").json()


def counts(env):
    with env.factory() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (CodeReview, PullRequest, PullRequestFile, ReviewIssue))


def file_states(review):
    return {file["path"]: (file["review_state"], file["skip_reason"]) for file in review["pull_request"]["files"]}


# --- Request validation: nothing is saved and GitHub/AI aren't called -------

@pytest.mark.parametrize("url", [
    "https://gitlab.com/octo-org/sample-repo/pull/7",
    "https://github.com/octo-org/sample-repo/issues/7",
    "http://github.com/octo-org/sample-repo/pull/7",
    "https://github.com/octo-org/sample-repo/pull/7?redirect=http://evil.example",
    "javascript:alert(1)",
])
def test_invalid_urls_are_rejected_before_any_request(env, url):
    response = submit(env, url)
    assert response.status_code == 422
    assert "pull request URL" in response.json()["detail"]
    assert env.github.requests == [] and env.ai == [] and counts(env) == (0, 0, 0, 0)


def test_source_root_must_be_a_relative_repository_path(env):
    response = submit(env, source_root="../etc")
    assert response.status_code == 422
    assert env.github.requests == []


def test_missing_project_is_404_before_calling_github(env):
    response = env.client.post("/pull-request-reviews/", json={"project_id": 999, "pr_url": URL})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
    assert env.github.requests == []


def test_missing_github_token_is_a_clear_503(env, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    del env.app.dependency_overrides[get_github_client_factory]
    response = submit(env)
    assert response.status_code == 503
    assert "GITHUB_TOKEN" in response.json()["detail"]
    assert counts(env) == (0, 0, 0, 0)


def test_private_pull_requests_are_rejected(env):
    env.github.pr["base"] = {"sha": "b" * 40, "repo": {"private": True}}
    response = submit(env)
    assert response.status_code == 404
    assert "not found or not public" in response.json()["detail"]
    assert counts(env) == (0, 0, 0, 0)


def test_missing_pull_requests_are_404(env):
    env.github.overrides[f"{API}/pulls/7"] = httpx.Response(404, json={"message": "Not Found"})
    response = submit(env)
    assert response.status_code == 404
    assert "not found or not public" in response.json()["detail"]
    assert counts(env) == (0, 0, 0, 0) and env.ai == []


def test_rate_limits_are_a_clear_503_and_nothing_is_saved(env):
    env.github.overrides[f"{API}/pulls/7"] = httpx.Response(
        403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"},
        json={"message": "API rate limit exceeded"})
    response = submit(env)
    assert response.status_code == 503
    assert "rate limit" in response.json()["detail"]
    assert "2030" in response.json()["detail"]
    assert counts(env) == (0, 0, 0, 0) and env.ai == []


@pytest.mark.parametrize("pr_change, message", [
    ({"changed_files": pr_review_service.MAX_CHANGED_FILES + 1}, "changed files"),
    ({"additions": pr_review_service.MAX_CHANGED_LINES, "deletions": 1}, "changed lines"),
])
def test_oversized_pull_requests_are_rejected_before_listing_files(env, pr_change, message):
    env.github.pr.update(pr_change)
    response = submit(env)
    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert not any(request.url.path.endswith("/files") for request in env.github.requests)
    assert counts(env) == (0, 0, 0, 0)


def _pending_pr_review(env, number, owner="octo-org"):
    with env.factory() as db:
        pr = PullRequest(owner=owner, repo="sample-repo", number=number, title="t", author="a",
                         html_url=f"https://github.com/{owner}/sample-repo/pull/{number}", base_sha="b" * 40,
                         head_sha=HEAD, source_root="", changed_files_count=1, additions=1, deletions=0)
        db.add(CodeReview(project_id=env.project_id, submitted_code="diff", programming_language="python",
                          review_status="pending", pull_request=pr))
        db.commit()


def test_a_pull_request_already_being_reviewed_is_not_reviewed_twice(env):
    _pending_pr_review(env, 7, owner="Octo-Org")  # GitHub names are case-insensitive
    response = submit(env)
    assert response.status_code == 409
    assert "already being reviewed" in response.json()["detail"]
    assert env.github.requests == [] and env.ai == []


def test_concurrent_pull_request_reviews_are_capped(env):
    for number in range(100, 100 + pr_review_service.MAX_ACTIVE_REVIEWS):
        _pending_pr_review(env, number)
    response = submit(env)
    assert response.status_code == 429
    assert "Too many" in response.json()["detail"]
    assert env.github.requests == []


def test_pull_request_reviews_per_hour_are_capped_to_bound_ai_spending(env):
    # Without accounts (Stage 12), a server-wide hourly cap bounds Anthropic calls
    # to MAX_REVIEWS_PER_HOUR x MAX_REVIEWED_FILES per hour, even if reviews finish.
    for number in range(200, 200 + pr_review_service.MAX_REVIEWS_PER_HOUR):
        _pending_pr_review(env, number)
    with env.factory() as db:
        db.query(CodeReview).update({"review_status": "completed"})
        db.commit()
    response = submit(env)
    assert response.status_code == 429
    assert "per hour" in response.json()["detail"]
    assert env.github.requests == [] and env.ai == []


def test_manual_reviews_do_not_count_toward_the_pull_request_cap(env):
    for _ in range(pr_review_service.MAX_REVIEWS_PER_HOUR):
        env.client.post("/code-reviews/", json={
            "project_id": env.project_id, "submitted_code": "x = 1\n", "programming_language": "python"})
    assert submit(env).status_code == 202


def test_stale_pending_reviews_do_not_block_new_ones(env):
    _pending_pr_review(env, 7)
    with env.factory() as db:
        db.query(CodeReview).update({"created_at": CodeReview.created_at - timedelta(hours=2)})
        db.commit()
    assert submit(env).status_code == 202


def test_large_files_missing_from_a_truncated_tree_are_capped_while_downloading(env):
    env.github.hidden_from_tree.add("src/util.py")
    env.github.contents["src/util.py"] = "x = 1\n" * (pr_review_service.MAX_FILE_CHARS // 6 + 1)
    review = detail(env, submit(env).json()["id"])
    assert file_states(review)["src/util.py"] == ("skipped", "too_large")


def test_a_push_while_the_pull_request_is_read_is_rejected(env):
    # The files must come from the same head commit that will be reviewed.
    reads = []

    def pull_request(request):
        reads.append(request)
        return httpx.Response(200, json={**env.github.pr, "head": {"sha": HEAD if len(reads) == 1 else "c" * 40}})

    env.github.handler = (lambda original: lambda request: (
        pull_request(request) if request.url.path == f"{API}/pulls/7" else original(request)))(env.github.handler)
    response = submit(env)
    assert response.status_code == 409
    assert "changed while" in response.json()["detail"]
    assert counts(env) == (0, 0, 0, 0)


def test_pull_requests_with_nothing_reviewable_are_rejected(env):
    env.github.files = [changed("README.md", "@@ -1 +1 @@\n-a\n+b"), changed("yarn.lock", "@@ -1 +1 @@\n-a\n+b")]
    response = submit(env)
    assert response.status_code == 422
    assert "no files MergeMind can review" in response.json()["detail"]
    assert counts(env) == (0, 0, 0, 0)


# --- Successful review -------------------------------------------------------

def test_reviews_changed_files_and_saves_per_file_findings(env, caplog):
    caplog.set_level(logging.DEBUG)
    response = submit(env)

    assert response.status_code == 202
    created = response.json()
    assert created["review_status"] == "pending"  # the background review runs after the response
    assert created["pull_request"]["head_sha"] == HEAD

    review = detail(env, created["id"])
    assert review["review_status"] == "completed"
    assert review["programming_language"] == "python"
    pr = review["pull_request"]
    assert (pr["owner"], pr["repo"], pr["number"], pr["title"], pr["author"]) == (
        "octo-org", "sample-repo", 7, "Add user creation", "octo-student")
    assert file_states(review) == {
        "src/app.py": ("reviewed", None), "src/util.py": ("reviewed", None),
        "README.md": ("skipped", "unsupported"), "package-lock.json": ("skipped", "generated"),
        "logo.png": ("skipped", "binary"), "old.py": ("skipped", "removed"),
    }

    found = {(issue["file_name"], issue["title"], issue["line_number"], issue["outside_diff"])
             for issue in review["issues"]}
    assert found == {
        ("src/app.py", "Empty names reach User", 5, False),
        ("src/app.py", "eval is dangerous", 9, True),
        ("src/util.py", "add subtracts", 2, False),
    }
    assert all(issue["confidence_score"] == 20 for issue in review["issues"])
    assert review["risk_score"] is not None and review["risk_level"]
    assert "src/app.py" in review["submitted_code"] and "+def create(name):" in review["submitted_code"]

    # The AI saw changed lines and only the directly imported file, read at the head commit.
    by_file = {call["payload"]["file_path"]: call for call in env.ai}
    assert set(by_file) == {"src/app.py", "src/util.py"}
    app_call = by_file["src/app.py"]
    assert app_call["payload"]["changed_lines"] == [4, 5]
    assert [item["path"] for item in app_call["payload"]["related_files"]] == ["src/models.py"]
    assert "changed_lines" in app_call["system"]
    assert env.github.fetched("src/models.py") and not env.github.fetched("src/unrelated.py")

    assert TOKEN not in response.text and TOKEN not in json.dumps(review) and TOKEN not in caplog.text


def test_manual_reviews_still_use_the_original_prompt_and_payload(env):
    response = env.client.post("/code-reviews/", json={
        "project_id": env.project_id, "submitted_code": "print(1)\n", "programming_language": "python"})
    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "completed"
    assert body["pull_request_id"] is None and body["pull_request"] is None
    assert "changed_lines" not in env.ai[0]["payload"]
    assert "changed_lines" not in env.ai[0]["system"]


def test_only_the_first_ten_reviewable_files_are_reviewed(env):
    limit = pr_review_service.MAX_REVIEWED_FILES
    env.github.files = [changed(f"src/m{n}.py", "@@ -0,0 +1 @@\n+x = 1", status="added") for n in range(limit + 2)]
    env.github.contents.update({f"src/m{n}.py": "x = 1\n" for n in range(limit + 2)})
    env.github.pr["changed_files"] = limit + 2

    review = detail(env, submit(env).json()["id"])

    states = [(file["review_state"], file["skip_reason"]) for file in review["pull_request"]["files"]]
    assert states == [("reviewed", None)] * limit + [("skipped", "file_limit")] * 2
    assert len(env.ai) == limit


def test_files_too_large_at_the_head_commit_are_skipped(env):
    env.github.contents["src/util.py"] = "x = 1\n" * (pr_review_service.MAX_FILE_CHARS // 6 + 1)
    review = detail(env, submit(env).json()["id"])
    assert file_states(review)["src/util.py"] == ("skipped", "too_large")
    assert {call["payload"]["file_path"] for call in env.ai} == {"src/app.py"}


def test_history_rows_show_pull_request_details_and_manual_rows_are_unchanged(env):
    env.client.post("/code-reviews/", json={
        "project_id": env.project_id, "submitted_code": "print(1)\n", "programming_language": "python"})
    pr_review_id = submit(env).json()["id"]

    page = env.client.get("/review-history/").json()
    rows = {row["id"]: row for row in page["items"]}
    assert page["total"] == 2
    pr_row = rows[pr_review_id]
    assert (pr_row["pull_request_id"], pr_row["pr_repo"], pr_row["pr_number"], pr_row["pr_title"]) == (
        pr_row["pull_request_id"], "octo-org/sample-repo", 7, "Add user creation")
    assert pr_row["pull_request_id"] is not None and pr_row["issue_count"] == 3
    manual = next(row for row in page["items"] if row["id"] != pr_review_id)
    assert (manual["pull_request_id"], manual["pr_repo"], manual["pr_number"], manual["pr_title"]) == (
        None, None, None, None)
    assert manual["code_preview"] == "print(1)\n"

    stats = env.client.get("/review-history/stats").json()
    assert stats["total_reviews"] == 2 and stats["completed_reviews"] == 2


# --- Background failures never leave a review pending ------------------------

def test_one_failed_file_does_not_fail_the_review(env):
    original = env.provider.messages.create.side_effect

    def create(**kwargs):
        if json.loads(kwargs["messages"][0]["content"])["file_path"] == "src/util.py":
            raise RuntimeError("provider down")
        return original(**kwargs)

    env.provider.messages.create.side_effect = create
    review = detail(env, submit(env).json()["id"])

    assert review["review_status"] == "completed"
    assert file_states(review)["src/app.py"] == ("reviewed", None)
    assert file_states(review)["src/util.py"] == ("failed", None)
    assert {issue["file_name"] for issue in review["issues"]} == {"src/app.py"}


def test_review_fails_when_every_file_fails(env):
    env.provider.messages.create.side_effect = RuntimeError("provider down")
    review = detail(env, submit(env).json()["id"])
    assert review["review_status"] == "failed"
    assert review["risk_score"] is None and review["issues"] == []
    assert {state for state, _ in file_states(review).values()} == {"failed", "skipped"}


def test_rate_limit_during_the_background_review_fails_it_cleanly(env):
    env.github.overrides[f"{API}/git/trees/"] = httpx.Response(
        429, headers={"retry-after": "60"}, json={"message": "slow down"})
    response = submit(env)
    assert response.status_code == 202
    review = detail(env, response.json()["id"])
    assert review["review_status"] == "failed"
    assert "pending" not in {state for state, _ in file_states(review).values()}
    assert env.ai == []


def test_rate_limit_on_one_file_fails_only_that_file(env):
    env.github.overrides[f"{API}/contents/src/util.py"] = httpx.Response(
        403, headers={"x-ratelimit-remaining": "0"}, json={"message": "API rate limit exceeded"})
    review = detail(env, submit(env).json()["id"])
    assert review["review_status"] == "completed"
    assert file_states(review)["src/util.py"] == ("failed", None)
    assert file_states(review)["src/app.py"] == ("reviewed", None)


def test_unexpected_errors_after_reviewing_still_mark_the_review_failed(env):
    with patch.object(pr_review_service, "calculate_risk", side_effect=RuntimeError("boom")):
        review_id = submit(env).json()["id"]
    review = detail(env, review_id)
    assert review["review_status"] == "failed"
    assert "pending" not in {state for state, _ in file_states(review).values()}


def test_a_failing_database_session_in_the_background_is_contained(caplog):
    # Even if recording the failure is impossible, the background task must not raise.
    broken = MagicMock(side_effect=RuntimeError("database unavailable"))
    pr_review_service.run_pull_request_review(1, broken, lambda: None)
    assert "database unavailable" in caplog.text


def test_missing_review_in_the_background_is_ignored(env):
    pr_review_service.run_pull_request_review(
        12345, env.factory, lambda: GitHubClient(TOKEN, transport=httpx.MockTransport(env.github.handler)))
    assert counts(env) == (0, 0, 0, 0)
