"""Stage 11: GitHub pull request reviews.

Adds only new tables and nullable columns, so existing reviews are unchanged:
- pull_requests: a pull request's details at review time;
- pull_request_files: its changed files and whether each was reviewed;
- code_reviews.pull_request_id (nullable, indexed): set only for PR reviews;
- review_issues.outside_diff (nullable): set only for PR findings.

Skips anything that already exists (for example, a database set up with
SQLAlchemy's create_all). On PostgreSQL, the new tables get the same
protection as alembic_version in 0003: Row Level Security on, and no access
(to the tables or their id sequences) for Supabase's "anon" and
"authenticated" roles.

Revision ID: 0004_pull_requests
Revises: 0003_protect_version_table
Create Date: 2026-11-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_pull_requests"
down_revision = "0003_protect_version_table"
branch_labels = None
depends_on = None

API_ROLES = ("anon", "authenticated")
NEW_TABLES = ("pull_requests", "pull_request_files")
REVIEW_FK = "fk_code_reviews_pull_request_id"
REVIEW_INDEX = "ix_code_reviews_pull_request_id"
FILES_INDEX = "ix_pull_request_files_pull_request_id"


def _inspector():
    # SQL preview (alembic upgrade head --sql) has no database to inspect.
    return None if op.get_context().as_sql else sa.inspect(op.get_bind())


def _tables(inspector) -> set[str]:
    return set(inspector.get_table_names()) if inspector else set()


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)} if inspector else set()


def _indexes(inspector, table: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table)} if inspector else set()


def upgrade() -> None:
    inspector = _inspector()
    tables = _tables(inspector)

    if "pull_requests" not in tables:
        op.create_table(
            "pull_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner", sa.String(100), nullable=False),
            sa.Column("repo", sa.String(100), nullable=False),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("author", sa.String(255), nullable=False),
            sa.Column("html_url", sa.String(300), nullable=False),
            sa.Column("base_sha", sa.String(64), nullable=False),
            sa.Column("head_sha", sa.String(64), nullable=False),
            sa.Column("source_root", sa.String(240), nullable=False),
            sa.Column("changed_files_count", sa.Integer(), nullable=False),
            sa.Column("additions", sa.Integer(), nullable=False),
            sa.Column("deletions", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "pull_request_files" not in tables:
        op.create_table(
            "pull_request_files",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
            sa.Column("path", sa.String(500), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("additions", sa.Integer(), nullable=False),
            sa.Column("deletions", sa.Integer(), nullable=False),
            sa.Column("patch", sa.Text(), nullable=True),
            sa.Column("language", sa.String(50), nullable=True),
            sa.Column("review_state", sa.String(20), nullable=False),
            sa.Column("skip_reason", sa.String(30), nullable=True),
        )
    if FILES_INDEX not in _indexes(inspector, "pull_request_files"):
        op.create_index(FILES_INDEX, "pull_request_files", ["pull_request_id"])

    if "pull_request_id" not in _columns(inspector, "code_reviews"):
        # Batch mode, because SQLite can only add a foreign key by copying the
        # table. PostgreSQL gets plain ALTER TABLE statements.
        with op.batch_alter_table("code_reviews") as batch:
            batch.add_column(sa.Column("pull_request_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(REVIEW_FK, "pull_requests", ["pull_request_id"], ["id"])
    if REVIEW_INDEX not in _indexes(inspector, "code_reviews"):
        op.create_index(REVIEW_INDEX, "code_reviews", ["pull_request_id"])

    if "outside_diff" not in _columns(inspector, "review_issues"):
        op.add_column("review_issues", sa.Column("outside_diff", sa.Boolean(), nullable=True))

    if op.get_context().dialect.name == "postgresql":
        for table in NEW_TABLES:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            for role in API_ROLES:
                op.execute(
                    f"DO $$ BEGIN "
                    f"IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
                    f'REVOKE ALL ON TABLE "{table}" FROM "{role}"; '
                    f"END IF; END $$"
                )
                # The id sequence too: Supabase's default privileges grant it as well.
                op.execute(
                    f"DO $$ DECLARE seq text := pg_get_serial_sequence('public.{table}', 'id'); BEGIN "
                    f"IF seq IS NOT NULL AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
                    f"EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM %I', seq, '{role}'); "
                    f"END IF; END $$"
                )


def _review_foreign_key(inspector) -> str | None:
    """The name of code_reviews' pull request foreign key, whoever created it."""
    if inspector is None:
        return REVIEW_FK
    for key in inspector.get_foreign_keys("code_reviews"):
        if key["constrained_columns"] == ["pull_request_id"]:
            return key["name"]
    return None


def downgrade() -> None:
    # Removes only what this migration added. PR reviews keep their
    # code_reviews rows, but lose their pull request details and labels.
    inspector = _inspector()
    foreign_key = _review_foreign_key(inspector)
    op.drop_column("review_issues", "outside_diff")
    op.drop_index(REVIEW_INDEX, table_name="code_reviews")
    with op.batch_alter_table("code_reviews") as batch:
        if foreign_key:
            batch.drop_constraint(foreign_key, type_="foreignkey")
        batch.drop_column("pull_request_id")
    op.drop_index(FILES_INDEX, table_name="pull_request_files")
    op.drop_table("pull_request_files")
    op.drop_table("pull_requests")
