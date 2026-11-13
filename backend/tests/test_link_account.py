"""Stage 12: the admin command that links an existing local user to a Supabase
Auth user. Dry run by default; links only by explicit ids, never by email."""
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import link_account
from app.database.database import Base
from app.models.models import CodeReview, Project, User

AUTH_ID = "11111111-2222-4333-8444-555555555555"


@pytest.fixture
def factory(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    make = sessionmaker(bind=engine)
    with make() as db:
        legacy = User(name="Legacy", email="legacy@example.com")
        other = User(name="Other", email="other@example.com", auth_user_id=str(uuid.uuid4()))
        db.add_all([legacy, other])
        db.flush()
        project = Project(user_id=legacy.id, name="Legacy project")
        db.add(project)
        db.flush()
        db.add_all(CodeReview(project_id=project.id, submitted_code="x", programming_language="python",
                              review_status="completed") for _ in range(3))
        db.commit()
    monkeypatch.setattr("app.database.database.SessionLocal", make)
    yield make
    engine.dispose()


def linked_auth_id(factory, user_id=1):
    with factory() as db:
        return db.get(User, user_id).auth_user_id


def test_dry_run_reports_what_would_change_and_changes_nothing(factory):
    with factory() as db:
        result = link_account.link_account(db, 1, AUTH_ID)
    assert result == {"user_id": 1, "email": "legacy@example.com", "auth_user_id": AUTH_ID,
                      "projects": 1, "reviews": 3, "action": "would link"}
    assert linked_auth_id(factory) is None


def test_apply_links_the_user(factory):
    with factory() as db:
        assert link_account.link_account(db, 1, AUTH_ID, apply=True)["action"] == "linked"
    assert linked_auth_id(factory) == AUTH_ID


def test_linking_again_to_the_same_id_changes_nothing(factory):
    with factory() as db:
        link_account.link_account(db, 1, AUTH_ID, apply=True)
        assert link_account.link_account(db, 1, AUTH_ID, apply=True)["action"] == "already linked"


@pytest.mark.parametrize("user_id, auth_user_id, message", [
    (99, AUTH_ID, "No user with id 99"),
    (1, "not-a-uuid", "not a valid UUID"),
    (2, AUTH_ID, "already linked to a different"),
])
def test_unsafe_links_are_refused(factory, user_id, auth_user_id, message):
    with factory() as db:
        with pytest.raises(ValueError, match=message):
            link_account.link_account(db, user_id, auth_user_id, apply=True)
    assert linked_auth_id(factory) is None


def test_an_auth_id_already_used_by_another_user_is_refused(factory):
    taken = linked_auth_id(factory, user_id=2)
    with factory() as db:
        with pytest.raises(ValueError, match="already linked to user 2"):
            link_account.link_account(db, 1, taken, apply=True)
    assert linked_auth_id(factory) is None


def test_cli_is_a_dry_run_unless_apply_is_given(factory, capsys):
    link_account.main(["--user-id", "1", "--auth-user-id", AUTH_ID])
    assert "Would link (dry run)" in capsys.readouterr().out
    assert linked_auth_id(factory) is None

    link_account.main(["--user-id", "1", "--auth-user-id", AUTH_ID, "--apply"])
    output = capsys.readouterr().out
    assert "Linked" in output and "legacy@example.com" in output and "1 project(s), 3 review(s)" in output
    assert linked_auth_id(factory) == AUTH_ID


def test_cli_never_links_by_email(factory):
    with pytest.raises(SystemExit):
        link_account.main(["--email", "legacy@example.com", "--apply"])
    assert linked_auth_id(factory) is None


def test_cli_reports_refusals_without_a_traceback(factory, capsys):
    with pytest.raises(SystemExit) as caught:
        link_account.main(["--user-id", "99", "--auth-user-id", AUTH_ID, "--apply"])
    assert caught.value.code == 2
    assert "No user with id 99" in capsys.readouterr().err
