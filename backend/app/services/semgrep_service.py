"""Semgrep static-analysis integration for MergeMind (Stage 13).

Semgrep only parses the submitted code; it is never executed. The rules are
MergeMind's own (app/analysis_rules/semgrep-python.yml), so scans work
offline and give the same results every time.

Semgrep can't be installed in the same environment as the backend (its
dependencies conflict), so it runs as a separate executable: `semgrep` on
PATH, or the path in SEMGREP_EXECUTABLE. See README, "Static analysis".
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from app.services.ai_review_service import MAX_LINE_NUMBER, MAX_TITLE_CHARS
from app.services.finding_kinds import KINDS

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).resolve().parent.parent / "analysis_rules" / "semgrep-python.yml"
SCAN_TIMEOUT_SECONDS = 30

SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}


class SemgrepScanError(Exception):
    """Raised when Semgrep cannot complete a scan."""


class SemgrepUnavailable(SemgrepScanError):
    """Raised when the Semgrep executable isn't installed."""


def _first_sentence(text: str) -> str:
    sentence = text.strip().split(". ")[0].rstrip(".")
    return sentence[:MAX_TITLE_CHARS]


def normalize_semgrep_finding(finding: dict) -> dict | None:
    """Convert one Semgrep result into a MergeMind review issue."""
    if not isinstance(finding, dict):
        return None

    extra = finding.get("extra")
    start = finding.get("start")
    if not isinstance(extra, dict) or not isinstance(start, dict):
        return None

    message = extra.get("message")
    line = start.get("line")
    if not isinstance(message, str) or not message.strip():
        return None
    if isinstance(line, bool) or not isinstance(line, int) or not 1 <= line <= MAX_LINE_NUMBER:
        return None

    metadata = extra.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    kind = metadata.get("mergemind_kind")
    if kind not in KINDS:
        kind = None

    # Rule IDs get a prefix from the rules file's folder, so show only the
    # last part ("code-eval"), and match on the kind in the metadata.
    rule = str(finding.get("check_id") or "semgrep").split(".")[-1]
    cwe = metadata.get("cwe")
    cwe_text = f" ({cwe})" if isinstance(cwe, str) and cwe else ""

    fix = extra.get("fix")
    if kind:
        suggested_fix = KINDS[kind].fix
    elif isinstance(fix, str) and fix.strip():
        suggested_fix = fix.strip()
    else:
        suggested_fix = None

    return {
        "title": KINDS[kind].title if kind else _first_sentence(message),
        "category": "security",
        "severity": SEVERITY_MAP.get(str(extra.get("severity", "INFO")).upper(), "low"),
        "line_number": line,
        "explanation": message.strip(),
        "why_it_matters": f"Semgrep's {rule} rule matched this line{cwe_text}.",
        "suggested_fix": suggested_fix,
        # Internal: used to match this finding with others, not saved.
        "kind": kind,
    }


def run_semgrep_scan(
    source_code: str,
    semgrep_executable: str | None = None,
) -> list[dict]:
    """Scan Python source code with MergeMind's rules and return findings."""
    if semgrep_executable is None:
        semgrep_executable = os.getenv("SEMGREP_EXECUTABLE", "semgrep")

    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = Path(temp_dir) / "submitted_code.py"
        source_file.write_text(source_code, encoding="utf-8")

        command = [
            semgrep_executable,
            "scan",
            "--config",
            str(RULES_FILE),
            "--json",
            "--metrics=off",
            "--disable-version-check",
            "--no-git-ignore",
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
        except subprocess.TimeoutExpired as exc:
            raise SemgrepScanError("Semgrep scan timed out.") from exc
        except FileNotFoundError as exc:
            raise SemgrepUnavailable("Semgrep is not installed.") from exc
        except OSError as exc:
            raise SemgrepScanError("Semgrep could not start.") from exc

    if result.returncode != 0:
        raise SemgrepScanError(f"Semgrep failed with exit code {result.returncode}.")

    try:
        output = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SemgrepScanError("Invalid Semgrep JSON output.") from exc

    if not isinstance(output, dict):
        raise SemgrepScanError("Unexpected Semgrep output format.")

    findings = output.get("results")
    if not isinstance(findings, list):
        raise SemgrepScanError("Semgrep results are missing or invalid.")

    if output.get("errors"):
        # For example, code Semgrep couldn't parse. Keep any results it still
        # produced; with none, the scan didn't really happen.
        if not findings:
            raise SemgrepScanError("Semgrep reported scanning errors.")
        logger.warning("Semgrep reported errors but returned %d findings.", len(findings))

    return [
        normalized
        for finding in findings
        if (normalized := normalize_semgrep_finding(finding)) is not None
    ]
