"""Stage 12 security boundary: Supabase sign-in and ownership checks.

The middleware verifies the Supabase access token (asymmetric JWT) on every
request. Routes then depend on get_current_user, which maps the verified
token to a local user, and check ownership explicitly in their queries:
a user's data is everything under a project with their user_id. Background
work (Stage 11 pull request reviews) runs without any request context.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from urllib.parse import urlsplit
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.database import get_db


def _issuer() -> str:
    url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError('Set a valid https SUPABASE_URL before starting Stage 12')
    return f'{url}/auth/v1'


@lru_cache(maxsize=4)
def _jwks_client(jwks_uri: str):
    return PyJWKClient(jwks_uri, cache_keys=True, lifespan=300, timeout=5)


def verify_token(token: str) -> dict:
    """Reject expired, unsigned, wrong-audience, wrong-issuer and bad-signature tokens.

    Requires Supabase asymmetric signing (RS256 or ES256), not the legacy HS256
    signing secret. Never accept service_role tokens as interactive user sessions.
    """
    issuer = _issuer()
    try:
        jwks_uri = f'{issuer}/.well-known/jwks.json'
        key = _jwks_client(jwks_uri).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=['RS256', 'ES256'],
            audience='authenticated', issuer=issuer,
            options={'require': ['exp', 'iat', 'sub', 'aud', 'iss']},
            leeway=15,
        )
        UUID(str(claims['sub']))
        if claims.get('role') != 'authenticated':
            raise ValueError('Not an authenticated user token')
        return claims
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail='Invalid or expired session') from exc


def _profile_name(claims: dict) -> str:
    meta = claims.get('user_metadata') or {}
    name = meta.get('full_name') or meta.get('name') or claims.get('email', '').split('@')[0] or 'Developer'
    return str(name)[:255]


def resolve_user(db: Session, claims: dict):
    """Resolve only by verified auth UUID. Do NOT silently claim an existing email account."""
    from app.models.models import User
    from sqlalchemy.exc import IntegrityError

    subject = str(UUID(str(claims['sub'])))
    user = db.query(User).filter(User.auth_user_id == subject).one_or_none()
    if user:
        return user
    email = claims.get('email')
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(status_code=403, detail='A verified email is required')
    # Existing local records must be linked deliberately by an administrator;
    # matching email text on its own is not proof that the legacy data is owned.
    if db.query(User.id).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail='Existing account requires administrator linking')
    user = User(name=_profile_name(claims), email=email, auth_user_id=subject)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Handles a concurrent first-request insert without granting a foreign identity.
        recovered = db.query(User).filter(User.auth_user_id == subject).one_or_none()
        if recovered:
            return recovered
        raise HTTPException(status_code=409, detail='Account initialization conflict') from exc
    db.refresh(user)
    return user


@dataclass(frozen=True)
class CurrentUser:
    id: int
    name: str
    email: str


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    """The signed-in user, from the token the middleware verified."""
    claims = getattr(request.state, 'stage12_claims', None)
    if not claims:
        raise HTTPException(status_code=401, detail='Authentication required')
    user = resolve_user(db, claims)
    return CurrentUser(id=user.id, name=user.name, email=user.email)


def owned_project_ids(user_id: int):
    """Subquery of the user's project ids, for filtering reviews they own."""
    from app.models.models import Project
    return select(Project.id).where(Project.user_id == user_id)


def get_owned_project(db: Session, project_id: int, user_id: int):
    """The project if it belongs to the user, else None (callers answer 404)."""
    from app.models.models import Project
    return db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).one_or_none()
