"""Stage 12: the Stage 11 AI usage limits stay server-wide with two signed-in users.

Drives the real API (middleware, routers, background task) as users A and B.
GitHub is the in-memory fake and Anthropic is mocked; nothing leaves the machine.
"""
import re

import httpx
import pytest

from app.routes import pull_request_reviews as pr_route
from app.services.pr_review_service import MAX_ACTIVE_REVIEWS, MAX_REVIEWS_PER_HOUR
from test_stage12_authorization import A, B, env  # noqa: F401 (pytest fixture)

API = "/repos/octo-org/sample-repo"
PULL_NUMBER = re.compile(rf"^{API}/pulls/(\d+)")


def pr_url(number):
    return f"https://github.com/octo-org/sample-repo/pull/{number}"


@pytest.fixture
def github(env):
    """Let the fake GitHub answer for any PR number (as #7), recording which were asked for."""
    asked = []
    serve = env.github.handler

    def handler(request):
        match = PULL_NUMBER.match(request.url.path)
        if match:
            asked.append(int(match.group(1)))
            path = request.url.path.replace(f"/pulls/{match.group(1)}", "/pulls/7", 1)
            request = httpx.Request(request.method, request.url.copy_with(path=path), headers=request.headers)
        return serve(request)

    env.github.handler = handler
    return asked


@pytest.fixture
def hold_reviews_pending(monkeypatch):
    """Keep started reviews 'pending', like reviews still running in the background."""
    monkeypatch.setattr(pr_route, "run_pull_request_review", lambda *args, **kwargs: None)


def start(env, user, number, owner="A"):
    return env.client.post("/pull-request-reviews/", headers=user, json={
        "project_id": env.ids[owner].project, "pr_url": pr_url(number)})


def ai_calls(env):
    return env.provider.messages.create.call_count


# --- 1. At most 3 pull request reviews run at once, across all users ------------

def test_concurrent_limit_counts_every_users_reviews(env, github, hold_reviews_pending):
    assert MAX_ACTIVE_REVIEWS == 3
    assert start(env, A, 101).status_code == 202
    assert start(env, B, 102, owner="B").status_code == 202
    assert start(env, A, 103).status_code == 202
    asked_before = list(github)

    blocked = start(env, B, 104, owner="B")
    assert blocked.status_code == 429
    assert "at most 3" in blocked.json()["detail"]
    # Refused before any GitHub request or AI call.
    assert github == asked_before
    assert ai_calls(env) == 0


# --- 2. At most 20 pull request reviews start per hour, across all users ----------

def test_hourly_limit_counts_every_users_reviews(env, github):
    assert MAX_REVIEWS_PER_HOUR == 20
    for number in range(200, 200 + MAX_REVIEWS_PER_HOUR):
        user, owner = (A, "A") if number % 2 else (B, "B")
        response = start(env, user, number, owner=owner)
        assert response.status_code == 202, response.json()
        # Each review finishes in the background, so only the hourly limit applies.
        detail = env.client.get(f"/review-history/{response.json()['id']}", headers=user).json()
        assert detail["review_status"] == "completed"
    calls_before = ai_calls(env)

    blocked = start(env, A, 299)
    assert blocked.status_code == 429
    assert "per hour" in blocked.json()["detail"]
    assert 299 not in github
    assert ai_calls(env) == calls_before


# --- 3. The same pull request can't be reviewed twice at once, by anyone ----------

def test_duplicate_pull_request_is_refused_for_every_user(env, github, hold_reviews_pending):
    assert start(env, A, 7).status_code == 202
    asked_before = list(github)
    for user, owner in ((A, "A"), (B, "B")):
        duplicate = start(env, user, 7, owner=owner)
        assert duplicate.status_code == 409
        assert "already being reviewed" in duplicate.json()["detail"]
    assert github == asked_before  # refused before reading GitHub again
    assert ai_calls(env) == 0


def test_a_finished_pull_request_can_be_reviewed_again_by_another_user(env, github):
    first = start(env, A, 7)
    assert env.client.get(f"/review-history/{first.json()['id']}", headers=A).json()["review_status"] == "completed"
    again = start(env, B, 7, owner="B")
    assert again.status_code == 202
    assert env.client.get(f"/review-history/{again.json()['id']}", headers=B).json()["review_status"] == "completed"


# --- 4. Ownership is checked before GitHub or Anthropic, even at the limit -------

def test_another_users_project_is_refused_before_any_request(env, github):
    response = start(env, A, 7, owner="B")
    assert response.status_code == 404
    assert github == [] and ai_calls(env) == 0

    manual = env.client.post("/code-reviews/", headers=A, json={
        "project_id": env.ids["B"].project, "submitted_code": "x = 1", "programming_language": "python"})
    assert manual.status_code == 404
    assert ai_calls(env) == 0


def test_ownership_is_checked_before_the_limits(env, github, hold_reviews_pending):
    for number in (101, 102, 103):
        assert start(env, A, number).status_code == 202
    # At the concurrent limit, a request for someone else's project still gets 404, not 429.
    assert start(env, A, 104, owner="B").status_code == 404
    assert 104 not in github


# --- 5. Background reviews still complete --------------------------------------

def test_background_reviews_complete_for_each_user(env, github):
    for user, owner, number in ((A, "A", 301), (B, "B", 302)):
        started = start(env, user, number, owner=owner)
        assert started.status_code == 202
        detail = env.client.get(f"/review-history/{started.json()['id']}", headers=user).json()
        assert detail["review_status"] == "completed"
        assert detail["pull_request"]["number"] == number
        assert {issue["file_name"] for issue in detail["issues"]} == {"src/app.py", "src/util.py"}
    assert ai_calls(env) == 4  # two reviewable files per PR
