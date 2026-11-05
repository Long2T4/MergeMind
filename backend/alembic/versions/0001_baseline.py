"""Baseline schema (Stages 1-9).

Safe for both new and existing databases:
- creates only the tables that don't exist yet;
- on existing tables, adds only the nullable or defaulted columns introduced
  after Stage 2 that may be missing (for example, columns added to Supabase
  by hand in Stage 8);
- never drops, renames or changes existing columns or data.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def _later_columns() -> dict[str, list[sa.Column]]:
    """Columns added after the original Stage 2 tables.

    Each is nullable or has a server default, so adding it to a table with
    existing rows is safe. Built fresh on each call (a Column can belong to
    only one table).
    """
    return {
        "code_reviews": [
            sa.Column("risk_score", sa.Integer(), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=True),
            sa.Column("risk_breakdown", sa.JSON(), nullable=True),
        ],
        "review_issues": [
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("why_it_matters", sa.Text(), nullable=True),
            sa.Column("suggested_fix", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.Integer(), nullable=True),
            sa.Column("confidence_level", sa.String(20), nullable=True),
            sa.Column("confidence_evidence", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        ],
    }


def _create_tables(existing: set[str]) -> None:
    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "projects" not in existing:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "code_reviews" not in existing:
        op.create_table(
            "code_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("submitted_code", sa.Text(), nullable=False),
            sa.Column("programming_language", sa.String(50), nullable=False),
            sa.Column("review_status", sa.String(50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("risk_score", sa.Integer(), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=True),
            sa.Column("risk_breakdown", sa.JSON(), nullable=True),
        )
    if "review_issues" not in existing:
        op.create_table(
            "review_issues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("review_id", sa.Integer(), sa.ForeignKey("code_reviews.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=True),
            sa.Column("line_number", sa.Integer(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("why_it_matters", sa.Text(), nullable=True),
            sa.Column("suggested_fix", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.Integer(), nullable=True),
            sa.Column("confidence_level", sa.String(20), nullable=True),
            sa.Column("confidence_evidence", sa.JSON(), nullable=True),
            # Same server default as the add-column path below, so fresh and
            # upgraded databases behave the same for raw inserts.
            sa.Column("status", sa.String(30), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def upgrade() -> None:
    if op.get_context().as_sql:
        # SQL preview (alembic upgrade head --sql): no database to inspect, so
        # show the full schema as it would be created on an empty database.
        _create_tables(set())
        return

    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    _create_tables(existing)

    # Bring tables that already existed up to date, without touching data.
    for table, columns in _later_columns().items():
        if table not in existing:
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        for column in columns:
            if column.name not in present:
                op.add_column(table, column)


def downgrade() -> None:
    # Downgrading the baseline would mean dropping every table and its data.
    raise RuntimeError("The baseline migration cannot be downgraded; it would delete all data.")
