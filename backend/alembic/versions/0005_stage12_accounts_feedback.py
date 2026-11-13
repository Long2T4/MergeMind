"""Stage 12: account identity and developer feedback on findings.

Adds only nullable columns, an index and a constraint; existing rows are kept:
- users.auth_user_id (nullable, unique index ix_users_auth_user_id): the
  Supabase Auth user id. Existing users stay unlinked until an administrator
  links them deliberately; emails are never matched automatically.
- review_issues.status_updated_at / status_updated_by (nullable, FK to
  users): who last changed a finding's status, and when.
- ck_review_issues_status: status must be open, fixed, dismissed or
  false_positive.

Before changing anything, it checks that every existing finding already has
one of those statuses. If not, it stops with an error and changes nothing:
review those rows first. It never rewrites data.

Skips anything that already exists (for example, a database set up with
SQLAlchemy's create_all). No new tables, so no Row Level Security changes.

Migration order with Stage 13: this revises 0004. Whichever stage merges
next sets its down_revision to the head on main at that time (check with
`alembic heads`, which must list exactly one head). No number is reserved.

Revision ID: 0005_stage12_accounts_feedback
Revises: 0004_pull_requests
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_stage12_accounts_feedback"
down_revision = "0004_pull_requests"
branch_labels = None
depends_on = None

STATUSES = ("open", "fixed", "dismissed", "false_positive")
STATUS_CHECK = "ck_review_issues_status"
STATUS_CHECK_SQL = "status IN ('open', 'fixed', 'dismissed', 'false_positive')"
AUTH_INDEX = "ix_users_auth_user_id"
UPDATED_BY_FK = "fk_review_issues_status_updated_by"


def _inspector():
    # SQL preview (alembic upgrade head --sql) has no database to inspect.
    return None if op.get_context().as_sql else sa.inspect(op.get_bind())


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)} if inspector else set()


def _indexes(inspector, table: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table)} if inspector else set()


def _check_constraints(inspector, table: str) -> set[str]:
    return {check["name"] for check in inspector.get_check_constraints(table)} if inspector else set()


def _stop_on_invalid_statuses() -> None:
    if op.get_context().as_sql:
        return
    invalid = op.get_bind().execute(
        sa.text("SELECT count(*) FROM review_issues WHERE status IS NULL OR status NOT IN :allowed")
        .bindparams(sa.bindparam("allowed", expanding=True)),
        {"allowed": list(STATUSES)},
    ).scalar()
    if invalid:
        raise RuntimeError(
            f"Migration 0005 stopped: {invalid} review_issues row(s) have a status other than "
            f"{', '.join(STATUSES)}. Review those rows first; nothing was changed."
        )


def upgrade() -> None:
    _stop_on_invalid_statuses()
    inspector = _inspector()

    if "auth_user_id" not in _columns(inspector, "users"):
        op.add_column("users", sa.Column("auth_user_id", sa.String(36), nullable=True))
    if AUTH_INDEX not in _indexes(inspector, "users"):
        op.create_index(AUTH_INDEX, "users", ["auth_user_id"], unique=True)

    issue_columns = _columns(inspector, "review_issues")
    add_updated_at = "status_updated_at" not in issue_columns
    add_updated_by = "status_updated_by" not in issue_columns
    add_check = STATUS_CHECK not in _check_constraints(inspector, "review_issues")
    if add_updated_at or add_updated_by or add_check:
        # Batch mode, because SQLite can only add constraints by copying the
        # table. PostgreSQL gets plain ALTER TABLE statements.
        with op.batch_alter_table("review_issues") as batch:
            if add_updated_at:
                batch.add_column(sa.Column("status_updated_at", sa.DateTime(), nullable=True))
            if add_updated_by:
                batch.add_column(sa.Column("status_updated_by", sa.Integer(), nullable=True))
                batch.create_foreign_key(UPDATED_BY_FK, "users", ["status_updated_by"], ["id"])
            if add_check:
                batch.create_check_constraint(STATUS_CHECK, STATUS_CHECK_SQL)


def _updated_by_foreign_key(inspector) -> str | None:
    """The name of the status_updated_by foreign key, whoever created it."""
    if inspector is None:
        return UPDATED_BY_FK
    for key in inspector.get_foreign_keys("review_issues"):
        if key["constrained_columns"] == ["status_updated_by"]:
            return key["name"]
    return None


def downgrade() -> None:
    # Removes only what this migration added. Status values are kept; the
    # record of who changed them, and when, is lost.
    inspector = _inspector()
    foreign_key = _updated_by_foreign_key(inspector)
    has_check = inspector is None or STATUS_CHECK in _check_constraints(inspector, "review_issues")
    with op.batch_alter_table("review_issues") as batch:
        if has_check:
            batch.drop_constraint(STATUS_CHECK, type_="check")
        if foreign_key:
            batch.drop_constraint(foreign_key, type_="foreignkey")
        batch.drop_column("status_updated_by")
        batch.drop_column("status_updated_at")
    op.drop_index(AUTH_INDEX, table_name="users")
    op.drop_column("users", "auth_user_id")
