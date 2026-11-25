"""Stage 6.1: analytics based exclusively on saved CodeReview/ReviewIssue records.

This endpoint reads the existing tables; no migrations, sample data, or writes.
The time axis uses UTC calendar buckets based on each review's created_at.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import CodeReview, ReviewIssue

router = APIRouter(prefix="/review-history", tags=["review-history"])

CATEGORY_KEYS = ("security", "logic", "performance", "code_quality", "other")
SEVERITY_KEYS = ("high", "medium", "low", "unclassified")


class TrendPoint(BaseModel):
    date: str  # UTC date at the beginning of the daily/weekly/monthly bucket
    high: int = 0
    medium: int = 0
    low: int = 0
    unclassified: int = 0
    security: int = 0
    logic: int = 0
    performance: int = 0
    code_quality: int = 0
    other: int = 0


class TrendSummary(BaseModel):
    total_reviews: int
    completed_reviews: int
    total_issues: int
    average_issues_per_review: float
    high_severity_issues: int


class ReviewTrendsOut(BaseModel):
    days: Literal["7", "30", "90", "all"]
    project_id: int | None
    granularity: Literal["day", "week", "month"]
    summary: TrendSummary
    points: list[TrendPoint]


def _bucket_start(day: date, start: date, granularity: str) -> date:
    if granularity == "month":
        return day.replace(day=1)
    if granularity == "week":
        return start + timedelta(days=((day - start).days // 7) * 7)
    return day


def _bucket_dates(start: date, end: date, granularity: str):
    current = start
    while current <= end:
        yield current
        if granularity == "month":
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            current += timedelta(days=7 if granularity == "week" else 1)


def _category_key(raw: str | None) -> str:
    value = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    return value if value in CATEGORY_KEYS else "other"


@router.get("/trends", response_model=ReviewTrendsOut)
def get_review_trends(
    days: Literal["7", "30", "90", "all"] = Query("30"),
    project_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    """Return non-paginated trends; never infer trends from the History page's 8 rows.

    7/30 days use one day per point; 90 days uses 7-day buckets; all-time uses
    calendar months. `last N days` includes today and the previous N-1 UTC dates.
    Category `other` includes testing, error_handling, input_validation,
    database, and any categories introduced in the future.
    """
    today = datetime.now(timezone.utc).date()
    granularity = "month" if days == "all" else "week" if days == "90" else "day"
    start = None if days == "all" else today - timedelta(days=int(days) - 1)
    filters = []
    if start is not None:
        filters.append(CodeReview.created_at >= datetime.combine(start, datetime.min.time()))
    if project_id is not None:
        filters.append(CodeReview.project_id == project_id)

    total_reviews, completed_reviews, first_date = (
        db.query(
            func.count(CodeReview.id),
            func.sum(case((func.lower(CodeReview.review_status) == "completed", 1), else_=0)),
            func.min(CodeReview.created_at),
        )
        .filter(*filters)
        .one()
    )
    total_reviews = total_reviews or 0
    completed_reviews = completed_reviews or 0
    if days == "all" and first_date:
        start = first_date.date().replace(day=1)

    # One grouped database query; rows are issues assigned to the day their
    # parent review was submitted, so review counts and issue trends align.
    day_expression = func.date(CodeReview.created_at)
    issue_rows = (
        db.query(
            day_expression.label("day"),
            func.lower(func.trim(ReviewIssue.severity)).label("severity"),
            func.lower(func.trim(ReviewIssue.category)).label("category"),
            func.count(ReviewIssue.id).label("issue_count"),
        )
        .join(CodeReview, ReviewIssue.review_id == CodeReview.id)
        .filter(*filters)
        .group_by(day_expression, func.lower(func.trim(ReviewIssue.severity)),
                  func.lower(func.trim(ReviewIssue.category)))
        .all()
    )

    buckets = defaultdict(lambda: {key: 0 for key in (*SEVERITY_KEYS, *CATEGORY_KEYS)})
    total_issues = 0
    high_severity_issues = 0
    for row in issue_rows:
        day = date.fromisoformat(str(row.day))
        bucket = _bucket_start(day, start, granularity)
        count = int(row.issue_count)
        severity = (row.severity or "").strip().lower()
        severity = severity if severity in SEVERITY_KEYS else "unclassified"
        category = _category_key(row.category)
        buckets[bucket][severity] += count
        buckets[bucket][category] += count
        total_issues += count
        if severity == "high":
            high_severity_issues += count

    # Empty all-time datasets have no artificial dates or artificial issues.
    if start is None:
        points = []
    else:
        points = [
            TrendPoint(date=bucket.isoformat(), **buckets[bucket])
            for bucket in _bucket_dates(start, today, granularity)
        ]

    return ReviewTrendsOut(
        days=days,
        project_id=project_id,
        granularity=granularity,
        summary=TrendSummary(
            total_reviews=total_reviews,
            completed_reviews=completed_reviews,
            total_issues=total_issues,
            average_issues_per_review=round(total_issues / total_reviews, 2) if total_reviews else 0,
            high_severity_issues=high_severity_issues,
        ),
        points=points,
    )
