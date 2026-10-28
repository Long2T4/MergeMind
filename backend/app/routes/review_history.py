"""Stage 6: paginated historical reviews backed by MergeMind's existing tables.

Read-only: it does not create new database tables or modify review results.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.database import get_db
from app.models.models import CodeReview, ReviewIssue
from app.models.schemas import CodeReviewOut

router = APIRouter(prefix="/review-history", tags=["review-history"])

CODE_PREVIEW_LENGTH = 160


class ReviewHistoryItem(BaseModel):
    """Lightweight list row: full code and issues come from GET /review-history/{id}."""
    id: int
    project_id: int
    programming_language: str
    review_status: str
    created_at: datetime
    code_preview: str
    issue_count: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int


class ReviewHistoryPage(BaseModel):
    items: list[ReviewHistoryItem]
    total: int
    limit: int
    offset: int


class ReviewHistoryStats(BaseModel):
    """Totals for the reviews matching the same filters as the list."""
    total_reviews: int
    completed_reviews: int
    total_issues: int
    high_severity_issues: int


def _review_filters(q: str, language: str, status: str, project_id: int | None) -> list:
    conditions = []
    if project_id is not None:
        conditions.append(CodeReview.project_id == project_id)
    if language:
        conditions.append(func.lower(CodeReview.programming_language) == language.lower())
    if status:
        conditions.append(func.lower(CodeReview.review_status) == status.lower())
    if q.strip():
        # autoescape makes "%" and "_" literal; the term stays a bound parameter.
        term = q.strip()
        conditions.append(
            or_(
                CodeReview.programming_language.icontains(term, autoescape=True),
                CodeReview.submitted_code.icontains(term, autoescape=True),
            )
        )
    return conditions


def _severity_is(level: str):
    return case((func.lower(ReviewIssue.severity) == level, 1), else_=0)


def _is_high_severity():
    return _severity_is("high")


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
    query = db.query(CodeReview).filter(*_review_filters(q, language, status, project_id))
    total = query.count()
    rows = (
        query.with_entities(
            CodeReview.id,
            CodeReview.project_id,
            CodeReview.programming_language,
            CodeReview.review_status,
            CodeReview.created_at,
            func.substr(CodeReview.submitted_code, 1, CODE_PREVIEW_LENGTH).label("code_preview"),
        )
        .order_by(CodeReview.created_at.desc(), CodeReview.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # One grouped query for the issue counts of this page only.
    counts = {}
    page_ids = [row.id for row in rows]
    if page_ids:
        counts = {
            review_id: (issue_count, high or 0, medium or 0, low or 0)
            for review_id, issue_count, high, medium, low in (
                db.query(
                    ReviewIssue.review_id,
                    func.count(ReviewIssue.id),
                    func.sum(_severity_is("high")),
                    func.sum(_severity_is("medium")),
                    func.sum(_severity_is("low")),
                )
                .filter(ReviewIssue.review_id.in_(page_ids))
                .group_by(ReviewIssue.review_id)
                .all()
            )
        }

    items = []
    for row in rows:
        issue_count, high_count, medium_count, low_count = counts.get(row.id, (0, 0, 0, 0))
        items.append(ReviewHistoryItem(
            id=row.id,
            project_id=row.project_id,
            programming_language=row.programming_language,
            review_status=row.review_status,
            created_at=row.created_at,
            code_preview=row.code_preview or "",
            issue_count=issue_count,
            high_severity_count=high_count,
            medium_severity_count=medium_count,
            low_severity_count=low_count,
        ))
    return ReviewHistoryPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats", response_model=ReviewHistoryStats)
def review_history_stats(
    q: str = Query("", max_length=200),
    language: str = Query("", max_length=50),
    status: str = Query("", max_length=50),
    project_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    conditions = _review_filters(q, language, status, project_id)
    total_reviews, completed_reviews = (
        db.query(
            func.count(CodeReview.id),
            func.sum(case((func.lower(CodeReview.review_status) == "completed", 1), else_=0)),
        )
        .filter(*conditions)
        .one()
    )
    matching_ids = select(CodeReview.id).where(*conditions)
    total_issues, high_severity_issues = (
        db.query(func.count(ReviewIssue.id), func.sum(_is_high_severity()))
        .filter(ReviewIssue.review_id.in_(matching_ids))
        .one()
    )
    return ReviewHistoryStats(
        total_reviews=total_reviews,
        completed_reviews=completed_reviews or 0,
        total_issues=total_issues,
        high_severity_issues=high_severity_issues or 0,
    )


@router.get("/{review_id}", response_model=CodeReviewOut)
def get_review_history_detail(
    review_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    review = (
        db.query(CodeReview)
        .options(selectinload(CodeReview.issues))
        .filter(CodeReview.id == review_id)
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
