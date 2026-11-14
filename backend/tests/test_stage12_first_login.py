"""Stage 12: a new user's first requests, sent at the same time.

The browser fires several API calls right after sign-in. Each one may try to
create the local user. All of them must succeed with the same row, and no
request may ever claim a row by matching email alone.

Runs on SQLite and, when MIGRATION_TEST_DATABASE_URL points at a disposable
local database, on PostgreSQL.
"""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.models import User
from app.stage12 import security

POSTGRES_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")


@pytest.fixture(params=["sqlite", "postgresql"])
def factory(request, tmp_path):
    if request.param == "sqlite":
        # A file database, so separate threads get separate connections.
        engine = create_engine(f"sqlite:///{tmp_path / 'first_login.db'}",
                               connect_args={"check_same_thread": False, "timeout": 30})
    else:
        if not POSTGRES_URL:
            pytest.skip("Set MIGRATION_TEST_DATABASE_URL to a disposable local PostgreSQL database")
        host = POSTGRES_URL.rsplit("@", 1)[-1].lower()
        if not host.startswith(("localhost", "127.0.0.1")) or "supabase" in POSTGRES_URL.lower():
            pytest.fail("Refusing to use MIGRATION_TEST_DATABASE_URL: it is not a local database")
        engine = create_engine(POSTGRES_URL, pool_size=20, max_overflow=40)
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    Base.metadata.drop_all(engine)
    engine.dispose()


def claims(subject, email):
    return {"sub": subject, "email": email, "role": "authenticated"}


def count_users(factory, **filters):
    with factory() as db:
        query = select(func.count()).select_from(User)
        for column, value in filters.items():
            query = query.where(getattr(User, column) == value)
        return db.scalar(query)


def test_reuses_the_row_a_simultaneous_request_created(factory, monkeypatch):
    """The exact interleaving from Step 7: another request for the same login
    commits its row between this request's UUID lookup and its email check."""
    subject = str(uuid.uuid4())
    real_lookup = security._user_for_subject
    calls = []

    def lookup_racing_another_request(db, wanted):
        calls.append(wanted)
        if len(calls) == 1:
            with factory() as other:  # the other request wins the insert
                other.add(User(name="New", email="new@example.com", auth_user_id=subject))
                other.commit()
            return None  # ...after this request's first lookup missed it
        return real_lookup(db, wanted)

    monkeypatch.setattr(security, "_user_for_subject", lookup_racing_another_request)
    with factory() as db:
        user = security.resolve_user(db, claims(subject, "new@example.com"))

    assert user.auth_user_id == subject
    assert count_users(factory, email="new@example.com") == 1


@pytest.mark.parametrize("existing_login", ["none", "another login"])
def test_email_match_alone_never_claims_an_account(factory, existing_login):
    other = str(uuid.uuid4()) if existing_login == "another login" else None
    with factory() as db:
        db.add(User(name="Legacy", email="owner@example.com", auth_user_id=other))
        db.commit()

    with factory() as db, pytest.raises(HTTPException) as error:
        security.resolve_user(db, claims(str(uuid.uuid4()), "owner@example.com"))

    assert error.value.status_code == 409
    assert error.value.detail == "Existing account requires administrator linking"
    with factory() as db:
        row = db.scalars(select(User).where(User.email == "owner@example.com")).one()
        assert row.auth_user_id == other  # unchanged: not taken over


def test_parallel_first_requests_all_resolve_to_one_row(factory):
    """Several brand-new users, each sending a burst of first requests at once."""
    users = {str(uuid.uuid4()): f"dev{index}@example.com" for index in range(6)}
    per_user = 8
    jobs = [(subject, email) for subject, email in users.items() for _ in range(per_user)]
    start = threading.Barrier(len(jobs))

    def first_request(job):
        subject, email = job
        start.wait()
        with factory() as db:
            try:
                return subject, security.resolve_user(db, claims(subject, email)).id
            except HTTPException as error:
                return subject, error

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(first_request, jobs))

    errors = [(result.status_code, result.detail) for _, result in results if isinstance(result, HTTPException)]
    assert errors == []
    for subject, email in users.items():
        ids = {user_id for owner, user_id in results if owner == subject}
        assert len(ids) == 1  # every request got the same account
        assert count_users(factory, auth_user_id=subject) == 1
        assert count_users(factory, email=email) == 1
