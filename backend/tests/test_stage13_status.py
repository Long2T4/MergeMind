"""Stage 13: reviews record whether Semgrep and Bandit ran, end to end.

Manual reviews go through POST /code-reviews/ and pull request reviews through
the Stage 11 background review. The AI and GitHub are faked; scanner results
are the REAL recorded output in tests/fixtures/stage13/.
"""
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.models import CodeReview, ReviewIssue
from app.services import pr_review_service
from app.services.bandit_service import normalize_bandit_finding
from app.services.semgrep_service import normalize_semgrep_finding
from test_pull_request_reviews import env, submit, detail  # noqa: F401 (env is a fixture)
from test_stage13_integration import create_test_app

FIXTURES = Path(__file__).parent / "fixtures" / "stage13"


def recorded(tool, normalize):
    results = json.loads((FIXTURES / f"{tool}_vulnerable.json").read_text())["results"]
    return [finding for result in results if (finding := normalize(result))]


def scanners(semgrep="completed", bandit="completed", with_findings=True):
    return {
        "semgrep": recorded("semgrep", normalize_semgrep_finding) if with_findings and semgrep == "completed" else [],
        "semgrep_status": semgrep,
        "bandit": recorded("bandit", normalize_bandit_finding) if with_findings and bandit == "completed" else [],
        "bandit_status": bandit,
    }


AI = [{"title": title, "category": "security", "severity": "high", "line_number": line,
       "explanation": title, "why_it_matters": "It matters.", "suggested_fix": "Fix it."}
      for line, title in [(6, "Hard-coded database password"), (14, "Code execution via eval()"),
                          (18, "Command injection via shell=True")]]


def run_manual_review(ai=AI, security=None, merge_error=None, language="python"):
    app, engine, factory, project_id = create_test_app()
    patches = [patch("app.routes.code_reviews.review_code", return_value=ai)]
    if security is not None:
        patches.append(patch("app.routes.code_reviews.collect_security_findings", return_value=security))
    if merge_error is not None:
        patches.append(patch("app.routes.code_reviews.merge_findings", side_effect=merge_error))
    try:
        for p in patches:
            p.start()
        with TestClient(app) as client:
            response = client.post("/code-reviews/", json={
                "project_id": project_id, "submitted_code": "print(1)\n", "programming_language": language})
            listed = client.get("/code-reviews/").json()
        with factory() as db:
            saved = db.query(CodeReview).one().analysis_status
            issues = db.query(ReviewIssue).all()
            evidence = [issue.confidence_evidence for issue in issues]
        return response.json(), listed, saved, evidence
    finally:
        for p in patches:
            p.stop()
        engine.dispose()


def test_manual_review_saves_both_scanner_statuses_and_returns_them():
    created, listed, saved, _ = run_manual_review(security=scanners())

    assert saved == {"semgrep": "completed", "bandit": "completed"}
    assert created["analysis_status"] == saved
    assert listed[0]["analysis_status"] == saved


def test_real_scanner_output_gives_one_saved_finding_per_problem():
    """Regression: 8 problems were saved as 24 findings, inflating History and
    Learning counts. Now each is saved once, with every source as evidence."""
    created, _, _, evidence = run_manual_review(security=scanners())

    assert created["review_status"] == "completed"
    assert len(created["issues"]) == 8
    # The AI's 3 problems were confirmed by both tools; the rest by both tools.
    assert evidence.count({"ai": True, "semgrep": True, "bandit": True}) == 3
    assert evidence.count({"semgrep": True, "bandit": True}) == 5
    assert {issue["confidence_level"] for issue in created["issues"]} == {"high", "medium"}


def test_scanners_that_are_not_installed_are_reported_as_unavailable():
    # tests/conftest.py makes both scanners "not installed" by default.
    created, _, saved, _ = run_manual_review()

    assert created["review_status"] == "completed"
    assert saved == {"semgrep": "unavailable", "bandit": "unavailable"}
    assert len(created["issues"]) == 3  # the AI's findings are still saved


def test_a_failed_scanner_is_reported_separately_from_the_other():
    _, _, saved, _ = run_manual_review(security=scanners(semgrep="failed"))
    assert saved == {"semgrep": "failed", "bandit": "completed"}


def test_an_unexpected_merge_error_keeps_the_ai_review_and_reports_failure():
    created, _, saved, evidence = run_manual_review(security=scanners(), merge_error=RuntimeError("bug"))

    assert created["review_status"] == "completed"
    assert saved == {"semgrep": "failed", "bandit": "failed"}
    assert evidence == [{"ai": True}] * 3


def test_non_python_code_is_not_scanned():
    _, _, saved, _ = run_manual_review(language="javascript")
    assert saved == {"semgrep": "not_run", "bandit": "not_run"}


def test_a_failed_ai_review_records_no_scanner_status():
    app, engine, factory, project_id = create_test_app()
    try:
        with patch("app.routes.code_reviews.review_code", side_effect=RuntimeError("AI down")), TestClient(app) as client:
            created = client.post("/code-reviews/", json={
                "project_id": project_id, "submitted_code": "print(1)\n", "programming_language": "python"}).json()
        assert created["review_status"] == "failed"
        assert created["analysis_status"] is None
    finally:
        engine.dispose()


# --- Pull request reviews (Stage 11) -------------------------------------------

def test_pull_request_review_combines_file_statuses(env):  # noqa: F811
    # Two Python files are reviewed; Semgrep fails on one of them.
    statuses = iter([scanners(semgrep="failed", with_findings=False), scanners(with_findings=False)])
    with patch.object(pr_review_service, "collect_security_findings", side_effect=lambda code, language: next(statuses)):
        review_id = submit(env).json()["id"]

    review = detail(env, review_id)
    assert review["review_status"] == "completed"
    assert review["analysis_status"] == {"semgrep": "failed", "bandit": "completed"}


def test_pull_request_review_reports_unavailable_scanners(env):  # noqa: F811
    review = detail(env, submit(env).json()["id"])
    assert review["analysis_status"] == {"semgrep": "unavailable", "bandit": "unavailable"}
