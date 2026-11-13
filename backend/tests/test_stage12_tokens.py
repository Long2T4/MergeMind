"""Stage 12: Supabase access-token verification with real signed JWTs.

Real RSA (RS256) and EC (ES256) keys sign real tokens; only Supabase's JWKS
endpoint is replaced by an in-memory key set, and SUPABASE_URL points at a
fake project. Exercises verify_token directly and through the middleware.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite://")

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.models.models import Project, User
from app.routes import health, projects, users
from app.stage12 import security
from app.stage12.bootstrap import install_stage12

PROJECT_URL = "https://test-project.supabase.co"
ISSUER = f"{PROJECT_URL}/auth/v1"
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EC_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEYS = {"rsa-1": RSA_KEY.public_key(), "ec-1": EC_KEY.public_key()}


class FakeJWKS:
    """Stands in for PyJWKClient: looks up the signing key by the token's kid."""
    unreachable = False

    def get_signing_key_from_jwt(self, token):
        if FakeJWKS.unreachable:
            raise jwt.PyJWKClientConnectionError("JWKS endpoint unreachable")
        kid = jwt.get_unverified_header(token).get("kid")
        if kid not in PUBLIC_KEYS:
            raise jwt.PyJWKClientError(f"Unable to find a signing key that matches: {kid}")
        return SimpleNamespace(key=PUBLIC_KEYS[kid])


@pytest.fixture(autouse=True)
def supabase(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", PROJECT_URL)
    monkeypatch.setattr(security, "_jwks_client", lambda uri: FakeJWKS())
    FakeJWKS.unreachable = False


def claims(**overrides):
    now = int(time.time())
    body = {"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISSUER, "role": "authenticated",
            "email": "dev@example.com", "iat": now, "exp": now + 300}
    body.update(overrides)
    return {key: value for key, value in body.items() if value is not None}


def token(body=None, key=RSA_KEY, algorithm="RS256", kid="rsa-1"):
    return jwt.encode(body if body is not None else claims(), key, algorithm=algorithm, headers={"kid": kid})


def rejected(raw_token):
    with pytest.raises(HTTPException) as caught:
        security.verify_token(raw_token)
    assert caught.value.status_code == 401
    assert caught.value.detail == "Invalid or expired session"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


# --- verify_token: what is accepted --------------------------------------------

def test_valid_rs256_and_es256_tokens_are_accepted():
    body = claims()
    assert security.verify_token(token(body))["sub"] == body["sub"]
    assert security.verify_token(token(body, key=EC_KEY, algorithm="ES256", kid="ec-1"))["sub"] == body["sub"]


def test_a_trailing_slash_in_supabase_url_still_matches_the_issuer(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", PROJECT_URL + "/")
    assert security.verify_token(token())["iss"] == ISSUER


# --- verify_token: signatures and algorithms -------------------------------------

def test_a_signature_from_another_key_is_rejected():
    rejected(token(key=OTHER_RSA_KEY))  # same kid, wrong private key


def test_a_tampered_payload_is_rejected():
    # Swap in another user's id; everything else is valid, so only the signature catches it.
    header, _, signature = token().split(".")
    forged_payload = _b64(json.dumps(claims(sub=str(uuid.uuid4()))).encode())
    rejected(".".join([header, forged_payload, signature]))


def test_an_unknown_key_id_is_rejected():
    rejected(token(kid="not-a-supabase-key"))


def test_hs256_tokens_are_rejected():
    rejected(token(key="legacy-jwt-secret-for-tests-0123456789abcdef", algorithm="HS256"))


def test_algorithm_confusion_with_the_public_key_is_rejected():
    # HS256 "signed" with the RSA public key as the HMAC secret.
    public_pem = RSA_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    header = {"kid": "rsa-1", "alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims()).encode())}"
    signature = hmac.new(public_pem, signing_input.encode(), hashlib.sha256).digest()
    rejected(f"{signing_input}.{_b64(signature)}")


def test_unsigned_alg_none_tokens_are_rejected():
    rejected(jwt.encode(claims(), None, algorithm="none", headers={"kid": "rsa-1"}))


@pytest.mark.parametrize("raw", ["not-a-jwt", "a.b.c", ""])
def test_garbage_is_rejected(raw):
    rejected(raw)


# --- verify_token: claims ---------------------------------------------------------

def test_expired_tokens_are_rejected_beyond_the_clock_leeway():
    now = int(time.time())
    assert security.verify_token(token(claims(iat=now - 600, exp=now - 5)))  # within the 15 s leeway
    rejected(token(claims(iat=now - 600, exp=now - 60)))


@pytest.mark.parametrize("audience", ["anon", "service_role", "other-app", None])
def test_wrong_or_missing_audience_is_rejected(audience):
    rejected(token(claims(aud=audience)))


@pytest.mark.parametrize("issuer", ["https://evil.example/auth/v1", "https://other-project.supabase.co/auth/v1", None])
def test_wrong_or_missing_issuer_is_rejected(issuer):
    rejected(token(claims(iss=issuer)))


@pytest.mark.parametrize("missing", ["exp", "iat", "sub"])
def test_required_claims_must_be_present(missing):
    rejected(token(claims(**{missing: None})))


@pytest.mark.parametrize("subject", ["user-1", "1234", "' OR 1=1 --"])
def test_subject_must_be_a_uuid(subject):
    rejected(token(claims(sub=subject)))


@pytest.mark.parametrize("role", ["service_role", "anon", None])
def test_only_authenticated_user_tokens_are_accepted(role):
    rejected(token(claims(role=role)))


def test_an_unreachable_key_set_is_a_401_not_a_crash():
    FakeJWKS.unreachable = True
    rejected(token())


# --- Through the middleware and routes ----------------------------------------------

@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = FastAPI()
    install_stage12(app)
    for module in (health, projects, users):
        app.include_router(module.router)

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(client=client, factory=factory)
    engine.dispose()


def bearer(raw_token):
    return {"Authorization": f"Bearer {raw_token}"}


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer   ", "Basic dXNlcjpwYXNz", "bearer x", "Token abc"])
def test_requests_without_a_bearer_token_get_401(api, header):
    headers = {} if header is None else {"Authorization": header}
    response = api.client.get("/account/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_an_invalid_token_gets_401_and_reaches_no_route(api):
    response = api.client.get("/account/me", headers=bearer(token(key=OTHER_RSA_KEY)))
    assert response.status_code == 401
    with api.factory() as db:
        assert db.query(User).count() == 0


def test_first_sign_in_creates_one_linked_user_and_later_ones_reuse_it(api):
    body = claims(email="new@example.com", user_metadata={"full_name": "New Developer"})
    first = api.client.get("/account/me", headers=bearer(token(body)))
    second = api.client.get("/account/me", headers=bearer(token(body)))
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["name"] == "New Developer"
    with api.factory() as db:
        saved = db.query(User).all()
        assert len(saved) == 1 and saved[0].auth_user_id == body["sub"]


def test_an_existing_unlinked_email_cannot_be_taken_over(api):
    with api.factory() as db:
        legacy = User(name="Legacy", email="legacy@example.com")
        db.add(legacy)
        db.flush()
        db.add(Project(user_id=legacy.id, name="Legacy project"))
        db.commit()
    response = api.client.get("/projects/", headers=bearer(token(claims(email="legacy@example.com"))))
    assert response.status_code == 409
    assert "administrator linking" in response.json()["detail"]
    with api.factory() as db:
        assert db.query(User).filter(User.email == "legacy@example.com").one().auth_user_id is None


def test_a_token_without_an_email_gets_403(api):
    response = api.client.get("/account/me", headers=bearer(token(claims(email=None))))
    assert response.status_code == 403


@pytest.mark.parametrize("method", ["get", "post"])
def test_the_old_users_endpoints_are_blocked_even_when_signed_in(api, method):
    extra = {"json": {"name": "x", "email": "x@example.com"}} if method == "post" else {}
    assert getattr(api.client, method)("/users/", headers=bearer(token()), **extra).status_code == 403


def test_health_needs_no_token(api):
    assert api.client.get("/health").status_code == 200


# --- Server misconfiguration (recorded; startup validation is Step 6) -------------------

@pytest.mark.parametrize("value", [None, "", "http://test-project.supabase.co", "https://user:pass@test-project.supabase.co"])
def test_an_invalid_supabase_url_never_lets_a_request_through(api, monkeypatch, value):
    if value is None:
        monkeypatch.delenv("SUPABASE_URL", raising=False)
    else:
        monkeypatch.setenv("SUPABASE_URL", value)
    response = api.client.get("/account/me", headers=bearer(token()))
    assert response.status_code != 200
    with api.factory() as db:
        assert db.query(User).count() == 0
