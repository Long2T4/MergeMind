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

from app.database.database import Base
from app.models import models  # noqa: F401 (registers the tables on Base)

BACKEND = Path(__file__).resolve().parents[1]
POSTGRES_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
TABLES = ("review_issues", "code_reviews", "projects", "users", "alembic_version")
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

    assert current_revision(engine) == "0002_review_indexes"
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
        row = connection.execute(text("SELECT explanation, status, risk_score FROM review_issues "
                                      "JOIN code_reviews ON code_reviews.id = review_issues.review_id")).one()
    assert tuple(row) == ("Existing finding", "open", None)
    assert INDEXES <= index_names(engine, "code_reviews") | index_names(engine, "review_issues")


def test_database_created_before_migrations_upgrades_cleanly(engine):
    # Databases set up with the old create_all() startup already have every table.
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, name, email, created_at) "
                                "VALUES (1, 'Kept', 'kept@example.com', '2026-10-01 10:00:00')"))

    migrate(engine)

    assert current_revision(engine) == "0002_review_indexes"
    assert schema_differences(engine) == []
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM users")).scalar_one() == "Kept"


def test_upgrading_twice_is_a_no_op(engine):
    migrate(engine)
    migrate(engine)

    assert current_revision(engine) == "0002_review_indexes"


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
