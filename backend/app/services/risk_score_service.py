
# Stage 8: Pull Request Risk Score
# Calculates finding-based merge risk using existing AI review results.

SEVERITY_POINTS = {
    "high": 30,
    "medium": 15,
    "low": 5,
}

CATEGORY_GROUPS = {
    "security": "security",
    "input_validation": "security",
    "testing": "testing",
    "code_quality": "maintainability",
    "error_handling": "maintainability",
    "logic": "maintainability",
    "database": "maintainability",
    "performance": "performance",
}

CATEGORY_WEIGHTS = {
    "security": 0.35,
    "testing": 0.25,
    "maintainability": 0.25,
    "performance": 0.15,
}

MINIMUM_RISK = {
    "high": 70,
    "medium": 40,
    "low": 10,
}


def calculate_risk(issues: list[dict]) -> dict:
    """
    Calculate a 0-100 finding-based risk score from review issues.

    This is a heuristic score, not the probability that a merge
    will fail. PR metadata and test execution results are not
    included until those inputs become available.
    """
    breakdown = {
        "security": 0,
        "testing": 0,
        "maintainability": 0,
        "performance": 0,
    }

    highest_severity = None

    for issue in issues:
        severity = str(issue.get("severity", "low")).lower()
        category = str(issue.get("category", "code_quality")).lower()

        if severity not in SEVERITY_POINTS:
            severity = "low"

        group = CATEGORY_GROUPS.get(category, "maintainability")

        breakdown[group] = min(
            100,
            breakdown[group] + SEVERITY_POINTS[severity],
        )

        if (
            highest_severity is None
            or SEVERITY_POINTS[severity] > SEVERITY_POINTS[highest_severity]
        ):
            highest_severity = severity

    weighted_score = sum(
        breakdown[group] * weight
        for group, weight in CATEGORY_WEIGHTS.items()
    )

    minimum_score = MINIMUM_RISK.get(highest_severity, 0)

    risk_score = min(
        100,
        max(round(weighted_score), minimum_score),
    )

    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_breakdown": breakdown,
    }
