"""Alembic migration tests, on disposable databases only.

Always runs against a temporary SQLite file. Also runs against PostgreSQL when
MIGRATION_TEST_DATABASE_URL points at a throwaway local database (CI starts
one); every table in it is dropped, so a non-local or Supabase URL is refused.
"""
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.database.database import Base
from app.models import models  # noqa: F401 (registers the tables on Base)

BACKEND = Path(__file__).resolve().parents[1]
POSTGRES_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
HEAD = "0008_revoke_api_role_access"
API_ROLES = ("anon", "authenticated")
TABLES = ("review_issues", "code_reviews", "pull_request_files", "pull_requests", "projects", "users",
          "alembic_version")
PR_TABLES = ("pull_requests", "pull_request_files")
INDEXES = {"ix_code_reviews_project_id", "ix_code_reviews_created_at", "ix_review_issues_review_id"}


def _is_disposable(url: str) -> bool:
    host = url.rsplit("@", 1)[-1].lower()
    return host.startswith(("localhost", "127.0.0.1")) and "supabase" not in url.lower()


def _drop_all(engine) -> None:
    with engine.begin() as connection:
        for table in TABLES:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


@pytest.fixture(params=["sqlite", "postgresql"])
def engine(request, tmp_path):
    if request.param == "sqlite":
        database = create_engine(f"sqlite:///{tmp_path / 'migrations.db'}")
    else:
        if not POSTGRES_URL:
            pytest.skip("Set MIGRATION_TEST_DATABASE_URL to a disposable local PostgreSQL database")
        if not _is_disposable(POSTGRES_URL):
            pytest.fail("Refusing to drop tables: MIGRATION_TEST_DATABASE_URL is not a local database")
        database = create_engine(POSTGRES_URL)
        _drop_all(database)
    yield database
    if request.param == "postgresql":
        _drop_all(database)
    database.dispose()


def migrate(engine, revision="head", downgrade=False) -> None:
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["configure_logger"] = False
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        (command.downgrade if downgrade else command.upgrade)(config, revision)


def schema_differences(engine) -> list:
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)


def current_revision(engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def index_names(engine, table: str) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes(table)}


def test_fresh_database_matches_the_models(engine):
    migrate(engine)

    assert current_revision(engine) == HEAD
    assert schema_differences(engine) == []


def test_existing_old_database_gains_new_columns_without_losing_data(engine):
    # The Stage 2 shape, before titles, confidence, risk and status existed.
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL, "
            "email VARCHAR(255) NOT NULL UNIQUE, created_at TIMESTAMP NOT NULL)",
            "CREATE TABLE projects (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), "
            "name VARCHAR(255) NOT NULL, description TEXT, created_at TIMESTAMP NOT NULL)",
            "CREATE TABLE code_reviews (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), "
            "submitted_code TEXT NOT NULL, programming_language VARCHAR(50) NOT NULL, "
            "review_status VARCHAR(50) NOT NULL, created_at TIMESTAMP NOT NULL)",
            "CREATE TABLE review_issues (id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL REFERENCES code_reviews(id), "
            "category VARCHAR(50) NOT NULL, severity VARCHAR(20) NOT NULL, file_name VARCHAR(255), "
            "line_number INTEGER, explanation TEXT NOT NULL, created_at TIMESTAMP NOT NULL)",
            "INSERT INTO users VALUES (1, 'Existing', 'existing@example.com', '2026-10-01 10:00:00')",
            "INSERT INTO projects VALUES (1, 1, 'Existing project', NULL, '2026-10-01 10:00:00')",
            "INSERT INTO code_reviews VALUES (1, 1, 'print(1)', 'python', 'completed', '2026-10-01 10:00:00')",
            "INSERT INTO review_issues VALUES (1, 1, 'logic', 'low', NULL, 1, 'Existing finding', '2026-10-01 10:00:00')",
        ):
            connection.execute(text(statement))

    migrate(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("review_issues")}
    assert {"title", "confidence_score", "confidence_evidence", "status"} <= columns
    assert {"risk_score", "risk_breakdown"} <= {c["name"] for c in inspect(engine).get_columns("code_reviews")}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT submitted_code FROM code_reviews")).scalar_one() == "print(1)"
        row = connection.execute(text("SELECT explanation, status, risk_score, beginner_explanation FROM review_issues "
                                      "JOIN code_reviews ON code_reviews.id = review_issues.review_id")).one()
    assert tuple(row) == ("Existing finding", "open", None, None)
    assert INDEXES <= index_names(engine, "code_reviews") | index_names(engine, "review_issues")


def test_database_created_before_migrations_upgrades_cleanly(engine):
    # Databases set up with the old create_all() startup already have every table.
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, name, email, created_at) "
                                "VALUES (1, 'Kept', 'kept@example.com', '2026-10-01 10:00:00')"))

    migrate(engine)

    assert current_revision(engine) == HEAD
    assert schema_differences(engine) == []
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM users")).scalar_one() == "Kept"


def test_upgrading_twice_is_a_no_op(engine):
    migrate(engine)
    migrate(engine)

    assert current_revision(engine) == HEAD


def test_index_migration_can_be_reversed_and_reapplied(engine):
    migrate(engine)

    migrate(engine, "0001_baseline", downgrade=True)
    assert not INDEXES & (index_names(engine, "code_reviews") | index_names(engine, "review_issues"))

    migrate(engine)
    assert INDEXES <= index_names(engine, "code_reviews") | index_names(engine, "review_issues")


def test_baseline_refuses_to_downgrade_and_keeps_the_tables(engine):
    migrate(engine)

    with pytest.raises(RuntimeError, match="cannot be downgraded"):
        migrate(engine, "base", downgrade=True)

    assert {"users", "projects", "code_reviews", "review_issues"} <= set(inspect(engine).get_table_names())


def _seed_stage_10_review(engine) -> None:
    with engine.begin() as connection:
        for statement in (
            "INSERT INTO users (id, name, email, created_at) VALUES (1, 'Kept', 'kept@example.com', '2026-11-05 10:00:00')",
            "INSERT INTO projects (id, user_id, name, created_at) VALUES (1, 1, 'Kept', '2026-11-05 10:00:00')",
            "INSERT INTO code_reviews (id, project_id, submitted_code, programming_language, review_status, "
            "created_at, risk_score) VALUES (1, 1, 'print(1)', 'python', 'completed', '2026-11-05 10:00:00', 70)",
            "INSERT INTO review_issues (id, review_id, category, severity, explanation, created_at) "
            "VALUES (1, 1, 'logic', 'high', 'Kept finding', '2026-11-05 10:00:00')",
        ):
            connection.execute(text(statement))


def test_stage_10_database_gains_pull_request_tables_and_keeps_manual_reviews(engine):
    migrate(engine, "0003_protect_version_table")
    _seed_stage_10_review(engine)

    migrate(engine)

    assert current_revision(engine) == HEAD
    assert schema_differences(engine) == []
    assert set(PR_TABLES) <= set(inspect(engine).get_table_names())
    assert "ix_code_reviews_pull_request_id" in index_names(engine, "code_reviews")
    assert INDEXES <= index_names(engine, "code_reviews") | index_names(engine, "review_issues")
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT submitted_code, risk_score, pull_request_id, explanation, outside_diff, status "
            "FROM code_reviews JOIN review_issues ON review_issues.review_id = code_reviews.id")).one()
    assert tuple(row) == ("print(1)", 70, None, "Kept finding", None, "open")


def test_pull_request_migration_can_be_reversed_without_losing_manual_reviews(engine):
    migrate(engine)
    _seed_stage_10_review(engine)

    migrate(engine, "0003_protect_version_table", downgrade=True)
    assert not set(PR_TABLES) & set(inspect(engine).get_table_names())
    assert "pull_request_id" not in {c["name"] for c in inspect(engine).get_columns("code_reviews")}
    assert "outside_diff" not in {c["name"] for c in inspect(engine).get_columns("review_issues")}
    assert INDEXES <= index_names(engine, "code_reviews") | index_names(engine, "review_issues")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT explanation FROM review_issues")).scalar_one() == "Kept finding"

    migrate(engine)
    assert schema_differences(engine) == []


STAGE_12_ISSUE_COLUMNS = {"status_updated_at", "status_updated_by"}


def _columns(engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def test_stage_11_database_gains_stage_12_columns_and_keeps_data(engine):
    migrate(engine, "0004_pull_requests")
    _seed_stage_10_review(engine)

    migrate(engine)

    assert current_revision(engine) == HEAD
    assert schema_differences(engine) == []
    assert "auth_user_id" in _columns(engine, "users")
    assert STAGE_12_ISSUE_COLUMNS <= _columns(engine, "review_issues")
    assert "ix_users_auth_user_id" in index_names(engine, "users")
    with engine.connect() as connection:
        user = connection.execute(text("SELECT name, auth_user_id FROM users")).one()
        issue = connection.execute(text(
            "SELECT explanation, status, status_updated_at, status_updated_by FROM review_issues")).one()
    assert tuple(user) == ("Kept", None)
    assert tuple(issue) == ("Kept finding", "open", None, None)


def test_an_invalid_existing_status_stops_the_migration_without_changing_anything(engine):
    migrate(engine, "0004_pull_requests")
    _seed_stage_10_review(engine)
    with engine.begin() as connection:
        connection.execute(text("UPDATE review_issues SET status = 'done'"))

    with pytest.raises(RuntimeError, match="1 review_issues row"):
        migrate(engine)

    assert current_revision(engine) == "0004_pull_requests"
    assert "auth_user_id" not in _columns(engine, "users")
    assert not STAGE_12_ISSUE_COLUMNS & _columns(engine, "review_issues")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT status FROM review_issues")).scalar_one() == "done"


def test_status_constraint_rejects_unknown_values(engine):
    migrate(engine)
    _seed_stage_10_review(engine)
    with engine.begin() as connection:
        for status in ("fixed", "dismissed", "false_positive", "open"):
            connection.execute(text("UPDATE review_issues SET status = :s"), {"s": status})
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE review_issues SET status = 'resolved'"))


def test_auth_user_id_is_unique_but_many_users_can_be_unlinked(engine):
    migrate(engine)
    with engine.begin() as connection:
        for user_id in (1, 2, 3):
            connection.execute(text(
                "INSERT INTO users (id, name, email, created_at) VALUES (:i, 'u', :e, '2026-11-13 10:00:00')"),
                {"i": user_id, "e": f"u{user_id}@example.com"})
        connection.execute(text("UPDATE users SET auth_user_id = :a WHERE id = 1"),
                           {"a": "11111111-1111-1111-1111-111111111111"})
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE users SET auth_user_id = :a WHERE id = 2"),
                               {"a": "11111111-1111-1111-1111-111111111111"})


def test_stage_12_migration_can_be_reversed_without_losing_data(engine):
    migrate(engine)
    _seed_stage_10_review(engine)

    migrate(engine, "0004_pull_requests", downgrade=True)
    assert "auth_user_id" not in _columns(engine, "users")
    assert not STAGE_12_ISSUE_COLUMNS & _columns(engine, "review_issues")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT explanation FROM review_issues")).scalar_one() == "Kept finding"
    with engine.begin() as connection:  # the constraint went with the downgrade
        connection.execute(text("UPDATE review_issues SET status = 'anything'"))
        connection.execute(text("UPDATE review_issues SET status = 'open'"))

    migrate(engine)
    assert schema_differences(engine) == []



def test_stage_12_database_gains_scanner_status_and_keeps_reviews(engine):
    migrate(engine, "0005_stage12_accounts_feedback")
    _seed_stage_10_review(engine)
    assert "analysis_status" not in _columns(engine, "code_reviews")

    migrate(engine)

    assert current_revision(engine) == HEAD
    assert "analysis_status" in _columns(engine, "code_reviews")
    with engine.connect() as connection:
        # Older reviews say "not recorded" (NULL); nothing else changed.
        assert connection.execute(text("SELECT analysis_status FROM code_reviews")).scalar_one() is None
        assert connection.execute(text("SELECT explanation FROM review_issues")).scalar_one() == "Kept finding"
    assert schema_differences(engine) == []


def test_scanner_status_migration_can_be_reversed_without_losing_reviews(engine):
    migrate(engine)
    _seed_stage_10_review(engine)

    migrate(engine, "0005_stage12_accounts_feedback", downgrade=True)
    assert "analysis_status" not in _columns(engine, "code_reviews")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM code_reviews")).scalar_one() == 1
        assert connection.execute(text("SELECT explanation FROM review_issues")).scalar_one() == "Kept finding"

    migrate(engine)
    assert schema_differences(engine) == []


def test_stage_13_database_gains_beginner_explanations_and_keeps_findings(engine):
    migrate(engine, "0006_review_analysis_status")
    _seed_stage_10_review(engine)
    assert "beginner_explanation" not in _columns(engine, "review_issues")

    migrate(engine)

    assert current_revision(engine) == HEAD
    with engine.connect() as connection:
        row = connection.execute(text("SELECT explanation, status, beginner_explanation FROM review_issues")).one()
    assert tuple(row) == ("Kept finding", "open", None)  # nothing generated or changed
    assert schema_differences(engine) == []


def test_beginner_explanation_migration_can_be_reversed_without_losing_findings(engine):
    migrate(engine)
    _seed_stage_10_review(engine)
    with engine.begin() as connection:
        connection.execute(text("UPDATE review_issues SET beginner_explanation = :value"),
                           {"value": '{"what_is_wrong": "x", "why_it_matters": "y", "before": "a", "after": "b"}'})

    migrate(engine, "0006_review_analysis_status", downgrade=True)
    assert "beginner_explanation" not in _columns(engine, "review_issues")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT explanation FROM review_issues")).scalar_one() == "Kept finding"

    migrate(engine)
    assert schema_differences(engine) == []

@pytest.fixture
def postgres(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL-only behaviour")
    return engine


ORIGINAL_TABLES = ("users", "projects", "code_reviews", "review_issues")


def _rls_enabled(connection, table: str) -> bool:
    return connection.execute(text("SELECT relrowsecurity FROM pg_class WHERE relname = :t"), {"t": table}).scalar()


def test_version_table_is_hidden_from_supabase_api_roles(postgres):
    # Recreate Supabase's setup: API roles that get every new public table by default.
    created = []
    with postgres.begin() as connection:
        for role in API_ROLES:
            if not connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}).scalar():
                connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
                created.append(role)
        connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated"))
        connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated"))
    try:
        migrate(postgres)

        with postgres.connect() as connection:
            assert _rls_enabled(connection, "alembic_version") is True
            for role in API_ROLES:
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert connection.execute(text(
                        f"SELECT has_table_privilege('{role}', 'public.alembic_version', '{privilege}')"
                    )).scalar() is False
                # Stage 11's tables get the same protection as the version table.
                for table in PR_TABLES:
                    assert connection.execute(text(
                        f"SELECT has_table_privilege('{role}', 'public.{table}', 'SELECT')"
                    )).scalar() is False
                    assert connection.execute(text(
                        f"SELECT has_sequence_privilege('{role}', pg_get_serial_sequence('public.{table}', 'id'), 'USAGE')"
                    )).scalar() is False
                # Stage 14 (0008): the original app tables too, and their sequences.
                for table in ORIGINAL_TABLES:
                    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "TRIGGER", "REFERENCES"):
                        assert connection.execute(text(
                            f"SELECT has_table_privilege('{role}', 'public.{table}', '{privilege}')"
                        )).scalar() is False, (role, table, privilege)
                    assert connection.execute(text(
                        f"SELECT has_sequence_privilege('{role}', pg_get_serial_sequence('public.{table}', 'id'), 'USAGE')"
                    )).scalar() is False
            for table in PR_TABLES + ORIGINAL_TABLES:
                assert _rls_enabled(connection, table) is True

        # 0008 also changed the default privileges: a table created later by
        # the same role isn't granted to the API roles.
        with postgres.begin() as connection:
            connection.execute(text("CREATE TABLE later_table (id serial PRIMARY KEY)"))
            assert connection.execute(text(
                "SELECT has_table_privilege('anon', 'public.later_table', 'SELECT')")).scalar() is False
            assert connection.execute(text(
                "SELECT has_sequence_privilege('anon', 'public.later_table_id_seq', 'USAGE')")).scalar() is False
            connection.execute(text("DROP TABLE later_table"))

        with postgres.connect() as connection:
            connection.execute(text("SET ROLE anon"))
            with pytest.raises(DBAPIError, match="permission denied"):
                connection.execute(text("SELECT version_num FROM alembic_version"))
            connection.rollback()
            connection.execute(text("SET ROLE anon"))
            with pytest.raises(DBAPIError, match="permission denied"):
                connection.execute(text("TRUNCATE review_issues"))  # not covered by Row Level Security
            connection.rollback()
    finally:
        _drop_all(postgres)
        with postgres.begin() as connection:
            connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated"))
            connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated"))
            for role in created:
                connection.execute(text(f'DROP ROLE "{role}"'))



def test_revoking_api_roles_keeps_data_and_the_owner_can_still_work(postgres):
    """0008 on a Stage 13 database set up like Supabase: data kept, and the
    backend (the tables' owner) can still read, write and use the sequences."""
    created = []
    with postgres.begin() as connection:
        for role in API_ROLES:
            if not connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}).scalar():
                connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
                created.append(role)
    try:
        migrate(postgres, "0007_beginner_explanations")
        _seed_stage_10_review(postgres)
        with postgres.begin() as connection:  # Supabase's grants on the original tables
            for table in ORIGINAL_TABLES:
                connection.execute(text(f"GRANT ALL ON TABLE {table} TO anon, authenticated"))
                connection.execute(text(f"GRANT ALL ON SEQUENCE {table}_id_seq TO anon, authenticated"))
            assert connection.execute(text("SELECT has_table_privilege('anon', 'public.users', 'TRUNCATE')")).scalar()

        migrate(postgres)

        assert current_revision(postgres) == HEAD
        with postgres.begin() as connection:
            assert connection.execute(text("SELECT explanation FROM review_issues")).scalar_one() == "Kept finding"
            assert connection.execute(text("SELECT count(*) FROM code_reviews")).scalar_one() == 1
            assert connection.execute(text("SELECT has_table_privilege('anon', 'public.users', 'TRUNCATE')")).scalar() is False
            # The owner still works normally, including new ids from the sequences.
            connection.execute(text("SELECT setval('projects_id_seq', (SELECT max(id) FROM projects))"))
            new_id = connection.execute(text(
                "INSERT INTO projects (user_id, name, created_at) VALUES (1, 'After 0008', now()) RETURNING id")).scalar_one()
            connection.execute(text("UPDATE projects SET name = 'Renamed' WHERE id = :id"), {"id": new_id})
            connection.execute(text("DELETE FROM projects WHERE id = :id"), {"id": new_id})
        # The downgrade grants nothing back.
        migrate(postgres, "0007_beginner_explanations", downgrade=True)
        with postgres.connect() as connection:
            assert connection.execute(text("SELECT has_table_privilege('anon', 'public.users', 'SELECT')")).scalar() is False
        migrate(postgres)
        assert schema_differences(postgres) == []
    finally:
        _drop_all(postgres)
        with postgres.begin() as connection:
            connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated"))
            connection.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated"))
            for role in created:
                connection.execute(text(f'DROP ROLE "{role}"'))

def test_migrations_still_run_as_a_non_superuser_table_owner(postgres):
    # Like Supabase's postgres role: owns the tables, is not a superuser, and
    # cannot bypass Row Level Security. Owners are exempt unless RLS is FORCEd.
    owner = "mergemind_migrator"
    with postgres.begin() as connection:
        if not connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": owner}).scalar():
            connection.execute(text(f"CREATE ROLE {owner} LOGIN PASSWORD 'migrator' NOSUPERUSER NOBYPASSRLS"))
        connection.execute(text(f"GRANT USAGE, CREATE ON SCHEMA public TO {owner}"))
    owner_engine = create_engine(make_url(POSTGRES_URL).set(username=owner, password="migrator"))
    try:
        migrate(owner_engine)
        assert current_revision(owner_engine) == HEAD
        with owner_engine.connect() as connection:
            assert _rls_enabled(connection, "alembic_version") is True
            assert connection.execute(text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")).scalar() is False

        # Alembic must still read and update its version table with RLS on.
        migrate(owner_engine, "0002_review_indexes", downgrade=True)
        assert current_revision(owner_engine) == "0002_review_indexes"
        migrate(owner_engine)
        assert current_revision(owner_engine) == HEAD
    finally:
        owner_engine.dispose()
        _drop_all(postgres)
        with postgres.begin() as connection:
            connection.execute(text(f"DROP OWNED BY {owner}"))
            connection.execute(text(f"DROP ROLE {owner}"))
