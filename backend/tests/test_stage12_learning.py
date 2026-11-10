"""Stage 12 unit tests; real-model integration tests should also be run against the repo."""
from datetime import datetime
from types import SimpleNamespace

from app.stage12.routes import learning_metrics, normalize_category, FindingStatus
from pydantic import ValidationError
import pytest


def record(**fields):
    return SimpleNamespace(**fields)


def test_learning_counts_each_review_once_and_tracks_outcomes():
    reviews = [
        record(id=1, created_at=datetime(2026, 10, 1)),
        record(id=2, created_at=datetime(2026, 11, 2)),
        record(id=3, created_at=datetime(2026, 11, 3)),
    ]
    findings = [
        record(review_id=1, category='code_quality', status='fixed'),
        record(review_id=1, category='Security', status='open'),
        record(review_id=2, category='Code Quality', status='false_positive'),
        record(review_id=3, category='Code Quality', status='dismissed'),
    ]
    result = learning_metrics(reviews, findings)
    assert result['total_reviews'] == 3
    assert result['total_issues'] == 4
    assert result['fixed_issues'] == 1
    assert result['false_positives'] == 1
    assert result['statuses']['dismissed'] == 1
    assert result['categories']['Code Quality'] == 3
    assert result['repeated_categories'][0] == {'category': 'Code Quality', 'review_count': 3}
    assert result['monthly_categories'][0]['month'] == '2026-10'


def test_empty_learning():
    result = learning_metrics([], [])
    assert result['total_reviews'] == 0
    assert result['categories'] == {}
    assert result['repeated_categories'] == []


def test_category_normalization():
    assert normalize_category('input_validation') == 'Input Validation'
    assert normalize_category('ERROR-HANDLING') == 'Error Handling'
    assert normalize_category('unexpected') == 'Other'


def test_status_validation():
    assert FindingStatus(status='false_positive').status == 'false_positive'
    with pytest.raises(ValidationError):
        FindingStatus(status='resolved')
