"""Manual maintenance commands. Nothing here runs automatically.

Reviews can be left "pending" if the server stops mid-review (for example,
during a deploy or crash). This finds them and, only with --apply, marks them
"failed" so they show as retryable instead of in progress.

Run from backend/ (uses DATABASE_URL from backend/.env):

    python -m app.maintenance                  # dry run: list stale reviews
    python -m app.maintenance --apply          # mark them failed
    python -m app.maintenance --older-than-minutes 60
"""
import argparse
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import CodeReview

# Longer than any real review: the AI client times out after 120 seconds and
# retries twice, so a review still pending after this long has been abandoned.
DEFAULT_STALE_MINUTES = 30


def fail_stale_pending_reviews(
    db: Session, older_than_minutes: int = DEFAULT_STALE_MINUTES, apply: bool = False,
) -> list[int]:
    """Return ids of reviews pending longer than the cutoff; mark them failed only if apply."""
    if older_than_minutes < 1:
        raise ValueError("older_than_minutes must be at least 1")
    cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
    stale = (
        db.query(CodeReview)
        .filter(CodeReview.review_status == "pending", CodeReview.created_at < cutoff)
        .order_by(CodeReview.id)
        .all()
    )
    if apply and stale:
        for review in stale:
            review.review_status = "failed"
        db.commit()
    return [review.id for review in stale]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Find reviews stuck in 'pending'.")
    parser.add_argument("--older-than-minutes", type=int, default=DEFAULT_STALE_MINUTES)
    parser.add_argument("--apply", action="store_true", help="mark the reviews failed (default: dry run)")
    args = parser.parse_args(argv)

    from app.database.database import SessionLocal

    with SessionLocal() as db:
        ids = fail_stale_pending_reviews(db, args.older_than_minutes, apply=args.apply)
    action = "Marked failed" if args.apply else "Would mark failed (dry run)"
    print(f"{action}: {len(ids)} review(s){': ' + ', '.join(map(str, ids)) if ids else ''}")


if __name__ == "__main__":
    main()
