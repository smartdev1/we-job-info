"""Unit tests for template CRUD (versioning included)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import ARRAY
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.api.deps import get_current_user
from app.core.db import get_session
from app.models import Base, Template

# SQLite n'a pas le type ARRAY ; on le compile en TEXT uniquement pour les tests locaux.
@compiles(ARRAY, "sqlite")
def _visit_array(element, compiler, **kw):  # type: ignore[no-untyped-def]
    return "TEXT"

TEST_URL = "sqlite+aiosqlite:///:memory:"

# Moteur et session partagés pour que les données persistent entre deux requêtes
# TestClient sur une base en mémoire.
_test_engine = create_async_engine(
    TEST_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)

async def _init_models() -> None:
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _override_session() -> AsyncGenerator[AsyncSession, None]:
    await _init_models()
    async with _test_session_factory() as session:
        yield session


def _make_app() -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    async def _override_user():
        from app.models import User
        import uuid
        return User(id=uuid.uuid4(), email="test@test.com", password_hash="x")

    app.dependency_overrides[get_current_user] = _override_user
    return app


def test_template_crud_with_versioning() -> None:
    app = _make_app()
    client = TestClient(app)

    # List empty
    res = client.get("/api/v1/templates")
    assert res.status_code == 200
    assert res.json()["items"] == []

    # Create
    res = client.post(
        "/api/v1/templates",
        json={
            "name": "Offre emploi",
            "kind": "emploi",
            "markup": "{{ title }}",
            "html": "<div>{{ title }}</div>",
            "css": ".c{}",
            "format": "jinja2",
            "active": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    template_id = body["id"]
    assert body["version"] == 1
    assert body["kind"] == "emploi"
    assert body["markup"] == "{{ title }}"

    # Get
    res = client.get(f"/api/v1/templates/{template_id}")
    assert res.status_code == 200
    assert res.json()["version"] == 1

    # Update increments version
    res = client.patch(f"/api/v1/templates/{template_id}", json={"html": "<div class='big'>{{ title }}</div>"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["version"] == 2

    # Delete
    res = client.delete(f"/api/v1/templates/{template_id}")
    assert res.status_code == 204
    res = client.get(f"/api/v1/templates/{template_id}")
    assert res.status_code == 404

    # Model HTML/CSS compatibility fields still present
    res = client.post("/api/v1/templates", json={"name": "X", "html": "<h1></h1>"})
    assert res.status_code == 201
    assert res.json()["version"] == 1
    assert res.json()["format"] == "jinja2"


def test_generated_asset_template_version_defaults_to_zero():
    """GeneratedAsset.template_version vaut 0 par defaut (legacy/inconnu)."""
    import asyncio

    from app.models import GeneratedAsset, Offer

    async def _run() -> None:
        await _init_models()
        async with _test_session_factory() as session:
            offer = Offer(title="Test offre", company="ACME", status="nouvelle")
            session.add(offer)
            await session.flush()
            asset = GeneratedAsset(offer_id=offer.id)
            session.add(asset)
            await session.flush()
            await session.refresh(asset)
            assert asset.template_version == 0

    asyncio.run(_run())


def test_seed_templates_is_idempotent():
    """Le seed ne cree pas de doublon en cas de reexécution."""
    import asyncio
    import os
    import sys
    import tempfile
    from pathlib import Path

    import app.core.config as config_mod
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models import Base, Template

    # scripts/ n'est pas un package ; on charge seed_templates par son chemin.
    scripts_dir = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import seed_templates as seed_mod  # noqa: E402

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite+aiosqlite:///{tmp.name}"

    original_get_settings = config_mod.get_settings

    async def _run() -> int:
        config_mod.get_settings.cache_clear()
        fake_settings = type("Settings", (), {"database_url": db_url})()
        config_mod.get_settings = lambda: fake_settings  # type: ignore[assignment]
        seed_mod.get_settings = lambda: fake_settings  # type: ignore[assignment]

        # Creer les tables sur le fichier avant le seed (le seed ne fait que INSERT).
        setup_engine = create_async_engine(db_url)
        async with setup_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await setup_engine.dispose()

        await seed_mod.main()
        await seed_mod.main()

        # Compter les templates avec un moteur partage (StaticPool sur fichier).
        count_engine = create_async_engine(db_url, poolclass=StaticPool)
        session_factory = async_sessionmaker(count_engine, expire_on_commit=False)
        async with session_factory() as session:
            result = await session.execute(select(Template))
            count = len(result.scalars().all())
        await count_engine.dispose()
        return count

    try:
        assert asyncio.run(_run()) == 2
    finally:
        config_mod.get_settings = original_get_settings  # type: ignore[assignment]
        os.unlink(tmp.name)


def test_template_unknown_404() -> None:
    app = _make_app()
    client = TestClient(app)
    res = client.patch("/api/v1/templates/00000000-0000-0000-0000-000000000001", json={"name": "X"})
    assert res.status_code == 404
    res = client.delete("/api/v1/templates/00000000-0000-0000-0000-000000000002")
    assert res.status_code == 404
