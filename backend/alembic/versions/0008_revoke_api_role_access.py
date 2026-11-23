"""Remove Supabase's API roles' access to MergeMind's original tables (Stage 14).

Supabase's "anon" and "authenticated" roles are what its publishable key uses,
and that key ships in the frontend. Supabase's default privileges give these
roles every privilege on new tables and sequences in public. Migrations 0003
and 0004 revoked them for the tables they created. The four original tables
still had them: users, projects, code_reviews and review_issues, with their id
sequences.

Row Level Security, with no policies, blocks reading and changing rows
through the Data API. But TRUNCATE, TRIGGER and REFERENCES aren't covered by
Row Level Security, and nothing needs these grants: the backend connects as
the tables' owner.

This migration:
- revokes all privileges on those four tables and their id sequences from
  anon and authenticated, and makes sure Row Level Security is on;
- changes the default privileges of the role running migrations in public, so
  tables and sequences it creates later aren't granted to those roles either.
  Defaults that other roles set, such as Supabase's own, are unchanged.

PostgreSQL only. Skipped where the roles don't exist, as in local and CI
databases. The owner's privileges and service_role (a server-only secret
key) are unchanged. No data or columns change. The downgrade doesn't grant
the access back, like 0003.

Revision ID: 0008_revoke_api_role_access
Revises: 0007_beginner_explanations
Create Date: 2026-11-23
"""
from alembic import op

revision = "0008_revoke_api_role_access"
down_revision = "0007_beginner_explanations"
branch_labels = None
depends_on = None

TABLES = ("users", "projects", "code_reviews", "review_issues")
API_ROLES = ("anon", "authenticated")


def _if_role_exists(role: str, statement: str) -> str:
    return (f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f"{statement} END IF; END $$")


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        for role in API_ROLES:
            op.execute(_if_role_exists(role, f'REVOKE ALL ON TABLE "{table}" FROM "{role}";'))
            op.execute(
                f"DO $$ DECLARE seq text := pg_get_serial_sequence('public.{table}', 'id'); BEGIN "
                f"IF seq IS NOT NULL AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
                f"EXECUTE format('REVOKE ALL ON SEQUENCE %s FROM %I', seq, '{role}'); "
                f"END IF; END $$"
            )
    for role in API_ROLES:
        # Future tables and sequences created by this role in public.
        op.execute(_if_role_exists(
            role,
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM "{role}"; '
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM "{role}";',
        ))


def downgrade() -> None:
    # Deliberately grants nothing back: the revoked access was never needed.
    # Row Level Security stays on; earlier migrations rely on it.
    pass
