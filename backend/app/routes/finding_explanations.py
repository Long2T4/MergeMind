"""Generate once per saved finding within the local API process."""

from collections import deque
from threading import Lock
from time import monotonic

from anthropic import APIError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import PullRequestFile
from app.models.schemas import BeginnerExplanation
from app.services.beginner_explanation_service import explain_finding
from app.stage12.security import CurrentUser, get_current_user, get_owned_finding

router = APIRouter(prefix="/account", tags=["finding explanations"])
MAX_ATTEMPTS_PER_HOUR = 20
MAX_CONCURRENT_GENERATIONS = 3
_generation_lock = Lock()
_active_findings: set[int] = set()
_attempts: deque[float] = deque()


@router.post("/findings/{issue_id}/beginner-explanation", response_model=BeginnerExplanation)
def get_or_generate_explanation(
    issue_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user),
):
    issue = get_owned_finding(db, issue_id, user.id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    if issue.beginner_explanation is not None:
        return issue.beginner_explanation

    with _generation_lock:
        # The initial read could have overlapped another request's commit.
        db.refresh(issue, attribute_names=["beginner_explanation"])
        if issue.beginner_explanation is not None:
            return issue.beginner_explanation
        if issue_id in _active_findings:
            raise HTTPException(status_code=409, detail="An explanation is already generating. Try again shortly.")
        now = monotonic()
        while _attempts and now - _attempts[0] >= 3600:
            _attempts.popleft()
        if len(_attempts) >= MAX_ATTEMPTS_PER_HOUR:
            raise HTTPException(status_code=429, detail="The hourly explanation limit was reached. Try again later.")
        if len(_active_findings) >= MAX_CONCURRENT_GENERATIONS:
            raise HTTPException(status_code=429, detail="The explanation service is busy. Try again shortly.")
        _active_findings.add(issue_id)
        _attempts.append(now)

    try:
        review = issue.review
        language = review.programming_language
        if review.pull_request_id and issue.file_name:
            file_language = (
                db.query(PullRequestFile.language)
                .filter(PullRequestFile.pull_request_id == review.pull_request_id,
                        PullRequestFile.path == issue.file_name)
                .limit(1)
                .scalar()
            )
            language = file_language or language
        try:
            explanation = explain_finding(issue, language)
        except (APIError, RuntimeError, ValidationError) as error:
            raise HTTPException(
                status_code=502, detail="Could not generate the explanation. Try again.",
            ) from error
        issue.beginner_explanation = explanation.model_dump()
        db.commit()
        return explanation
    finally:
        with _generation_lock:
            _active_findings.remove(issue_id)
