"""Coordinate security scanner findings for MergeMind (Stage 13)."""

import logging

from app.services.bandit_service import (
    BanditScanError,
    BanditUnavailable,
    run_bandit_scan,
)
from app.services.finding_kinds import kind_from_text
from app.services.semgrep_service import (
    SemgrepScanError,
    SemgrepUnavailable,
    run_semgrep_scan,
)

logger = logging.getLogger(__name__)

# What happened to each scanner, saved with the review and shown to the user:
#   completed   - the scan ran (with or without findings)
#   failed      - it started but couldn't finish (timeout, crash, bad output)
#   unavailable - the scanner isn't installed on this server
#   not_run     - not applicable: only Python code is scanned
SCANNER_STATUSES = ("completed", "failed", "unavailable", "not_run")

# Findings of the same kind at most this many lines apart are one problem.
MERGE_LINE_DISTANCE = 1

_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def collect_security_findings(
    source_code: str,
    language: str,
) -> dict:
    """Collect Semgrep and Bandit findings without interrupting AI reviews."""

    result = {
        "semgrep": [],
        "semgrep_status": "not_run",
        "bandit": [],
        "bandit_status": "not_run",
    }

    if (language or "").lower() != "python":
        return result

    # Stage 13: Run Semgrep.
    try:
        result["semgrep"] = run_semgrep_scan(source_code)
        result["semgrep_status"] = "completed"
    except SemgrepUnavailable:
        logger.warning("Semgrep is not installed; continuing without Semgrep findings.")
        result["semgrep_status"] = "unavailable"
    except SemgrepScanError:
        logger.warning(
            "Semgrep analysis failed; continuing without Semgrep findings.",
            exc_info=True,
        )
        result["semgrep_status"] = "failed"

    # Stage 13: Run Bandit independently.
    try:
        result["bandit"] = run_bandit_scan(source_code)
        result["bandit_status"] = "completed"
    except BanditUnavailable:
        logger.warning("Bandit is not installed; continuing without Bandit findings.")
        result["bandit_status"] = "unavailable"
    except BanditScanError:
        logger.warning(
            "Bandit analysis failed; continuing without Bandit findings.",
            exc_info=True,
        )
        result["bandit_status"] = "failed"

    return result


def analysis_status(security_analysis: dict) -> dict:
    """The part of a collect_security_findings() result saved with a review."""
    return {
        "semgrep": security_analysis.get("semgrep_status", "not_run"),
        "bandit": security_analysis.get("bandit_status", "not_run"),
    }


def combine_statuses(statuses: list[dict]) -> dict | None:
    """One status per scanner for a pull request review, from its files.

    A failure in any file is reported; otherwise completed if any file was
    scanned, then unavailable, otherwise not_run.
    """
    if not statuses:
        return None
    combined = {}
    for scanner in ("semgrep", "bandit"):
        values = {status.get(scanner, "not_run") for status in statuses}
        combined[scanner] = "not_run"
        for value in ("failed", "completed", "unavailable"):
            if value in values:
                combined[scanner] = value
                break
    return combined


def _kind(finding: dict) -> str | None:
    # Scanner findings carry their kind; AI findings are read for one.
    return finding.get("kind") or kind_from_text(finding.get("title"), finding.get("explanation"))


def merge_findings(
    ai_findings: list[dict],
    semgrep_findings: list[dict],
    bandit_findings: list[dict] | None = None,
) -> list[dict]:
    """Combine findings that describe the same problem, keeping each source as evidence.

    Two findings are the same problem only if they are the same known kind of
    vulnerability, at most MERGE_LINE_DISTANCE lines apart, and from different
    sources. Titles, severities and CWE numbers are not compared: the tools
    word and rate the same problem differently. A finding whose kind is
    unknown is never merged. The merged finding keeps the first source's text
    (the AI's, when it found the problem), the highest severity, and every
    source in its evidence.
    """

    groups = []

    sources = [
        ("ai", ai_findings),
        ("semgrep", semgrep_findings),
        ("bandit", bandit_findings or []),
    ]

    for source, findings in sources:
        for finding in findings:
            issue = {key: value for key, value in finding.items() if key != "kind"}
            kind = _kind(finding)
            line = issue.get("line_number")

            match = None
            if kind and isinstance(line, int):
                candidates = [
                    group for group in groups
                    if group["kind"] == kind
                    and isinstance(group["line"], int)
                    and abs(group["line"] - line) <= MERGE_LINE_DISTANCE
                    and source not in group["issue"]["evidence"]
                ]
                if candidates:
                    match = min(candidates, key=lambda group: abs(group["line"] - line))

            if match is None:
                issue["evidence"] = {source: True}
                groups.append({"kind": kind, "line": line, "issue": issue})
                continue

            existing = match["issue"]
            existing["evidence"][source] = True
            if _SEVERITY_RANK.get(issue.get("severity"), 0) > _SEVERITY_RANK.get(existing.get("severity"), 0):
                existing["severity"] = issue["severity"]
            if not existing.get("suggested_fix") and issue.get("suggested_fix"):
                existing["suggested_fix"] = issue["suggested_fix"]

    return [group["issue"] for group in groups]
