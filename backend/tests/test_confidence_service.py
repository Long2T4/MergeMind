
from app.services.confidence_service import calculate_confidence


def test_high_confidence():
    # Test 1: Multiple tools confirm an issue.
    evidence = {
        "ai": True,
        "semgrep": True,
        "bandit": True,
        "test_failure": True,
        "git_history": False,
        "dependency": False,
    }

    result = calculate_confidence(evidence)

    assert result["confidence_score"] == 85
    assert result["confidence_level"] == "high"


def test_low_confidence():
    # Test 2: Only the AI detects an issue.
    evidence = {
        "ai": True,
        "semgrep": False,
        "bandit": False,
        "test_failure": False,
        "git_history": False,
        "dependency": False,
    }

    result = calculate_confidence(evidence)

    assert result["confidence_score"] == 20
    assert result["confidence_level"] == "low"
    assert result["recommendation"] == "Human verification needed"
