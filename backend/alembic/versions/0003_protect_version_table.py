"""Protect Alembic's version table from Supabase's Data API roles.

Supabase grants its "anon" and "authenticated" roles full access to every new
table in the public schema. MergeMind's own tables have Row Level Security
enabled with no policies, so those roles can't use them; this gives
alembic_version the same protection:
- enables Row Level Security (not FORCE, so the table owner that runs
  migrations is unaffected and Alembic can still read and update it);
- revokes all privileges on it from "anon" and "authenticated" when those
  roles exist.

PostgreSQL only; does nothing on SQLite.

Revision ID: 0003_protect_version_table
Revises: 0002_review_indexes
Create Date: 2026-11-05
"""
from alembic import op

revision = "0003_protect_version_table"
down_revision = "0002_review_indexes"
branch_labels = None
depends_on = None

API_ROLES = ("anon", "authenticated")


def _version_table() -> str:
    return op.get_context().version_table


def _revoke_if_role_exists(role: str, table: str) -> None:
    op.execute(
        f"DO $$ BEGIN "
        f"IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
        f'REVOKE ALL ON TABLE "{table}" FROM "{role}"; '
        f"END IF; END $$"
    )


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    table = _version_table()
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    for role in API_ROLES:
        _revoke_if_role_exists(role, table)


def downgrade() -> None:
    # Turns Row Level Security off again. The revoked API-role privileges are
    # deliberately not granted back.
    if op.get_context().dialect.name != "postgresql":
        return
    op.execute(f'ALTER TABLE "{_version_table()}" DISABLE ROW LEVEL SECURITY')
