
"""Run Bandit security scans and normalize findings for MergeMind."""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from app.services.ai_review_service import (
    MAX_LINE_NUMBER,
    MAX_TITLE_CHARS,
)

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


class BanditScanError(Exception):
    """Raised when Bandit cannot complete a valid scan."""


def normalize_bandit_finding(finding: dict) -> dict | None:
    """Convert a Bandit finding into MergeMind's issue format."""

    if not isinstance(finding, dict):
        return None

    message = finding.get("issue_text")
    line_number = finding.get("line_number")
    severity = finding.get("issue_severity")
    test_id = finding.get("test_id")

    if not isinstance(message, str) or not message.strip():
        return None

    if (
        not isinstance(line_number, int)
        or isinstance(line_number, bool)
        or line_number < 1
        or line_number > MAX_LINE_NUMBER
    ):
        return None

    if not isinstance(severity, str):
        return None

    normalized_severity = SEVERITY_MAP.get(severity.upper())

    if normalized_severity is None:
        return None

    if not isinstance(test_id, str) or not test_id.strip():
        return None

    title = f"{test_id}: {message.strip()}"

    return {
        "title": title[:MAX_TITLE_CHARS],
        "category": "security",
        "severity": normalized_severity,
        "line_number": line_number,
        "explanation": message.strip(),
        "why_it_matters": (
            "Bandit identified a potential Python security issue "
            f"associated with rule {test_id}."
        ),
        "suggested_fix": (
            "Review the flagged code and apply the recommended "
            "security remediation for this Bandit rule."
        ),
    }


def run_bandit_scan(
    source_code: str,
    bandit_executable: str | None = None,
) -> list[dict]:
    """Run Bandit on Python source and return normalized findings."""

    if bandit_executable is None:
        bandit_executable = os.getenv(
            "BANDIT_EXECUTABLE",
            "bandit",
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = Path(temp_dir) / "submitted_code.py"
        source_file.write_text(source_code, encoding="utf-8")

        command = [
            bandit_executable,
            "-f",
            "json",
            "-q",
            str(source_file),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise BanditScanError(
                "Bandit scan timed out."
            ) from error
        except OSError as error:
            raise BanditScanError(
                "Bandit executable could not be started."
            ) from error

        # Bandit returns 0 for a clean scan and 1 when
        # security findings are detected.
        if result.returncode not in (0, 1):
            raise BanditScanError(
                f"Bandit exited with code {result.returncode}."
            )

        try:
            output = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise BanditScanError(
                "Bandit returned invalid JSON."
            ) from error

        if not isinstance(output, dict):
            raise BanditScanError(
                "Bandit returned an unexpected response."
            )

        if output.get("errors"):
            raise BanditScanError(
                "Bandit reported scanning errors."
            )

        findings = output.get("results")

        if not isinstance(findings, list):
            raise BanditScanError(
                "Bandit results were missing or invalid."
            )

        return [
            normalized
            for finding in findings
            if (
                normalized := normalize_bandit_finding(finding)
            ) is not None
        ]
