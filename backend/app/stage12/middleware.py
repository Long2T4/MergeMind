"""Reject anonymous access before any route runs.

Authentication only: the verified token claims are stored on the request, and
routes resolve the user and check ownership through get_current_user. No
database work or user context lives here, so background tasks don't depend
on it.
"""
from __future__ import annotations
import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.stage12.security import verify_token

logger = logging.getLogger(__name__)

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
            request.state.stage12_claims = verify_token(bearer[7:].strip())
        except HTTPException as exc:
            return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        except RuntimeError as exc:
            # Server misconfiguration (SUPABASE_URL): fail closed, clearly.
            logger.error('Sign-in is misconfigured: %s', exc)
            return JSONResponse({'detail': "Sign-in isn't configured on this server"}, status_code=503)
        return await call_next(request)
