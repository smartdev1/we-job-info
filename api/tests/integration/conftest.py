"""Shared fixtures for the integration tests.

The integration tests must never reach the database configured in .env, which
points at the production Neon instance. They all run against an in-memory
SQLite database that is recreated for each test.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.core.db import get_session
from app.models import Base

TEST_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    TEST_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _reset_schema() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def make_app():
    """Build the FastAPI app bound to the in-memory database."""
    asyncio.run(_reset_schema())

    async def _override_session() -> Iterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    application = create_app()
    application.dependency_overrides[get_session] = _override_session
    return application


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(make_app()) as test_client:
        yield test_client
