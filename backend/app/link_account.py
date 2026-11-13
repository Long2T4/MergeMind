"""Link an existing MergeMind user to a Supabase Auth account. Admin only.

Users created before Stage 12 (for example user 1, who owns the earlier
reviews) have no Supabase identity, so signing in with their email gets a
409 instead of their data. This links one user to one Supabase Auth user id,
chosen deliberately by an administrator. Emails are never matched
automatically: copy the Auth user id from Supabase (Authentication > Users)
after confirming the person owns the account.

Run from backend/ (uses DATABASE_URL from backend/.env). Dry run by default:

    python -m app.link_account --user-id 1 --auth-user-id <uuid>          # show what would change
    python -m app.link_account --user-id 1 --auth-user-id <uuid> --apply  # link
"""
import argparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import CodeReview, Project, User


def link_account(db: Session, user_id: int, auth_user_id: str, apply: bool = False) -> dict:
    """Describe (and, only with apply, make) the link. Raises ValueError if unsafe."""
    try:
        auth_user_id = str(UUID(auth_user_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"{auth_user_id!r} is not a valid UUID (copy it from Supabase Authentication > Users)")
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"No user with id {user_id}")
    if user.auth_user_id and user.auth_user_id != auth_user_id:
        raise ValueError(f"User {user_id} is already linked to a different Supabase account; nothing was changed")
    holder = db.query(User).filter(User.auth_user_id == auth_user_id, User.id != user_id).first()
    if holder is not None:
        raise ValueError(f"That Supabase account is already linked to user {holder.id}; nothing was changed")

    project_ids = [row.id for row in db.query(Project.id).filter(Project.user_id == user_id)]
    reviews = db.query(CodeReview).filter(CodeReview.project_id.in_(project_ids)).count() if project_ids else 0
    if user.auth_user_id == auth_user_id:
        action = "already linked"
    elif apply:
        user.auth_user_id = auth_user_id
        db.commit()
        action = "linked"
    else:
        action = "would link"
    return {"user_id": user.id, "email": user.email, "auth_user_id": auth_user_id,
            "projects": len(project_ids), "reviews": reviews, "action": action}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Link an existing user to a Supabase Auth account (admin only).")
    parser.add_argument("--user-id", type=int, required=True, help="MergeMind users.id to link")
    parser.add_argument("--auth-user-id", required=True, help="Supabase Auth user id (UUID)")
    parser.add_argument("--apply", action="store_true", help="make the link (default: dry run)")
    args = parser.parse_args(argv)

    from app.database.database import SessionLocal

    with SessionLocal() as db:
        try:
            result = link_account(db, args.user_id, args.auth_user_id, apply=args.apply)
        except ValueError as error:
            parser.error(str(error))
    label = {"would link": "Would link (dry run)", "linked": "Linked", "already linked": "Already linked"}
    print(f"{label[result['action']]}: user {result['user_id']} ({result['email']}) -> Supabase "
          f"{result['auth_user_id']}, owning {result['projects']} project(s), {result['reviews']} review(s)")


if __name__ == "__main__":
    main()
