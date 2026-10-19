"""Stage 6: paginated historical reviews backed by MergeMind's existing tables.

Read-only: it does not create new database tables or modify review results.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.database.database import get_db
from app.models.models import CodeReview, ReviewIssue
from app.models.schemas import CodeReviewOut

router = APIRouter(prefix="/review-history", tags=["review-history"])


class ReviewHistoryPage(BaseModel):
    items: list[CodeReviewOut]
    total: int
    limit: int
    offset: int


class ReviewHistoryStats(BaseModel):
    total_reviews: int
    completed_reviews: int
    total_issues: int
    high_severity_issues: int


@router.get("/", response_model=ReviewHistoryPage)
def list_review_history(
    q: str = Query("", max_length=200),
    language: str = Query("", max_length=50),
    status: str = Query("", max_length=50),
    project_id: int | None = Query(None, ge=1),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    # Use the same CodeReview + ReviewIssue models already used by Stage 3-5.
    query = db.query(CodeReview)
    if project_id is not None:
        query = query.filter(CodeReview.project_id == project_id)
    if language:
        query = query.filter(func.lower(CodeReview.programming_language) == language.lower())
    if status:
        query = query.filter(func.lower(CodeReview.review_status) == status.lower())
    if q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CodeReview.programming_language.ilike(pattern),
                CodeReview.submitted_code.ilike(pattern),
            )
        )

    total = query.count()
    items = (
        query.options(selectinload(CodeReview.issues))
        .order_by(CodeReview.created_at.desc(), CodeReview.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ReviewHistoryPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats", response_model=ReviewHistoryStats)
def review_history_stats(
    project_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    reviews = db.query(CodeReview)
    issues = db.query(ReviewIssue).join(CodeReview, ReviewIssue.review_id == CodeReview.id)
    if project_id is not None:
        reviews = reviews.filter(CodeReview.project_id == project_id)
        issues = issues.filter(CodeReview.project_id == project_id)
    return ReviewHistoryStats(
        total_reviews=reviews.count(),
        completed_reviews=reviews.filter(CodeReview.review_status == "completed").count(),
        total_issues=issues.count(),
        high_severity_issues=issues.filter(func.lower(ReviewIssue.severity) == "high").count(),
    )
