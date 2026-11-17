
"""Routes for manual AI code reviews and security analysis."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models.models import CodeReview, ReviewIssue
from app.models.schemas import (
    CodeReviewCreate,
    CodeReviewOut,
    ContextSummary,
)

from app.services.ai_review_service import (
    build_review_payload,
    review_code,
)
from app.services.analysis_service import (
    collect_security_findings,
    merge_findings,
)
from app.services.project_context_service import (
    collect_project_context,
)
from app.services.confidence_service import calculate_confidence
from app.services.risk_score_service import calculate_risk

from app.stage12.security import (
    CurrentUser,
    get_current_user,
    get_owned_project,
    owned_project_ids,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/code-reviews",
    tags=["code-reviews"],
)

# Stage 12: Limit manual AI reviews across all users.
MAX_MANUAL_REVIEWS_PER_HOUR = 30


@router.post("/", response_model=CodeReviewOut)
def create_code_review(
    review: CodeReviewCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    context = None
    summary = None
    context_input = review.project_context

    # --------------------------------------------------
    # Stage 12: Validate project context and AI payload.
    # --------------------------------------------------
    try:
        if context_input is not None:
            context = collect_project_context(
                context_input.file_path,
                review.submitted_code,
                context_input.files,
                source_root=context_input.source_root,
            )

            summary = ContextSummary(
                file_path=context_input.file_path,
                selected_files=[
                    file.path for file in context.files
                ],
                total_chars=context.total_chars,
                unresolved_imports=list(
                    context.unresolved_imports
                ),
                omitted_files=list(context.omitted_files),
            )

        build_review_payload(
            review.submitted_code,
            review.programming_language,
            project_context=context,
            file_path=(
                context_input.file_path
                if context_input
                else None
            ),
        )

    except RecursionError as error:
        raise HTTPException(
            status_code=422,
            detail=(
                "Submitted code is too complex to collect "
                "project context; submit a smaller file"
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    # --------------------------------------------------
    # Stage 12: Verify project ownership.
    # --------------------------------------------------
    if get_owned_project(
        db,
        review.project_id,
        user.id,
    ) is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    # --------------------------------------------------
    # Stage 12: Enforce manual review rate limits.
    # --------------------------------------------------
    recent_manual = (
        db.query(func.count(CodeReview.id))
        .filter(
            CodeReview.pull_request_id.is_(None),
            CodeReview.created_at >= (
                datetime.utcnow() - timedelta(hours=1)
            ),
        )
        .scalar()
    )

    if recent_manual >= MAX_MANUAL_REVIEWS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=(
                f"MergeMind runs at most "
                f"{MAX_MANUAL_REVIEWS_PER_HOUR} "
                "manual reviews per hour. Try again later."
            ),
        )

    def response():
        result = CodeReviewOut.model_validate(db_review)
        result.context_summary = summary
        return result

    # --------------------------------------------------
    # Create pending review record.
    # --------------------------------------------------
    db_review = CodeReview(
        project_id=review.project_id,
        submitted_code=review.submitted_code,
        programming_language=review.programming_language,
        review_status="pending",
    )

    db.add(db_review)
    db.commit()
    db.refresh(db_review)

    # --------------------------------------------------
    # Stage 13: Step 1 - Claude AI analysis.
    # --------------------------------------------------
    try:
        if context_input is None:
            issues = review_code(
                review.submitted_code,
                review.programming_language,
            )
        else:
            issues = review_code(
                review.submitted_code,
                review.programming_language,
                project_context=context,
                file_path=context_input.file_path,
            )

    except Exception as error:
        logger.exception(
            "AI review failed for code review id=%s: %s",
            db_review.id,
            error,
        )

        db_review.review_status = "failed"
        db.commit()
        db.refresh(db_review)

        return response()

    # --------------------------------------------------
    # Stage 13: Step 2 - Semgrep and Bandit analysis.
    # --------------------------------------------------
    try:
        security_analysis = collect_security_findings(
            review.submitted_code,
            review.programming_language,
        )

        semgrep_findings = security_analysis["semgrep"]
        bandit_findings = security_analysis["bandit"]

        # Log scanner failures independently.
        if security_analysis["semgrep_status"] == "failed":
            logger.warning(
                "Semgrep failed for code review id=%s.",
                db_review.id,
            )

        if security_analysis["bandit_status"] == "failed":
            logger.warning(
                "Bandit failed for code review id=%s.",
                db_review.id,
            )

        # --------------------------------------------------
        # Stage 13: Step 3 - Merge findings from all sources.
        # --------------------------------------------------
        merged_issues = merge_findings(
            issues,
            semgrep_findings,
            bandit_findings,
        )

    except Exception:
        # An unexpected scanner or merging error must not
        # prevent the existing Claude review from completing.
        logger.exception(
            "Security analysis failed for code review id=%s; "
            "continuing with Claude findings.",
            db_review.id,
        )

        merged_issues = [
            {
                **issue,
                "evidence": {"ai": True},
            }
            for issue in issues
        ]

    # --------------------------------------------------
    # Stage 7: Confidence scoring.
    # Stage 8: Risk scoring.
    # Stage 13: Store combined security evidence.
    # --------------------------------------------------
    review_id = db_review.id

    try:
        risk_issues = []

        for merged_issue in merged_issues:
            # Copy the issue to avoid modifying the original.
            issue = merged_issue.copy()

            # Evidence is stored separately in the database.
            evidence = issue.pop(
                "evidence",
                {"ai": True},
            )

            # Stage 7: Calculate confidence from evidence.
            confidence = calculate_confidence(evidence)

            # Store issue details and confidence information.
            db.add(
                ReviewIssue(
                    review_id=review_id,
                    **issue,
                    confidence_score=confidence[
                        "confidence_score"
                    ],
                    confidence_level=confidence[
                        "confidence_level"
                    ],
                    confidence_evidence=evidence,
                )
            )

            # Stage 8: Risk scoring uses issue details.
            risk_issues.append(issue)

        # --------------------------------------------------
        # Stage 8: Calculate overall review risk.
        # --------------------------------------------------
        risk = calculate_risk(risk_issues)

        db_review.risk_score = risk["risk_score"]
        db_review.risk_level = risk["risk_level"]
        db_review.risk_breakdown = risk["risk_breakdown"]

        db_review.review_status = "completed"
        db.commit()

    except Exception as error:
        # Discard partial findings and mark the review failed.
        db.rollback()

        logger.exception(
            "Saving review findings failed for code review "
            "id=%s: %s",
            review_id,
            error,
        )

        db_review = db.get(CodeReview, review_id)

        if db_review is not None:
            db_review.review_status = "failed"
            db.commit()

    db.refresh(db_review)
    return response()


@router.get("/", response_model=list[CodeReviewOut])
def list_code_reviews(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return (
        db.query(CodeReview)
        .options(joinedload(CodeReview.issues))
        .filter(
            CodeReview.project_id.in_(
                owned_project_ids(user.id)
            )
        )
        .order_by(CodeReview.created_at.desc())
        .all()
    )