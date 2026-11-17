
"""Coordinate security scanner findings for MergeMind."""

import logging

from app.services.semgrep_service import (
    SemgrepScanError,
    run_semgrep_scan,
)
from app.services.bandit_service import (
    BanditScanError,
    run_bandit_scan,
)

logger = logging.getLogger(__name__)


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

    if language.lower() != "python":
        return result

    # Stage 13: Run Semgrep.
    try:
        result["semgrep"] = run_semgrep_scan(source_code)
        result["semgrep_status"] = "completed"

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

    except BanditScanError:
        logger.warning(
            "Bandit analysis failed; continuing without Bandit findings.",
            exc_info=True,
        )
        result["bandit_status"] = "failed"

    return result


def merge_findings(
    ai_findings: list[dict],
    semgrep_findings: list[dict],
    bandit_findings: list[dict] | None = None,
) -> list[dict]:
    """Combine findings while preserving evidence from each source."""

    merged = []
    seen = {}

    sources = [
        ("ai", ai_findings),
        ("semgrep", semgrep_findings),
        ("bandit", bandit_findings or []),
    ]

    for source, findings in sources:
        for finding in findings:
            issue = finding.copy()

            title = str(issue.get("title", "")).lower().strip()

            normalized_title = "".join(
                character for character in title
                if character.isalnum()
            )

            key = (
                issue.get("category"),
                issue.get("severity"),
                issue.get("line_number"),
                normalized_title,
            )

            if key in seen:
                existing = merged[seen[key]]
                existing["evidence"][source] = True
            else:
                issue["evidence"] = {source: True}
                seen[key] = len(merged)
                merged.append(issue)

    return merged
