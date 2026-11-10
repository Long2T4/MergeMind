"""Reject anonymous access before legacy routes execute; scope ORM sessions per request."""
from __future__ import annotations
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.database.database import SessionLocal
from app.stage12.security import owner_context, resolve_user, verify_token

PUBLIC = {'/health', '/health/', '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc'}

class Stage12AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == 'OPTIONS' or request.url.path in PUBLIC:
            return await call_next(request)
        # Disable the legacy unrestricted user create/list endpoint. Identities
        # now come exclusively from a verified Supabase session.
        if request.url.path.rstrip('/') == '/users':
            return JSONResponse({'detail': 'Use /account/me'}, status_code=403)
        bearer = request.headers.get('authorization', '')
        if not bearer.startswith('Bearer ') or not bearer[7:].strip():
            return JSONResponse({'detail': 'Authentication required'}, status_code=401)
        try:
            claims = verify_token(bearer[7:].strip())
            with SessionLocal() as db:
                user = resolve_user(db, claims)
                request.state.stage12_user = {'id': user.id, 'name': user.name, 'email': user.email}
        except HTTPException as exc:
            return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        owner_token = owner_context.set(request.state.stage12_user['id'])
        try:
            return await call_next(request)
        finally:
            owner_context.reset(owner_token)
