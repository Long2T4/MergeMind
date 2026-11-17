
"""Tests for Bandit security scanning and finding normalization."""

import json
import subprocess
from unittest.mock import patch

import pytest

from app.services.bandit_service import (
    BanditScanError,
    normalize_bandit_finding,
    run_bandit_scan,
)


def sample_bandit_finding():
    """Return a representative Bandit security finding."""
    return {
        "test_id": "B602",
        "issue_text": "subprocess call with shell=True identified.",
        "issue_severity": "HIGH",
        "issue_confidence": "HIGH",
        "line_number": 4,
    }


def test_normalize_high_severity_finding():
    """HIGH severity should map to MergeMind's high severity."""
    result = normalize_bandit_finding(sample_bandit_finding())

    assert result is not None
    # B602 is a known kind: a readable title and fix instead of "B602: ...".
    assert result["title"] == "Command run through a shell"
    assert "shell=True" in result["suggested_fix"]
    assert result["kind"] == "shell-injection"
    assert result["category"] == "security"
    assert result["severity"] == "high"
    assert result["line_number"] == 4


def test_normalize_low_severity_finding():
    """LOW severity should map to MergeMind's low severity."""
    finding = sample_bandit_finding()
    finding["issue_severity"] = "LOW"

    result = normalize_bandit_finding(finding)

    assert result["severity"] == "low"


def test_reject_invalid_finding():
    """Malformed findings should not enter the review database."""
    finding = sample_bandit_finding()
    finding["line_number"] = -1

    assert normalize_bandit_finding(finding) is None
    assert normalize_bandit_finding({}) is None
    assert normalize_bandit_finding(None) is None


def test_successful_bandit_scan():
    """Bandit exit code 1 with valid findings is successful."""
    output = {
        "errors": [],
        "results": [sample_bandit_finding()],
    }

    completed = subprocess.CompletedProcess(
        args=["bandit"],
        returncode=1,
        stdout=json.dumps(output),
        stderr="",
    )

    with patch(
        "app.services.bandit_service.subprocess.run",
        return_value=completed,
    ) as mock_run:
        findings = run_bandit_scan(
            "import subprocess",
            "bandit",
        )

    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    mock_run.assert_called_once()


def test_clean_bandit_scan():
    """A clean scan should return no findings."""
    output = {
        "errors": [],
        "results": [],
    }

    completed = subprocess.CompletedProcess(
        args=["bandit"],
        returncode=0,
        stdout=json.dumps(output),
        stderr="",
    )

    with patch(
        "app.services.bandit_service.subprocess.run",
        return_value=completed,
    ):
        findings = run_bandit_scan(
            "print('hello')",
            "bandit",
        )

    assert findings == []


def test_bandit_timeout():
    """A scanner timeout should raise a controlled error."""
    with patch(
        "app.services.bandit_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd="bandit",
            timeout=60,
        ),
    ):
        with pytest.raises(BanditScanError):
            run_bandit_scan("print('hello')", "bandit")


def test_bandit_invalid_json():
    """Invalid scanner output should raise a controlled error."""
    completed = subprocess.CompletedProcess(
        args=["bandit"],
        returncode=0,
        stdout="not valid json",
        stderr="",
    )

    with patch(
        "app.services.bandit_service.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(BanditScanError):
            run_bandit_scan("print('hello')", "bandit")


def test_bandit_unexpected_exit_code():
    """Unexpected scanner exit codes should be rejected."""
    completed = subprocess.CompletedProcess(
        args=["bandit"],
        returncode=2,
        stdout="",
        stderr="Bandit failed",
    )

    with patch(
        "app.services.bandit_service.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(BanditScanError):
            run_bandit_scan("print('hello')", "bandit")
