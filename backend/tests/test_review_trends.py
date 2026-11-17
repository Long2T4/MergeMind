"""Stage 6.1 regression tests; run with: cd backend && pytest tests/test_review_trends.py"""
import os
from datetime import datetime, timedelta

# The app normally reads DATABASE_URL from Supabase; these tests use SQLite only.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.models import CodeReview, Project, ReviewIssue, User
from app.routes.review_trends import get_review_trends


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_review(db, project_id, age_days, severities_and_categories, status="completed"):
    review = CodeReview(
        project_id=project_id,
        submitted_code="print('hello')",
        programming_language="python",
        review_status=status,
        created_at=datetime.utcnow() - timedelta(days=age_days),
    )
    db.add(review)
    db.flush()
    for severity, category in severities_and_categories:
        db.add(ReviewIssue(
            review_id=review.id, category=category, severity=severity,
            explanation="Saved issue", suggested_fix="Fix", created_at=review.created_at,
        ))
    db.commit()
    return review


def seed_projects(db):
    db.add(User(id=1, name="Tester", email="test@example.com"))
    db.add_all([Project(id=1, user_id=1, name="Alpha"), Project(id=2, user_id=1, name="Beta")])
    db.commit()


def test_reads_saved_reviews_without_paginating(db):
    seed_projects(db)
    # Nine records: previous page-limited charts would miss the first review.
    for _ in range(9):
        add_review(db, 1, 0, [("high", "security"), ("medium", "code_quality")])
    result = get_review_trends(days="7", project_id=1, db=db)
    assert result.summary.total_reviews == 9
    assert result.summary.total_issues == 18
    assert result.summary.high_severity_issues == 9
    assert result.summary.average_issues_per_review == 2
    assert sum(p.high for p in result.points) == 9
    assert sum(p.code_quality for p in result.points) == 9
    assert len(result.points) == 7


def test_range_and_project_filter(db):
    seed_projects(db)
    add_review(db, 1, 0, [("high", "security"), ("low", "logic")])
    add_review(db, 1, 45, [("medium", "performance")])
    add_review(db, 2, 0, [("high", "code_quality")])
    add_review(db, 1, 95, [("high", "security")])

    recent = get_review_trends(days="30", project_id=1, db=db)
    assert recent.summary.total_reviews == 1
    assert recent.summary.total_issues == 2
    assert sum(p.logic for p in recent.points) == 1
    assert recent.granularity == "day"

    quarterly = get_review_trends(days="90", project_id=1, db=db)
    assert quarterly.summary.total_reviews == 2
    assert quarterly.summary.total_issues == 3
    assert quarterly.granularity == "week"
    assert sum(p.performance for p in quarterly.points) == 1

    all_projects = get_review_trends(days="all", project_id=None, db=db)
    assert all_projects.summary.total_reviews == 4
    assert all_projects.summary.total_issues == 5
    assert all_projects.granularity == "month"


def test_zero_issue_and_failed_reviews_count_in_average(db):
    seed_projects(db)
    add_review(db, 1, 0, [("high", "testing")])
    add_review(db, 1, 0, [], status="failed")
    report = get_review_trends(days="7", project_id=1, db=db)
    assert report.summary.total_reviews == 2
    assert report.summary.completed_reviews == 1
    assert report.summary.total_issues == 1
    assert report.summary.average_issues_per_review == 0.5
    assert sum(p.other for p in report.points) == 1


def test_empty_all_time(db):
    result = get_review_trends(days="all", project_id=None, db=db)
    assert result.summary.total_reviews == 0
    assert result.summary.average_issues_per_review == 0
    assert result.points == []
