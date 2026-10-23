"""CSRF middleware for non-GET requests."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Require x-csrf-token header matching csrf_token cookie for non-GET requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        from app.core.config import get_settings
        if get_settings().app_env != "production":
            return await call_next(request)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        # Skip CSRF for login endpoint (no session yet)
        if request.url.path == "/api/v1/auth/login":
            return await call_next(request)
        header = request.headers.get("x-csrf-token")
        cookie = request.cookies.get("csrf_token")
        if not header or not cookie or header != cookie:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)