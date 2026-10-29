
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models.models import CodeReview, ReviewIssue
from app.models.schemas import CodeReviewCreate, CodeReviewOut, ContextSummary
from app.services.ai_review_service import build_review_payload, review_code
from app.services.project_context_service import collect_project_context

# Stage 7: Import confidence scoring function
from app.services.confidence_service import calculate_confidence
# Stage 8: Import overall risk scoring function
from app.services.risk_score_service import calculate_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/code-reviews", tags=["code-reviews"])


@router.post("/", response_model=CodeReviewOut)
def create_code_review(review: CodeReviewCreate, db: Session = Depends(get_db)):
    context = None
    summary = None
    context_input = review.project_context
    try:
        if context_input is not None:
            context = collect_project_context(
                context_input.file_path, review.submitted_code, context_input.files,
                source_root=context_input.source_root,
            )
            summary = ContextSummary(
                file_path=context_input.file_path,
                selected_files=[file.path for file in context.files],
                total_chars=context.total_chars,
                unresolved_imports=list(context.unresolved_imports),
                omitted_files=list(context.omitted_files),
            )
        # Validate the final serialized prompt before creating a database row.
        build_review_payload(
            review.submitted_code, review.programming_language,
            project_context=context,
            file_path=context_input.file_path if context_input else None,
        )
    except RecursionError as error:
        raise HTTPException(
            status_code=422,
            detail="Submitted code is too complex to collect project context; submit a smaller file",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    def response():
        result = CodeReviewOut.model_validate(db_review)
        result.context_summary = summary
        return result

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
        if context_input is None:
            issues = review_code(review.submitted_code, review.programming_language)
        else:
            issues = review_code(
                review.submitted_code, review.programming_language,
                project_context=context, file_path=context_input.file_path,
            )
    except Exception as error:
        logger.exception("AI review failed for code review id=%s: %s", db_review.id, error)
        db_review.review_status = "failed"
        db.commit()
        db.refresh(db_review)
        return response()

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

    
    # Stage 8: Calculate overall risk from the detected issues.
    risk = calculate_risk(issues)

    db_review.risk_score = risk["risk_score"]
    db_review.risk_level = risk["risk_level"]
    db_review.risk_breakdown = risk["risk_breakdown"]

    db_review.review_status = "completed"
    db.commit()
    db.refresh(db_review)
    return response()


@router.get("/", response_model=list[CodeReviewOut])
def list_code_reviews(db: Session = Depends(get_db)):
    return (
        db.query(CodeReview)
        .options(joinedload(CodeReview.issues))
        .order_by(CodeReview.created_at.desc())
        .all()
    )
