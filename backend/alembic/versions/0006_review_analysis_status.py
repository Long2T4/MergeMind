"""Stage 13: record whether Semgrep and Bandit ran for each review.

Adds one nullable column, code_reviews.analysis_status (JSON), for example
{"semgrep": "completed", "bandit": "unavailable"}. Each value is completed,
failed, unavailable (not installed) or not_run (only Python is scanned).
Without it, "no scanner findings" and "the scanner never ran" look the same.

Existing reviews keep NULL ("not recorded"); no data is rewritten. Skips the
column if it already exists (for example, a database set up with
SQLAlchemy's create_all). No new tables, so no Row Level Security changes.

Revision ID: 0006_review_analysis_status
Revises: 0005_stage12_accounts_feedback
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_review_analysis_status"
down_revision = "0005_stage12_accounts_feedback"
branch_labels = None
depends_on = None


def _has_column() -> bool:
    # SQL preview (alembic upgrade head --sql) has no database to inspect.
    if op.get_context().as_sql:
        return False
    columns = sa.inspect(op.get_bind()).get_columns("code_reviews")
    return any(column["name"] == "analysis_status" for column in columns)


def upgrade() -> None:
    if not _has_column():
        op.add_column("code_reviews", sa.Column("analysis_status", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Removes only this column; the reviews and their findings are kept.
    with op.batch_alter_table("code_reviews") as batch:
        batch.drop_column("analysis_status")
