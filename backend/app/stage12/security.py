"""Stage 12 security boundary. Server-side Supabase asymmetric JWT verification.

Legacy user-data routes are protected by both authentication middleware and
SQLAlchemy ORM ownership criteria. Any code that uses raw SQL must be audited
separately before public deployment.
"""
from __future__ import annotations

from contextvars import ContextVar
from functools import lru_cache
import os
from urllib.parse import urlsplit
from uuid import UUID

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session, with_loader_criteria

# No user = no ownership filter, used only inside internal auth identity resolution.
owner_context: ContextVar[int | None] = ContextVar('stage12_owner', default=None)


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


def install_ownership_filters():
    """Apply row ownership to all ORM SELECTs, including count/aggregation queries.

    This covers mapped entities with user_id, project_id or review_id foreign keys;
    the User table is special-cased. Extra Stage 13 mappings are discovered at
    query time, so no static-analysis model fields are modified.
    """
    if getattr(Session, '_stage12_filters_installed', False):
        return

    @event.listens_for(Session, 'do_orm_execute')
    def _scope_query(state):
        current = owner_context.get()
        if current is None or not state.is_select:
            return
        from app.database.database import Base
        from app.models.models import User
        from sqlalchemy import false

        # Walk SQLAlchemy foreign keys to find an ownership path. This supports
        # Stage 11 review-file / PR child tables that might reference a review
        # indirectly instead of carrying project_id on every row.
        mapped = {mapper.local_table: mapper.class_ for mapper in Base.registry.mappers}
        predicate_cache = {}

        def owner_predicate(entity, path=frozenset()):
            if entity in predicate_cache:
                return predicate_cache[entity]
            if entity in path:
                return None
            if entity is User:
                return entity.id == current
            preds = []
            for column in entity.__table__.columns:
                for fk in column.foreign_keys:
                    parent = mapped.get(fk.column.table)
                    if parent is None:
                        continue
                    parent_predicate = owner_predicate(parent, path | {entity})
                    if parent_predicate is not None:
                        preds.append(column.in_(select(fk.column).where(parent_predicate)))
            if not preds:
                # Permit common schemas where ownership columns exist but are
                # not declared as FKs; explicit names are still ownership roots.
                names = entity.__table__.columns.keys()
                if 'user_id' in names:
                    preds = [entity.user_id == current]
            if preds:
                from sqlalchemy import or_
                predicate_cache[entity] = or_(*preds)
                return predicate_cache[entity]
            return None

        stmt = state.statement
        for entity in mapped.values():
            pred = owner_predicate(entity)
            if pred is None:
                name = entity.__tablename__.lower()
                if any(word in name for word in ('review', 'finding', 'pull_request')):
                    # A newly introduced user-data table with no recognized
                    # ownership path must not be accidentally exposed.
                    pred = false()
                else:
                    continue
            stmt = stmt.options(with_loader_criteria(entity, pred, include_aliases=True))
        state.statement = stmt

    @event.listens_for(Session, 'before_flush')
    def _block_cross_user_writes(db, flush_context, instances):
        current = owner_context.get()
        if current is None:
            return
        from app.models.models import User, Project, CodeReview, ReviewIssue
        from sqlalchemy import inspect

        project_ids = select(Project.id).where(Project.user_id == current)
        review_ids = select(CodeReview.id).where(CodeReview.project_id.in_(project_ids))
        for record in list(db.new) + list(db.dirty) + list(db.deleted):
            if isinstance(record, User):
                if record.id is not None and record.id != current:
                    raise HTTPException(status_code=403, detail='Cannot modify another user')
                continue
            if isinstance(record, Project):
                if record.user_id != current:
                    raise HTTPException(status_code=403, detail='Invalid project ownership')
            elif isinstance(record, CodeReview):
                # If a newly created project has no PK yet, the application
                # must flush that project before creating a review for it.
                if record.project_id is None or db.execute(select(Project.id).where(Project.id == record.project_id, Project.user_id == current)).first() is None:
                    raise HTTPException(status_code=404, detail='Project not found')
            elif isinstance(record, ReviewIssue):
                if record.review_id is None or db.execute(select(CodeReview.id).where(CodeReview.id == record.review_id, CodeReview.id.in_(review_ids))).first() is None:
                    raise HTTPException(status_code=404, detail='Review not found')
            elif 'user_id' in record.__mapper__.columns.keys():
                if getattr(record, 'user_id') != current:
                    raise HTTPException(status_code=403, detail='Not your resource')
            elif 'project_id' in record.__mapper__.columns.keys():
                project_id = getattr(record, 'project_id')
                if project_id is None or db.execute(select(Project.id).where(Project.id == project_id, Project.user_id == current)).first() is None:
                    raise HTTPException(status_code=404, detail='Project not found')
            elif 'review_id' in record.__mapper__.columns.keys():
                review_id = getattr(record, 'review_id')
                if review_id is None or db.execute(select(CodeReview.id).where(CodeReview.id == review_id, CodeReview.id.in_(review_ids))).first() is None:
                    raise HTTPException(status_code=404, detail='Review not found')

    Session._stage12_filters_installed = True
