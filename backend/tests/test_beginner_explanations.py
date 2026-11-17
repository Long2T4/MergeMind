"""Exercise the authenticated explanation endpoint with SQLite and a fake Claude."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest

from app.models.models import ReviewIssue
from app.routes import finding_explanations as explanations
from test_pull_request_reviews import ai_reply, finding
from test_stage12_authorization import A, B, PR_URL, env  # noqa: F401 (pytest fixture)

EXPLANATION = {
    "what_is_wrong": "The function subtracts when you asked it to add.",
    "why_it_matters": "You get the wrong total.",
    "before": "return a - b",
    "after": "return a + b",
}


def reply(value=EXPLANATION):
    return SimpleNamespace(
        content=[SimpleNamespace(text=json.dumps(value))], stop_reason="end_turn",
    )


def path(issue_id):
    return f"/account/findings/{issue_id}/beginner-explanation"


@pytest.fixture(autouse=True)
def reset_limit(monkeypatch):
    monkeypatch.setattr(explanations, "_attempts", explanations.deque())


@pytest.mark.parametrize("kind", ["manual", "pull_request"])
def test_generates_for_both_review_types_and_saves_for_reopening(env, kind):
    if kind == "manual":
        env.provider.messages.create.side_effect = None
        env.provider.messages.create.return_value = ai_reply([finding("Wrong operation", 2)])
        started = env.client.post("/code-reviews/", headers=A, json={
            "project_id": env.ids["A"].project,
            "submitted_code": "def add(a, b):\n    return a - b",
            "programming_language": "python",
        })
        assert started.status_code == 200
    else:
        started = env.client.post("/pull-request-reviews/", headers=A, json={
            "project_id": env.ids["A"].project, "pr_url": PR_URL,
        })
        assert started.status_code == 202

    detail_path = f"/review-history/{started.json()['id']}"
    issue = env.client.get(detail_path, headers=A).json()["issues"][0]
    assert issue["beginner_explanation"] is None
    url = path(issue["id"])
    env.provider.messages.create.reset_mock(side_effect=True)
    env.provider.messages.create.return_value = reply()
    assert env.client.post(url, headers=A).json() == EXPLANATION
    with env.factory() as db:
        assert db.get(ReviewIssue, issue["id"]).beginner_explanation == EXPLANATION
    detail = env.client.get(detail_path, headers=A).json()
    assert detail["issues"][0]["beginner_explanation"] == EXPLANATION
    assert env.client.post(url, headers=A).json() == EXPLANATION
    env.provider.messages.create.assert_called_once()
    args = env.provider.messages.create.call_args.kwargs
    payload = json.loads(args["messages"][0]["content"])
    assert payload["language"] == "python"
    assert payload["explanation"] == issue["explanation"]
    assert "submitted_code" not in payload


def test_only_the_owner_can_generate_or_read_an_explanation(env):
    url = path(env.ids["A"].issue)
    assert env.client.post(url).status_code == 401
    assert env.client.post(url, headers=B).status_code == 404
    assert env.client.post(path(9999), headers=A).status_code == 404
    env.provider.messages.create.assert_not_called()

    env.provider.messages.create.side_effect = None
    env.provider.messages.create.return_value = reply()
    assert env.client.post(url, headers=A).status_code == 200
    assert env.client.post(url, headers=B).status_code == 404
    env.provider.messages.create.assert_called_once()


def test_invalid_output_is_not_saved_and_retry_can_succeed(env):
    issue_id = env.ids["A"].issue
    env.provider.messages.create.side_effect = [reply({**EXPLANATION, "before": " "}), reply()]
    assert env.client.post(path(issue_id), headers=A).status_code == 502
    with env.factory() as db:
        assert db.get(ReviewIssue, issue_id).beginner_explanation is None
    assert env.client.post(path(issue_id), headers=A).json() == EXPLANATION
    assert env.provider.messages.create.call_count == 2


def test_limit_counts_failures_and_allows_cached_results_and_later_attempts(env, monkeypatch):
    first = path(env.ids["A"].issue)
    second = path(env.ids["B"].issue)
    now = 1000
    monkeypatch.setattr(explanations, "monotonic", lambda: now)
    monkeypatch.setattr(explanations, "MAX_ATTEMPTS_PER_HOUR", 2)
    env.provider.messages.create.side_effect = [reply(), reply({}), reply()]
    assert env.client.post(first, headers=A).json() == EXPLANATION
    assert env.client.post(second, headers=B).status_code == 502
    assert env.client.post(second, headers=B).status_code == 429
    assert env.client.post(first, headers=A).json() == EXPLANATION
    assert env.provider.messages.create.call_count == 2

    now += 3600
    assert env.client.post(second, headers=B).json() == EXPLANATION
    assert env.provider.messages.create.call_count == 3


def test_overlapping_requests_only_generate_once(env):
    generating = Event()
    finish = Event()
    url = path(env.ids["A"].issue)

    def slow_reply(**kwargs):
        generating.set()
        assert finish.wait(5)
        return reply()

    env.provider.messages.create.side_effect = slow_reply
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(env.client.post, url, headers=A)
        try:
            assert generating.wait(5)
            assert env.client.post(url, headers=A).status_code == 409
        finally:
            finish.set()
        assert first.result(timeout=5).json() == EXPLANATION

    assert env.client.post(url, headers=A).json() == EXPLANATION
    env.provider.messages.create.assert_called_once()
