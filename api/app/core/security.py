"""Security helpers: argon2 password hashing and signed session tokens."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings

_ph = PasswordHasher()
_serializer = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(get_settings().session_secret, salt="session")
    return _serializer


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_session_token(user_id: str) -> str:
    return _get_serializer().dumps({"uid": user_id, "iat": datetime.now(UTC).timestamp()})


def verify_session_token(token: str, max_age_seconds: int = 86400) -> str | None:
    try:
        data = _get_serializer().loads(token, max_age=max_age_seconds)
        return data.get("uid")
    except (BadSignature, SignatureExpired):
        return None


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)