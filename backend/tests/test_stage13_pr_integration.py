
"""Stage 13: GitHub PR integration tests for security scanners."""

from unittest.mock import patch

from app.models.models import ReviewIssue
from app.services import pr_review_service

from test_pull_request_reviews import (
    env,
    submit,
    detail,
    APP_PY,
)


def test_pr_review_saves_bandit_evidence(env):
    """Bandit findings should be saved with their source evidence."""

    bandit_issue = {
        "title": "B602: Unsafe shell execution",
        "category": "security",
        "severity": "high",
        "line_number": 4,
        "explanation": "Shell execution may be unsafe.",
        "why_it_matters": "Untrusted commands may be executed.",
        "suggested_fix": "Avoid shell=True.",
    }

    def scanner_results(code, language):
        if code == APP_PY:
            return {
                "semgrep": [],
                "semgrep_status": "completed",
                "bandit": [bandit_issue],
                "bandit_status": "completed",
            }

        return {
            "semgrep": [],
            "semgrep_status": "completed",
            "bandit": [],
            "bandit_status": "completed",
        }

    with patch.object(
        pr_review_service,
        "collect_security_findings",
        side_effect=scanner_results,
    ):
        response = submit(env)

    assert response.status_code == 202

    with env.factory() as db:
        issues = (
            db.query(ReviewIssue)
            .filter(ReviewIssue.title == bandit_issue["title"])
            .all()
        )

        assert len(issues) == 1
        assert issues[0].confidence_evidence == {
            "bandit": True,
        }


def test_pr_review_merges_claude_and_semgrep(env):
    """Matching Claude and Semgrep findings retain both sources."""

    semgrep_issue = {
        "title": "eval is dangerous",
        "category": "security",
        "severity": "high",
        "line_number": 9,
        "explanation": "Dynamic code execution.",
        "why_it_matters": "Potential code injection.",
        "suggested_fix": "Avoid eval.",
    }

    def scanner_results(code, language):
        if code == APP_PY:
            return {
                "semgrep": [semgrep_issue],
                "semgrep_status": "completed",
                "bandit": [],
                "bandit_status": "completed",
            }

        return {
            "semgrep": [],
            "semgrep_status": "completed",
            "bandit": [],
            "bandit_status": "completed",
        }

    with patch.object(
        pr_review_service,
        "collect_security_findings",
        side_effect=scanner_results,
    ):
        response = submit(env)

    assert response.status_code == 202

    with env.factory() as db:
        issues = (
            db.query(ReviewIssue)
            .filter(ReviewIssue.title == "eval is dangerous")
            .all()
        )

        assert len(issues) == 1
        assert issues[0].confidence_evidence == {
            "ai": True,
            "semgrep": True,
        }
