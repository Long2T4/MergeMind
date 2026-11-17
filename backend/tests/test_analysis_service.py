
"""Tests for the shared security analysis service."""

from unittest.mock import patch

from app.services.analysis_service import (
    collect_security_findings,
    merge_findings,
)
from app.services.semgrep_service import SemgrepScanError
from app.services.confidence_service import calculate_confidence


def test_successful_semgrep_analysis():
    """Verify successful scans return findings."""

    sample_finding = {
        "title": "Unsafe eval()",
        "category": "security",
        "severity": "medium",
        "line_number": 2,
        "explanation": "Detected unsafe eval().",
        "why_it_matters": "Potential code injection.",
        "suggested_fix": "Avoid eval().",
    }

    with patch(
        "app.services.analysis_service.run_semgrep_scan",
        return_value=[sample_finding],
    ) as mock_scan:
        result = collect_security_findings(
            "result = eval(input())",
            "python",
        )

    assert result["semgrep_status"] == "completed"
    assert len(result["semgrep"]) == 1
    assert result["semgrep"][0]["title"] == "Unsafe eval()"
    mock_scan.assert_called_once_with("result = eval(input())")


def test_failed_semgrep_analysis():
    """Scanner failures should not crash the analysis service."""

    with patch(
        "app.services.analysis_service.run_semgrep_scan",
        side_effect=SemgrepScanError("Scanner unavailable"),
    ):
        result = collect_security_findings(
            "print('hello')",
            "python",
        )

    assert result["semgrep_status"] == "failed"
    assert result["semgrep"] == []


def test_unsupported_language():
    """Unsupported languages should skip Semgrep."""

    with patch(
        "app.services.analysis_service.run_semgrep_scan",
    ) as mock_scan:
        result = collect_security_findings(
            "console.log('hello')",
            "javascript",
        )

    assert result["semgrep_status"] == "not_run"
    assert result["semgrep"] == []
    mock_scan.assert_not_called()


def test_merge_findings_preserves_evidence():
    """Matching AI and Semgrep findings should retain both sources."""

    ai_finding = {
        "title": "Unsafe eval",
        "category": "security",
        "severity": "medium",
        "line_number": 10,
        "explanation": "Unsafe execution of user input.",
        "why_it_matters": "Potential code injection.",
        "suggested_fix": "Avoid eval.",
    }

    semgrep_finding = {
        **ai_finding,
        "title": "Unsafe Eval",
    }

    merged = merge_findings(
        [ai_finding],
        [semgrep_finding],
    )

    assert len(merged) == 1
    assert merged[0]["evidence"] == {
        "ai": True,
        "semgrep": True,
    }


def test_merge_findings_keeps_different_vulnerabilities():
    """Different vulnerabilities on the same line must remain separate."""

    ai_finding = {
        "title": "SQL Injection",
        "category": "security",
        "severity": "high",
        "line_number": 10,
        "explanation": "User input is used in a SQL query.",
        "why_it_matters": "Could expose database information.",
        "suggested_fix": "Use parameterized queries.",
    }

    semgrep_finding = {
        "title": "Hardcoded Password",
        "category": "security",
        "severity": "high",
        "line_number": 10,
        "explanation": "A password is hardcoded in the source.",
        "why_it_matters": "Could expose credentials.",
        "suggested_fix": "Use environment variables.",
    }

    merged = merge_findings(
        [ai_finding],
        [semgrep_finding],
    )

    assert len(merged) == 2
    assert merged[0]["evidence"] == {"ai": True}
    assert merged[1]["evidence"] == {"semgrep": True}


def test_merged_findings_confidence_score():
    """Combined AI and Semgrep evidence should increase confidence."""

    ai_finding = {
        "title": "Unsafe eval",
        "category": "security",
        "severity": "medium",
        "line_number": 10,
        "explanation": "Unsafe execution of user input.",
        "why_it_matters": "Potential code injection.",
        "suggested_fix": "Avoid eval.",
    }

    semgrep_finding = {
        **ai_finding,
        "title": "Unsafe Eval",
    }

    merged = merge_findings(
        [ai_finding],
        [semgrep_finding],
    )

    assert len(merged) == 1

    confidence = calculate_confidence(merged[0]["evidence"])

    # Stage 13 weights: AI + one scanner is medium.
    assert confidence["confidence_score"] == 50
    assert confidence["confidence_level"] == "medium"
