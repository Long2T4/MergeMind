"""Stage 12: the real app refuses to start without a valid SUPABASE_URL."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.stage12.security import validate_auth_config


@pytest.mark.parametrize("value", [None, "", "http://project.supabase.co", "https://user:pass@project.supabase.co",
                                   "project.supabase.co", "https://"])
def test_invalid_supabase_url_is_a_clear_startup_error(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("SUPABASE_URL", raising=False)
    else:
        monkeypatch.setenv("SUPABASE_URL", value)
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        validate_auth_config()
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        with TestClient(app):
            pass


def test_a_valid_supabase_url_starts_normally(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    validate_auth_config()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


def test_the_old_open_users_endpoints_are_not_registered(monkeypatch):
    """Users come only from verified sign-ins; /users/ could list every email."""
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    assert not [route.path for route in app.routes if route.path.startswith("/users")]
    with TestClient(app) as client:
        for method in ("get", "post"):
            assert getattr(client, method)("/users/").status_code == 403
