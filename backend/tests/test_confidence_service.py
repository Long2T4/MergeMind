
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

    # AI 20 + Semgrep 30 + Bandit 30 + failed test 20 = 100 (the maximum).
    assert result["confidence_score"] == 100
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


def test_independent_sources_agreeing_raise_the_level():
    """Stage 13: one source is low, two agreeing are medium, all three high."""
    cases = [
        ({"ai": True}, 20, "low"),
        ({"semgrep": True}, 30, "low"),
        ({"bandit": True}, 30, "low"),
        ({"ai": True, "semgrep": True}, 50, "medium"),
        ({"ai": True, "bandit": True}, 50, "medium"),
        ({"semgrep": True, "bandit": True}, 60, "medium"),
        ({"ai": True, "semgrep": True, "bandit": True}, 80, "high"),
    ]
    for evidence, score, level in cases:
        result = calculate_confidence(evidence)
        assert (result["confidence_score"], result["confidence_level"]) == (score, level), evidence
    # Never above 100, whatever the evidence.
    assert calculate_confidence({source: True for source in (
        "ai", "semgrep", "bandit", "test_failure", "git_history", "dependency")})["confidence_score"] == 100

