"""Authentication endpoints: login, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import (
    create_session_token,
    generate_csrf_token,
    verify_session_token,
)
from app.services.auth_service import (
    authenticate,
    check_rate_limit,
    get_user_by_id,
    reset_rate_limit,
)

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_SESSION = "session"
COOKIE_CSRF = "csrf_token"
SESSION_MAX_AGE = 86400


class LoginRequest(BaseModel):
    email: str
    password: str


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require_csrf(request: Request) -> None:
    header = request.headers.get("x-csrf-token")
    cookie = request.cookies.get(COOKIE_CSRF)
    if not header or not cookie or header != cookie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    ip = _client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    user = await authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    reset_rate_limit(ip)

    settings = get_settings()
    secure = settings.app_env != "development"
    session_token = create_session_token(str(user.id))
    csrf_token = generate_csrf_token()

    response.set_cookie(
        key=COOKIE_SESSION,
        value=session_token,
        httponly=True,
        samesite="none" if settings.app_env != "development" else "strict",
        secure=secure,
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    response.set_cookie(
        key=COOKIE_CSRF,
        value=csrf_token,
        httponly=False,
        samesite="none" if settings.app_env != "development" else "strict",
        secure=secure,
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return {"status": "ok", "email": user.email}


@router.post("/logout", dependencies=[Depends(require_csrf)])
async def logout(request: Request, response: Response) -> dict:
    settings = get_settings()
    secure = settings.app_env != "development"
    response.delete_cookie(
        COOKIE_SESSION, path="/", httponly=True, samesite="none" if settings.app_env != "development" else "strict", secure=secure
    )
    response.delete_cookie(
        COOKIE_CSRF, path="/", httponly=False, samesite="none" if settings.app_env != "development" else "strict", secure=secure
    )
    return {"status": "ok"}


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_session)) -> dict:  # noqa: B008
    token = request.cookies.get(COOKIE_SESSION)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = verify_session_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return {"id": str(user.id), "email": user.email}