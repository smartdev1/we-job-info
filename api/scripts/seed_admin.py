"""CLI seed script: create or update an admin user in the database.

Usage:
    uv run python scripts/seed_admin.py --email admin@example.com --password 'secret'

The password is hashed with argon2 via app.core.security.hash_password.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import User


async def _seed(email: str, password: str) -> None:
    async with SessionLocal() as session:
        await _upsert(session, email, password)


async def _upsert(session: AsyncSession, email: str, password: str) -> None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    password_hash = hash_password(password)
    if user is None:
        user = User(email=email, password_hash=password_hash)
        session.add(user)
        await session.commit()
        print(f"Created admin user: {email}")
    else:
        user.password_hash = password_hash
        await session.commit()
        print(f"Updated password for existing user: {email}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an admin user (argon2 password).")
    parser.add_argument("--email", required=False, help="Admin email (defaults to ADMIN_EMAIL env var)")
    parser.add_argument("--password", required=False, help="Admin password (prompted if omitted)")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = get_settings()
    email = args.email or settings.admin_email
    if not email:
        print("Error: --email or ADMIN_EMAIL env var required.", file=sys.stderr)
        return 1

    password = args.password
    if not password:
        password = getpass.getpass("Admin password: ")
    if not password:
        print("Error: password must not be empty.", file=sys.stderr)
        return 1

    asyncio.run(_seed(email, password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
