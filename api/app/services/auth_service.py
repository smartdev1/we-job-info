"""Authentication service layer (no HTTP concerns)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models import User

# Rate limiting: IP -> list of attempt timestamps
_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 900  # 15 min


def check_rate_limit(ip: str) -> bool:
    """Return True if allowed, False if rate limited."""
    now = time.time()
    attempts = [t for t in _attempts[ip] if now - t < _WINDOW_SECONDS]
    _attempts[ip] = attempts
    if len(attempts) >= _MAX_ATTEMPTS:
        return False
    _attempts[ip].append(now)
    return True


def reset_rate_limit(ip: str) -> None:
    """Clear recorded attempts for an IP after a successful login."""
    _attempts.pop(ip, None)


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(tz=UTC)
    await db.commit()
    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()