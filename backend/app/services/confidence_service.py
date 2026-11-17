
# Stage 7: Confidence Score
# Calculates how strongly the available evidence supports a finding.
# It measures supporting evidence; it is not the probability that a finding
# is correct.
#
# Stage 13 weights: independent sources agreeing is what raises the level.
#   AI only 20 (low); one scanner only 30 (low)
#   AI + one scanner 50, both scanners 60 (medium)
#   AI + Semgrep + Bandit 80 (high)
# Scores are capped at 100. Findings saved earlier keep their stored scores.

EVIDENCE_WEIGHTS = {
    "ai": 20,
    "semgrep": 30,
    "bandit": 30,
    "test_failure": 20,
    "git_history": 10,
    "dependency": 5,
}

MAX_SCORE = 100


def calculate_confidence(evidence: dict) -> dict:
    """
    Calculate an evidence score between 0 and 100.

    Each confirmed source contributes its assigned weight.
    """

    score = 0

    for source, weight in EVIDENCE_WEIGHTS.items():
        if evidence.get(source) is True:
            score += weight

    score = min(score, MAX_SCORE)

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
