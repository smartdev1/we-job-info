"""Procrastinate application factory.

Configured from the same DATABASE_URL as the rest of the app, converted to a
synchronous psycopg DSN (Procrastinate runs workers against sync drivers).
"""

from __future__ import annotations

import os

import procrastinate

from app.core.config import get_settings


def _sync_dsn() -> str:
    settings = get_settings()
    url = os.getenv("PROCRASTINATE_DATABASE_URL") or settings.database_url
    # Convert async drivers to their sync counterparts.
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("sqlite+aiosqlite:///", "sqlite:///")
    return url


app = procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=_sync_dsn()))