"""Persistence of the offers extracted from a detail page.

The connectors turn a job page into an :class:`~app.sources.detail.OfferDetail`.
This module writes it into the database: the raw page is kept in
``raw_documents``, the offer in ``offers``, with its fingerprint, its score and
the suspicion reasons applied.

The write is idempotent: an offer is matched on its origin URL first, then on
its fingerprint, so running the ingestion twice does not create duplicates.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Offer, RawDocument, Source
from app.services.dedup import fingerprint as compute_fingerprint
from app.services.scoring import compute_score
from app.services.suspicion import check_suspicion
from app.sources.detail import OfferDetail

# The fields written from the detail page. They mirror the columns of the
# ``offers`` table that the extraction fills.
EXTRACTED_FIELDS = (
    "title",
    "company",
    "location",
    "city",
    "country",
    "contract_type",
    "education_level",
    "experience",
    "sector",
    "description",
    "missions",
    "profile",
    "benefits",
    "how_to_apply",
    "contact_email",
    "application_url",
    "deadline",
)


@dataclass
class PersistResult:
    """Outcome of persisting one offer."""

    offer_id: uuid.UUID
    created: bool
    fingerprint: str | None
    score: float
    suspicious: bool
    suspicion_reasons: list[str]
    duplicate_of: uuid.UUID | None = None


async def ensure_source(db: AsyncSession, source_id: str) -> uuid.UUID:
    """Return the id of the source row, creating it the first time."""
    result = await db.execute(select(Source).where(Source.name == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        source = Source(
            name=source_id,
            type="html",
            config={"connector": source_id},
            active=True,
        )
        db.add(source)
        await db.flush()
    return source.id


async def ensure_raw_document(
    db: AsyncSession,
    *,
    source_uuid: uuid.UUID | None,
    url: str | None,
    content: str,
) -> RawDocument:
    """Store the raw page, reusing the row when the content was already seen."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(RawDocument).where(RawDocument.content_hash == content_hash)
    )
    document = result.scalar_one_or_none()
    if document is None:
        document = RawDocument(
            source_id=source_uuid,
            url=url,
            content_type="text/html",
            content=content,
            content_hash=content_hash,
        )
        db.add(document)
        await db.flush()
    return document


async def find_by_url(db: AsyncSession, url: str | None) -> Offer | None:
    """Return the offer already stored under the same origin URL."""
    if not url:
        return None
    result = await db.execute(select(Offer).where(Offer.origin_url == url))
    return result.scalar_one_or_none()


async def find_by_fingerprint(db: AsyncSession, fingerprint: str | None) -> Offer | None:
    """Return the offer already stored under the same fingerprint."""
    if not fingerprint:
        return None
    result = await db.execute(select(Offer).where(Offer.fingerprint == fingerprint))
    return result.scalar_one_or_none()


def _apply_detail(offer: Offer, detail: OfferDetail) -> None:
    """Copy the extracted fields onto an offer row.

    A field that the page does not expose stays ``None`` on insertion. On
    update, an existing value is never overwritten by ``None``: the page may
    simply not repeat a value it published the first time.
    """
    for name in EXTRACTED_FIELDS:
        value = getattr(detail, name)
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        setattr(offer, name, value)


async def persist_offer_detail(
    db: AsyncSession,
    *,
    source_uuid: uuid.UUID | None,
    detail: OfferDetail,
    origin_url: str | None = None,
    raw_html: str | None = None,
    extraction_model: str | None = None,
) -> PersistResult:
    """Write one extracted offer and its raw page into the database.

    The offer is created when nothing matches its origin URL, and updated
    otherwise. An offer that carries the same fingerprint as another one but
    comes from a different URL is a near-duplicate, not the same posting: it
    is created as its own row and points at the other one through
    ``duplicate_of``, so the dashboard can flag it and a human can merge it.
    Its score and its suspicion reasons are recomputed on every write so that
    a re-run refreshes them.
    """
    document_id: uuid.UUID | None = None
    if raw_html:
        document = await ensure_raw_document(
            db, source_uuid=source_uuid, url=origin_url, content=raw_html
        )
        document_id = document.id

    fingerprint = compute_fingerprint(detail.company, detail.title, detail.city)
    existing = await find_by_url(db, origin_url)

    if existing is not None:
        offer = existing
        created = False
        _apply_detail(offer, detail)
        if document_id and not offer.raw_document_id:
            offer.raw_document_id = document_id
    else:
        # A different URL with the same fingerprint is a near-duplicate: the
        # row is created and the canonical one is recorded on it.
        canonical = await find_by_fingerprint(db, fingerprint)
        offer = Offer(
            origin_url=origin_url,
            source_id=source_uuid,
            raw_document_id=document_id,
            fingerprint=fingerprint,
            extraction_model=extraction_model,
            status="nouvelle",
        )
        if canonical is not None and canonical.origin_url != origin_url:
            offer.duplicate_of = canonical.id
        _apply_detail(offer, detail)
        db.add(offer)
        await db.flush()
        created = True

    if extraction_model and not offer.extraction_model:
        offer.extraction_model = extraction_model

    # The fingerprint is computed from the fields that were just written.
    offer.fingerprint = fingerprint or offer.fingerprint

    score = compute_score(offer)
    offer.score = score
    suspicious, reasons = check_suspicion(offer)
    offer.suspicious = suspicious
    offer.suspicion_reasons = reasons

    await db.flush()
    return PersistResult(
        offer_id=offer.id,
        created=created,
        fingerprint=offer.fingerprint,
        score=score,
        suspicious=suspicious,
        suspicion_reasons=reasons,
        duplicate_of=offer.duplicate_of,
    )


def columns_preview(detail: OfferDetail) -> dict[str, Any]:
    """Return the columns an offer detail would fill, for reporting."""
    return detail.as_columns()


def persist_offer_detail_sync(
    *,
    source_id: str,
    origin_url: str | None,
    raw_html: str | None,
    detail,
    extraction_model: str | None = None,
) -> None:
    """Synchronous wrapper around :func:`persist_offer_detail` for procrastinate tasks."""
    import asyncio

    from app.core.db import SessionLocal
    from app.ingestion.persist import ensure_source

    async def _run():
        async with SessionLocal() as db:
            source_uuid = await ensure_source(db, source_id)
            await persist_offer_detail(
                db,
                source_uuid=source_uuid,
                detail=detail,
                origin_url=origin_url,
                raw_html=raw_html,
                extraction_model=extraction_model,
            )
            await db.commit()

    asyncio.run(_run())
