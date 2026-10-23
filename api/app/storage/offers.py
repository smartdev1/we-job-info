"""Idempotent persistence of collected offers into the offers table."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Offer
from app.services.dedup import fingerprint as compute_fingerprint


async def upsert_collected_offer(
    db: AsyncSession,
    *,
    source_id: str | uuid.UUID | None = None,
    origin_url: str | None = None,
    title: str | None = None,
    company: str | None = None,
    city: str | None = None,
    fingerprint: str | None = None,
    raw_text: str | None = None,
    **extra: Any,
) -> Offer:
    """Upsert a collected offer, idempotent by origin_url then fingerprint.

    New offers enter with status 'nouvelle'. On a duplicate key the existing row
    is updated with the latest metadata.
    """
    if fingerprint is None:
        fingerprint = compute_fingerprint(company, title, city)

    existing: Offer | None = None
    if origin_url:
        result = await db.execute(select(Offer).where(Offer.origin_url == origin_url))
        existing = result.scalar_one_or_none()
    if existing is None and fingerprint:
        result = await db.execute(select(Offer).where(Offer.fingerprint == fingerprint))
        existing = result.scalar_one_or_none()

    if existing is not None:
        existing.title = title if title is not None else existing.title
        existing.company = company if company is not None else existing.company
        existing.city = city if city is not None else existing.city
        existing.fingerprint = fingerprint if fingerprint is not None else existing.fingerprint
        if source_id is not None:
            existing.source_id = source_id if not isinstance(source_id, str) else uuid.UUID(source_id)
        if origin_url is not None:
            existing.origin_url = origin_url
        if raw_text is not None and getattr(existing, "description", None) is None:
            existing.description = raw_text
        for k, v in extra.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        await db.flush()
        return existing

    sid = None
    if source_id is not None:
        sid = source_id if not isinstance(source_id, str) else uuid.UUID(source_id)

    offer = Offer(
        title=title,
        company=company,
        city=city,
        origin_url=origin_url,
        source_id=sid,
        fingerprint=fingerprint,
        status="nouvelle",
        description=raw_text,
    )
    for k, v in extra.items():
        if hasattr(offer, k):
            setattr(offer, k, v)
    db.add(offer)
    await db.flush()
    return offer


def persist_collected_offer_sync(*, source_id: str, origin_url: str | None, raw_text: str | None) -> None:
    """Sync wrapper used by procrastinate workers to persist a collected offer."""
    import uuid as _uuid

    from sqlalchemy import create_engine

    from app.core.config import get_settings

    settings = get_settings()
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "sqlite+aiosqlite:///", "sqlite:///"
    )
    # Normalise SSL params: asyncpg uses ssl=, psycopg uses sslmode=.
    url = url.replace("ssl=require", "sslmode=require").replace("ssl=prefer", "sslmode=prefer")
    engine = create_engine(url)
    with engine.begin() as conn:
        # Idempotence by origin_url.
        if origin_url:
            existing = conn.execute(
                __import__("sqlalchemy").text("SELECT id FROM offers WHERE origin_url = :u"),
                {"u": origin_url},
            ).first()
            if existing:
                return
        try:
            sid = _uuid.UUID(source_id)
        except (ValueError, AttributeError):
            sid = None
        conn.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO offers (id, origin_url, source_id, status, description) "
                "VALUES (:id, :u, :s, 'nouvelle', :d)"
            ),
            {"id": str(_uuid.uuid4()), "u": origin_url, "s": str(sid) if sid else None, "d": raw_text},
        )
