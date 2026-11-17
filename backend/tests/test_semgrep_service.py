
"""Unit tests for Semgrep finding normalization."""

from app.services.semgrep_service import normalize_semgrep_finding


def test_high_severity_finding():
    """An ERROR finding should become a high-severity security issue."""

    finding = {
        "check_id": "python.security.eval-detected",
        "start": {"line": 5},
        "extra": {
            "severity": "ERROR",
            "message": "Detected use of eval().",
        },
    }

    result = normalize_semgrep_finding(finding)

    assert result is not None
    assert result["title"] == "python.security.eval-detected"
    assert result["category"] == "security"
    assert result["severity"] == "high"
    assert result["line_number"] == 5
    assert result["explanation"] == "Detected use of eval()."


def test_warning_severity_finding():
    """A WARNING finding should become a medium-severity issue."""

    finding = {
        "check_id": "python.security.possible-injection",
        "start": {"line": 12},
        "extra": {
            "severity": "WARNING",
            "message": "Possible injection vulnerability.",
        },
    }

    result = normalize_semgrep_finding(finding)

    assert result is not None
    assert result["severity"] == "medium"
    assert result["line_number"] == 12


def test_invalid_finding():
    """Malformed findings should be ignored without crashing."""

    finding = {
        "check_id": "invalid-rule",
        "start": {"line": "not-a-number"},
        "extra": {
            "severity": "ERROR",
            "message": "Invalid finding.",
        },
    }

    result = normalize_semgrep_finding(finding)

    assert result is None


import subprocess
from unittest.mock import patch

import pytest

from app.services.semgrep_service import (
    SemgrepScanError,
    run_semgrep_scan,
)


def test_semgrep_scan_success():
    """A successful scan should return normalized security findings."""

    mock_output = """
    {
        "results": [
            {
                "check_id": "python.security.eval-detected",
                "start": {"line": 2},
                "extra": {
                    "severity": "WARNING",
                    "message": "Detected unsafe eval()."
                }
            }
        ],
        "errors": []
    }
    """

    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=mock_output,
        stderr="",
    )

    with patch(
        "app.services.semgrep_service.subprocess.run",
        return_value=completed,
    ):
        findings = run_semgrep_scan(
            "result = eval(input())",
            "semgrep",
        )

    assert len(findings) == 1
    assert findings[0]["category"] == "security"
    assert findings[0]["severity"] == "medium"


def test_semgrep_scan_timeout():
    """A scanner timeout should raise an explicit error."""

    with patch(
        "app.services.semgrep_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["semgrep"],
            timeout=60,
        ),
    ):
        with pytest.raises(SemgrepScanError, match="timed out"):
            run_semgrep_scan("print('hello')", "semgrep")


def test_semgrep_scan_failure():
    """A failed scanner should not be treated as zero findings."""

    completed = subprocess.CompletedProcess(
        args=[],
        returncode=2,
        stdout="",
        stderr="Scanner failed",
    )

    with patch(
        "app.services.semgrep_service.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(SemgrepScanError, match="exit code 2"):
            run_semgrep_scan("print('hello')", "semgrep")
