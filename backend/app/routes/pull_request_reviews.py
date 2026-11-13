"""Stage 11: start a review of a public GitHub pull request.

Everything that can be checked up front (URL, project, token, pull request
access, size, reviewable files) is checked before saving anything. The files
are then reviewed in a background task; poll GET /review-history/{id} for
progress.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db, get_session_factory
from app.models.schemas import CodeReviewOut, PullRequestReviewCreate
from app.services.github_service import GitHubError, get_github_client_factory, parse_pull_request_url
from app.services.pr_review_service import (
    PullRequestRejected, check_capacity, run_pull_request_review, start_pull_request_review,
)
from app.services.project_context_service import _project_path
from app.stage12.security import CurrentUser, get_current_user, get_owned_project

router = APIRouter(prefix="/pull-request-reviews", tags=["pull-request-reviews"])


@router.post("/", response_model=CodeReviewOut, status_code=202)
def create_pull_request_review(
    body: PullRequestReviewCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
    github_client=Depends(get_github_client_factory),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        ref = parse_pull_request_url(body.pr_url)
        source_root = _project_path(body.source_root.strip()) if body.source_root.strip() else ""
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # Stage 12: another user's project gets the same 404 as a missing one.
    # The duplicate and capacity checks below stay server-wide.
    if get_owned_project(db, body.project_id, user.id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        check_capacity(db, ref)
        with github_client() as client:
            review = start_pull_request_review(db, client, ref, body.project_id, source_root)
    except GitHubError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except PullRequestRejected as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None

    response = CodeReviewOut.model_validate(review)
    background_tasks.add_task(run_pull_request_review, review.id, session_factory, github_client)
    return response
