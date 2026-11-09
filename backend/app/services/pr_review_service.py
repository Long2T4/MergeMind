"""Stage 11: review a public GitHub pull request, one changed file at a time.

start_pull_request_review runs during the request: it checks the pull request
and saves it with a "pending" review. run_pull_request_review runs afterwards
as a background task, with its own database session, and always finishes the
review as "completed" or "failed".
"""
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import CodeReview, PullRequest, PullRequestFile, ReviewIssue
from app.services.ai_review_service import review_code
from app.services.confidence_service import calculate_confidence
from app.services.diff_service import changed_lines, focus_findings, language_for_path, line_count, skip_reason
from app.services.github_service import FileTooLarge, GitHubClient, PullRequestRef
from app.services.project_context_service import collect_project_context, import_candidates
from app.services.risk_score_service import calculate_risk

logger = logging.getLogger(__name__)

# Limits (approved for Stage 11; change them here).
MAX_CHANGED_FILES = 30
MAX_CHANGED_LINES = 3_000
MAX_REVIEWED_FILES = 10
MAX_FILE_CHARS = 100_000
MAX_CONTEXT_FETCHES = 40
# review_issues.file_name holds at most 255 characters.
MAX_REVIEWABLE_PATH = 255
MAX_STORED_PATH = 500
MAX_SUBMITTED_CHARS = 200_000
# Each review can make up to 10 AI calls and about 50 GitHub requests, so
# only a few may run at once. Reviews pending longer than the window count
# as abandoned (see app.maintenance), so they don't block new ones.
MAX_ACTIVE_REVIEWS = 3
ACTIVE_WINDOW_MINUTES = 30
# Until accounts exist (Stage 12), a server-wide hourly cap bounds AI spending
# to MAX_REVIEWS_PER_HOUR x MAX_REVIEWED_FILES calls per hour.
MAX_REVIEWS_PER_HOUR = 20


class PullRequestRejected(ValueError):
    """The pull request can't be reviewed; the message is shown to the user."""
    status_code = 422


class PullRequestConflict(PullRequestRejected):
    status_code = 409


class TooManyReviews(PullRequestRejected):
    status_code = 429


def check_capacity(db: Session, ref: PullRequestRef) -> None:
    """Refuse a second review of the same pull request, and cap concurrent and hourly reviews."""
    since = datetime.utcnow() - timedelta(minutes=ACTIVE_WINDOW_MINUTES)
    active = (
        db.query(PullRequest)
        .join(CodeReview, CodeReview.pull_request_id == PullRequest.id)
        .filter(CodeReview.review_status == "pending", CodeReview.created_at >= since)
    )
    same = active.filter(
        func.lower(PullRequest.owner) == ref.owner.lower(),
        func.lower(PullRequest.repo) == ref.repo.lower(),
        PullRequest.number == ref.number,
    )
    if same.first() is not None:
        raise PullRequestConflict(
            "This pull request is already being reviewed. Open it from History to follow its progress."
        )
    last_hour = (
        db.query(func.count(CodeReview.id))
        .filter(CodeReview.pull_request_id.is_not(None),
                CodeReview.created_at >= datetime.utcnow() - timedelta(hours=1))
        .scalar()
    )
    if last_hour >= MAX_REVIEWS_PER_HOUR:
        raise TooManyReviews(
            f"MergeMind reviews at most {MAX_REVIEWS_PER_HOUR} pull requests per hour. Try again later."
        )
    if active.count() >= MAX_ACTIVE_REVIEWS:
        raise TooManyReviews(
            f"Too many pull request reviews are running (at most {MAX_ACTIVE_REVIEWS}). Try again in a few minutes."
        )


@dataclass
class _FetchBudget:
    remaining: int


def check_pull_request_size(details: dict) -> None:
    if details["changed_files_count"] > MAX_CHANGED_FILES:
        raise PullRequestRejected(
            f"This pull request has {details['changed_files_count']} changed files. "
            f"MergeMind reviews pull requests with at most {MAX_CHANGED_FILES} changed files."
        )
    lines = details["additions"] + details["deletions"]
    if lines > MAX_CHANGED_LINES:
        raise PullRequestRejected(
            f"This pull request has {lines} changed lines. "
            f"MergeMind reviews pull requests with at most {MAX_CHANGED_LINES} changed lines."
        )


def plan_files(files: list[dict]) -> list[dict]:
    """Decide which files to review: the first MAX_REVIEWED_FILES eligible ones."""
    planned, reviewable = [], 0
    for changed_file in files:
        reason = skip_reason(changed_file)
        if reason is None and len(changed_file["path"]) > MAX_REVIEWABLE_PATH:
            reason = "unsupported"
        if reason is None:
            if reviewable >= MAX_REVIEWED_FILES:
                reason = "file_limit"
            else:
                reviewable += 1
        planned.append({
            "path": changed_file["path"][:MAX_STORED_PATH],
            "status": changed_file["status"][:20],
            "additions": changed_file["additions"],
            "deletions": changed_file["deletions"],
            "patch": changed_file["patch"],
            "language": language_for_path(changed_file["path"]),
            "review_state": "skipped" if reason else "pending",
            "skip_reason": reason,
        })
    return planned


def _combined_diff(files: list[dict]) -> str:
    """The reviewed files' diffs, stored as the review's code for History search and previews."""
    text = "".join(f"--- a/{f['path']}\n+++ b/{f['path']}\n{f['patch']}\n" for f in files)
    return text[:MAX_SUBMITTED_CHARS]


def start_pull_request_review(
    db: Session, client: GitHubClient, ref: PullRequestRef, project_id: int, source_root: str,
) -> CodeReview:
    """Check the pull request and save it with a pending review. Raises
    GitHubError or PullRequestRejected before anything is saved."""
    details = client.get_pull_request(ref)
    check_pull_request_size(details)
    files = client.list_files(ref)
    # The files must belong to the commit that will be reviewed.
    if client.get_pull_request(ref)["head_sha"] != details["head_sha"]:
        raise PullRequestConflict(
            "The pull request changed while MergeMind was reading it. Try again in a moment."
        )
    if len(files) > MAX_CHANGED_FILES:
        check_pull_request_size({**details, "changed_files_count": len(files)})
    planned = plan_files(files)
    reviewable = [f for f in planned if f["review_state"] == "pending"]
    if not reviewable:
        raise PullRequestRejected(
            "This pull request has no files MergeMind can review. It reviews Python, JavaScript, "
            "TypeScript, Java, C and C++ files, and skips removed, generated and binary files."
        )

    pull_request = PullRequest(**details, source_root=source_root)
    pull_request.files = [PullRequestFile(**f) for f in planned]
    language = Counter(f["language"] for f in reviewable).most_common(1)[0][0]
    review = CodeReview(
        project_id=project_id,
        submitted_code=_combined_diff(reviewable),
        programming_language=language,
        review_status="pending",
        pull_request=pull_request,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def _context_for(client, ref, pull_request, path, code, tree, budget):
    """Directly imported files at the head commit, fetched within the budget."""
    root = pull_request.source_root
    if root and not path.startswith(root + "/"):
        root = ""  # the import root only applies to files inside it
    candidates = [c for c in import_candidates(path, code, source_root=root) if c in tree]
    files = {}
    for candidate in candidates:
        if budget.remaining <= 0:
            break
        if tree[candidate] > MAX_FILE_CHARS:
            continue
        budget.remaining -= 1
        try:
            text = client.get_file_text(ref, candidate, pull_request.head_sha, max_chars=MAX_FILE_CHARS)
        except FileTooLarge:
            continue
        if text is not None:
            files[candidate] = text
    if not files:
        return None
    try:
        return collect_project_context(path, code, files, source_root=root)
    except (ValueError, RecursionError):
        return None


def _review_file(client, ref, pull_request, changed_file, tree, budget):
    """Returns (skip_reason, findings). skip_reason is None if the file was reviewed."""
    if tree.get(changed_file.path, 0) > MAX_FILE_CHARS:
        return "too_large", []
    try:
        # Capped while downloading: a truncated tree may not list this file's size.
        code = client.get_file_text(ref, changed_file.path, pull_request.head_sha, max_chars=MAX_FILE_CHARS)
    except FileTooLarge:
        return "too_large", []
    if code is None:
        return "binary", []
    context = _context_for(client, ref, pull_request, changed_file.path, code, tree, budget)
    lines = changed_lines(changed_file.patch)
    issues = review_code(
        code, changed_file.language, project_context=context,
        file_path=changed_file.path, changed_lines=sorted(lines),
    )
    return None, focus_findings(issues, lines, line_count=line_count(code))


def _review_files(db: Session, review_id: int, client: GitHubClient) -> None:
    review = db.get(CodeReview, review_id)
    if review is None or review.pull_request is None or review.review_status != "pending":
        return
    pull_request = review.pull_request
    ref = PullRequestRef(pull_request.owner, pull_request.repo, pull_request.number)
    tree = client.get_tree(ref, pull_request.head_sha)
    budget = _FetchBudget(MAX_CONTEXT_FETCHES)
    found = []

    pending_ids = [f.id for f in pull_request.files if f.review_state == "pending"]
    for file_id in pending_ids:
        changed_file = db.get(PullRequestFile, file_id)
        try:
            reason, issues = _review_file(client, ref, pull_request, changed_file, tree, budget)
            for issue in issues:
                evidence = {"ai": True}
                confidence = calculate_confidence(evidence)
                db.add(ReviewIssue(
                    review_id=review_id,
                    file_name=changed_file.path,
                    **issue,
                    confidence_score=confidence["confidence_score"],
                    confidence_level=confidence["confidence_level"],
                    confidence_evidence=evidence,
                ))
            changed_file.review_state = "skipped" if reason else "reviewed"
            changed_file.skip_reason = reason
            db.commit()  # one commit per file, so progress is visible while it runs
            found.extend(issues)
        except Exception:
            # One file's failure (AI, GitHub or database) doesn't stop the others.
            logger.exception("Reviewing a pull request file failed for code review id=%s", review_id)
            db.rollback()
            changed_file = db.get(PullRequestFile, file_id)
            changed_file.review_state = "failed"
            db.commit()

    review = db.get(CodeReview, review_id)
    if any(f.review_state == "reviewed" for f in review.pull_request.files):
        risk = calculate_risk(found)
        review.risk_score = risk["risk_score"]
        review.risk_level = risk["risk_level"]
        review.risk_breakdown = risk["risk_breakdown"]
        review.review_status = "completed"
    else:
        review.review_status = "failed"
    db.commit()


def _mark_failed(db: Session, review_id: int) -> None:
    review = db.get(CodeReview, review_id)
    if review is None:
        return
    review.review_status = "failed"
    for changed_file in review.pull_request.files if review.pull_request else ():
        if changed_file.review_state == "pending":
            changed_file.review_state = "failed"
    db.commit()


def run_pull_request_review(review_id: int, session_factory, client_factory) -> None:
    """Background task. Never raises, and never leaves the review pending if
    the database is reachable."""
    db = None
    try:
        db = session_factory()
        try:
            with client_factory() as client:
                _review_files(db, review_id, client)
        except Exception:
            logger.exception("Pull request review failed for code review id=%s", review_id)
            db.rollback()
            _mark_failed(db, review_id)
    except Exception:
        logger.exception("Could not record the result of code review id=%s", review_id)
    finally:
        if db is not None:
            db.close()
