
# Stage 7: Confidence Score
# Calculates how strongly the available evidence supports a finding.

EVIDENCE_WEIGHTS = {
    "ai": 20,
    "semgrep": 25,
    "bandit": 20,
    "test_failure": 20,
    "git_history": 10,
    "dependency": 5,
}


def calculate_confidence(evidence: dict) -> dict:
    """
    Calculate an evidence score between 0 and 100.

    Each confirmed source contributes its assigned weight.
    """

    score = 0

    for source, weight in EVIDENCE_WEIGHTS.items():
        if evidence.get(source) is True:
            score += weight

    if score >= 80:
        level = "high"
        recommendation = "Strong corroborating evidence"
    elif score >= 50:
        level = "medium"
        recommendation = "Human review recommended"
    else:
        level = "low"
        recommendation = "Human verification needed"

    return {
        "confidence_score": score,
        "confidence_level": level,
        "recommendation": recommendation,
    }
