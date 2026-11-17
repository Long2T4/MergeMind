"""Run Bandit security scans and normalize findings for MergeMind (Stage 13).

Bandit only parses the submitted code; it is never executed. Bandit is a
backend dependency (requirements.txt) and runs as the `bandit` executable,
or the path in BANDIT_EXECUTABLE.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from app.services.ai_review_service import (
    MAX_LINE_NUMBER,
    MAX_TITLE_CHARS,
)
from app.services.finding_kinds import KINDS, kind_for_bandit_test

logger = logging.getLogger(__name__)

SCAN_TIMEOUT_SECONDS = 30

# Checks that add noise when reviewing one file: warnings about merely
# importing pickle/subprocess (B403, B404), subprocess calls without a shell
# (B603, B607) and assert statements (B101).
SKIPPED_TESTS = ("B101", "B403", "B404", "B603", "B607")

SEVERITY_MAP = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


class BanditScanError(Exception):
    """Raised when Bandit cannot complete a valid scan."""


class BanditUnavailable(BanditScanError):
    """Raised when the Bandit executable isn't installed."""


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

    # Bandit itself isn't sure about these; they're mostly noise.
    if str(finding.get("issue_confidence", "")).upper() == "LOW":
        return None

    kind = kind_for_bandit_test(test_id)
    test_name = finding.get("test_name")
    readable_name = (
        test_name.replace("_", " ").capitalize()
        if isinstance(test_name, str) and test_name.strip()
        else f"Bandit check {test_id}"
    )
    more_info = finding.get("more_info")

    if kind:
        suggested_fix = KINDS[kind].fix
    elif isinstance(more_info, str) and more_info.startswith("https://"):
        suggested_fix = f"See Bandit's guidance for {test_id}: {more_info}"
    else:
        suggested_fix = None

    return {
        "title": (KINDS[kind].title if kind else readable_name)[:MAX_TITLE_CHARS],
        "category": "security",
        "severity": normalized_severity,
        "line_number": line_number,
        "explanation": message.strip(),
        "why_it_matters": f"Bandit check {test_id} flagged this line.",
        "suggested_fix": suggested_fix,
        # Internal: used to match this finding with others, not saved.
        "kind": kind,
    }


def _default_executable() -> str:
    """BANDIT_EXECUTABLE, else the bandit installed next to this Python (it's
    a backend dependency, so it's there even if the venv isn't activated),
    else `bandit` on PATH."""
    configured = os.getenv("BANDIT_EXECUTABLE")
    if configured:
        return configured
    for name in ("bandit.exe", "bandit"):
        candidate = Path(sys.executable).with_name(name)
        if candidate.is_file():
            return str(candidate)
    return "bandit"


def run_bandit_scan(
    source_code: str,
    bandit_executable: str | None = None,
) -> list[dict]:
    """Run Bandit on Python source and return normalized findings."""

    if bandit_executable is None:
        bandit_executable = _default_executable()

    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = Path(temp_dir) / "submitted_code.py"
        source_file.write_text(source_code, encoding="utf-8")

        command = [
            bandit_executable,
            "-f",
            "json",
            "-q",
            "--skip",
            ",".join(SKIPPED_TESTS),
            str(source_file),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SCAN_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise BanditScanError(
                "Bandit scan timed out."
            ) from error
        except FileNotFoundError as error:
            raise BanditUnavailable(
                "Bandit is not installed."
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

    findings = output.get("results")

    if not isinstance(findings, list):
        raise BanditScanError(
            "Bandit results were missing or invalid."
        )

    if output.get("errors"):
        # For example, code Bandit couldn't parse. Keep any results it still
        # produced; with none, the scan didn't really happen.
        if not findings:
            raise BanditScanError(
                "Bandit reported scanning errors."
            )
        logger.warning("Bandit reported errors but returned %d findings.", len(findings))

    return [
        normalized
        for finding in findings
        if (
            normalized := normalize_bandit_finding(finding)
        ) is not None
    ]
