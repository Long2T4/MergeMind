
from app.services.risk_score_service import calculate_risk


def test_no_issues():
    result = calculate_risk([])

    assert result["risk_score"] == 0
    assert result["risk_level"] == "low"
    assert all(score == 0 for score in result["risk_breakdown"].values())


def test_low_severity_issue():
    issues = [{"category": "code_quality", "severity": "low"}]

    result = calculate_risk(issues)

    assert result["risk_score"] == 10
    assert result["risk_level"] == "low"
    assert result["risk_breakdown"]["maintainability"] == 5


def test_medium_severity_issue():
    issues = [{"category": "testing", "severity": "medium"}]

    result = calculate_risk(issues)

    assert result["risk_score"] == 40
    assert result["risk_level"] == "medium"
    assert result["risk_breakdown"]["testing"] == 15


def test_high_severity_issue():
    issues = [{"category": "security", "severity": "high"}]

    result = calculate_risk(issues)

    assert result["risk_score"] == 70
    assert result["risk_level"] == "high"
    assert result["risk_breakdown"]["security"] == 30


def test_risk_score_capped_at_100():
    issues = [{"category": "security", "severity": "high"} for _ in range(20)]

    result = calculate_risk(issues)

    assert result["risk_score"] <= 100
    assert result["risk_breakdown"]["security"] == 100
    assert result["risk_level"] == "high"


def test_all_categories_grouped_correctly():
    issues = [
        {"category": "security", "severity": "low"},
        {"category": "input_validation", "severity": "low"},
        {"category": "testing", "severity": "low"},
        {"category": "code_quality", "severity": "low"},
        {"category": "error_handling", "severity": "low"},
        {"category": "logic", "severity": "low"},
        {"category": "database", "severity": "low"},
        {"category": "performance", "severity": "low"},
    ]

    result = calculate_risk(issues)

    assert result["risk_breakdown"] == {
        "security": 10,
        "testing": 5,
        "maintainability": 20,
        "performance": 5,
    }


def test_invalid_values_use_safe_defaults():
    issues = [{"category": "unknown", "severity": "unknown"}]

    result = calculate_risk(issues)

    assert result["risk_score"] == 10
    assert result["risk_breakdown"]["maintainability"] == 5
