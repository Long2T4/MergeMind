"""Stage 14: deployment settings and files (nothing is deployed by these tests)."""
from pathlib import Path

import pytest
import yaml

from app import main

ROOT = Path(__file__).resolve().parents[2]


def test_cors_defaults_to_the_local_frontend(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    assert main.cors_allowed_origins() == ["http://localhost:5173"]


def test_cors_takes_the_deployed_frontend_origins(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " https://mergemind.vercel.app/ , http://localhost:5173")
    assert main.cors_allowed_origins() == ["https://mergemind.vercel.app", "http://localhost:5173"]


def test_cors_refuses_a_wildcard(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="not \*"):
        main.cors_allowed_origins()


@pytest.mark.parametrize("value, enabled", [(None, True), ("true", True), ("false", False), ("0", False), ("OFF", False)])
def test_api_docs_can_be_turned_off(monkeypatch, value, enabled):
    if value is None:
        monkeypatch.delenv("API_DOCS_ENABLED", raising=False)
    else:
        monkeypatch.setenv("API_DOCS_ENABLED", value)
    assert main.api_docs_enabled() is enabled


def test_the_image_runs_one_worker_as_a_non_root_user_without_migrating():
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "USER mergemind" in dockerfile
    assert "--workers 1" in dockerfile
    assert "API_DOCS_ENABLED=false" in dockerfile
    assert "alembic upgrade" not in dockerfile  # migrations are applied deliberately
    ignored = (ROOT / "backend" / ".dockerignore").read_text(encoding="utf-8").split()
    assert ".env" in ignored and "venv/" in ignored


def test_the_render_blueprint_holds_no_secret_values():
    service = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))["services"][0]
    env = {item["key"]: item for item in service["envVars"]}
    for key in ("DATABASE_URL", "SUPABASE_URL", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "CORS_ALLOWED_ORIGINS"):
        assert env[key] == {"key": key, "sync": False}  # entered in Render's dashboard
    assert env["API_DOCS_ENABLED"]["value"] == "false"
    assert service["healthCheckPath"] == "/health" and service["autoDeploy"] is False
