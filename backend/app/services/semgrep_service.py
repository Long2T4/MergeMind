import json
import subprocess
import tempfile
from pathlib import Path
import os

from click import command


class SemgrepScanError(Exception):
    """Raised when Semgrep cannot complete a scan."""


def run_semgrep_scan(
    source_code: str,
    semgrep_executable: str | None = None,
) -> list[dict]:

    if semgrep_executable is None:
        semgrep_executable = os.getenv("SEMGREP_EXECUTABLE", "semgrep")

    """Scan Python source code and return normalized findings."""

    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = Path(temp_dir) / "submitted_code.py"
        source_file.write_text(source_code, encoding="utf-8")

        command = [
            semgrep_executable,
            "scan",
            "--config",
            "p/security-audit",
            "--json",
            "--no-git-ignore",
            "--metrics=off",
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


        except subprocess.TimeoutExpired as exc:
            raise SemgrepScanError("Semgrep scan timed out.") from exc
        except OSError as exc:
            raise SemgrepScanError("Semgrep could not start.") from exc

        if result.returncode != 0:
            raise SemgrepScanError(
                f"Semgrep failed with exit code {result.returncode}."
            )

        try:
            output = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SemgrepScanError("Invalid Semgrep JSON output.") from exc

        if not isinstance(output, dict):
            raise SemgrepScanError("Unexpected Semgrep output format.")

        if output.get("errors"):
            raise SemgrepScanError("Semgrep reported scanning errors.")

        findings = output.get("results")
        if not isinstance(findings, list):
            raise SemgrepScanError("Semgrep results are missing or invalid.")

        return [
            normalized
            for finding in findings
            if (normalized := normalize_semgrep_finding(finding)) is not None
        ]




"""Semgrep static-analysis integration for MergeMind."""

from app.services.ai_review_service import MAX_LINE_NUMBER, MAX_TITLE_CHARS


SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}


def normalize_semgrep_finding(finding: dict) -> dict | None:
    """Convert one Semgrep result into a MergeMind review issue."""
    if not isinstance(finding, dict):
        return None

    extra = finding.get("extra")
    start = finding.get("start")

    if not isinstance(extra, dict) or not isinstance(start, dict):
        return None

    rule_id = finding.get("check_id")
    message = extra.get("message")
    line = start.get("line")

    if not isinstance(message, str) or not message.strip():
        return None

    if isinstance(line, bool) or not isinstance(line, int):
        return None
    if not 1 <= line <= MAX_LINE_NUMBER:
        return None

    metadata = extra.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    severity = str(extra.get("severity", "INFO")).upper()
    title = str(rule_id or "Semgrep security finding")
    title = title[:MAX_TITLE_CHARS]

    fix = extra.get("fix")
    if not isinstance(fix, str) or not fix.strip():
        fix = None

    return {
        "title": title,
        "category": "security",
        "severity": SEVERITY_MAP.get(severity, "low"),
        "line_number": line,
        "explanation": message.strip(),
        "why_it_matters": (
            "Semgrep identified a pattern that may introduce a security risk."
        ),
        "suggested_fix": fix.strip() if fix else None,
    }