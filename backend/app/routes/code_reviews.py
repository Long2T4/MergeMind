
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models.models import CodeReview, ReviewIssue
from app.models.schemas import CodeReviewCreate, CodeReviewOut
from app.services.ai_review_service import review_code

# Stage 7: Import confidence scoring function
from app.services.confidence_service import calculate_confidence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/code-reviews", tags=["code-reviews"])


@router.post("/", response_model=CodeReviewOut)
def create_code_review(review: CodeReviewCreate, db: Session = Depends(get_db)):
    db_review = CodeReview(
        project_id=review.project_id,
        submitted_code=review.submitted_code,
        programming_language=review.programming_language,
        review_status="pending",
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)

    try:
        issues = review_code(review.submitted_code, review.programming_language)
    except Exception as error:
        logger.exception("AI review failed for code review id=%s: %s", db_review.id, error)
        db_review.review_status = "failed"
        db.commit()
        db.refresh(db_review)
        return db_review

    for issue in issues:
        evidence = {"ai": True}
        confidence = calculate_confidence(evidence)

        db.add(
            ReviewIssue(
                review_id=db_review.id,
                **issue,
                confidence_score=confidence["confidence_score"],
                confidence_level=confidence["confidence_level"],
                confidence_evidence=evidence,
            )
        )

    db_review.review_status = "completed"
    db.commit()
    db.refresh(db_review)
    return db_review


@router.get("/", response_model=list[CodeReviewOut])
def list_code_reviews(db: Session = Depends(get_db)):
    return (
        db.query(CodeReview)
        .options(joinedload(CodeReview.issues))
        .order_by(CodeReview.created_at.desc())
        .all()
    )
