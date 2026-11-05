"""Indexes for history filtering, newest-first sorting and issue lookups.

Skips any index that already exists (for example, one created by
SQLAlchemy's create_all on a database set up before migrations existed).

Revision ID: 0002_review_indexes
Revises: 0001_baseline
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_review_indexes"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

# Names match SQLAlchemy's index=True convention used in app/models/models.py.
INDEXES = [
    ("ix_code_reviews_project_id", "code_reviews", ["project_id"]),
    ("ix_code_reviews_created_at", "code_reviews", ["created_at"]),
    ("ix_review_issues_review_id", "review_issues", ["review_id"]),
]


def _existing_indexes(table: str) -> set[str]:
    if op.get_context().as_sql:
        return set()  # SQL preview: nothing to inspect
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    for name, table, columns in INDEXES:
        if name not in _existing_indexes(table):
            op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _ in reversed(INDEXES):
        if name in _existing_indexes(table):
            op.drop_index(name, table_name=table)
