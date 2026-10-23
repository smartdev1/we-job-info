"""Persistence tests of the extracted offers.

They run against an in-memory SQLite database, never against the instance
configured in .env, which points at the production Neon instance.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ingestion.persist import ensure_source, persist_offer_detail
from app.models import Base, Offer, RawDocument
from app.sources.detail import OfferDetail


def _run(body: Callable[[AsyncSession], Awaitable]) -> object:
    """Run ``body`` against a fresh in-memory database."""

    async def _main() -> object:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                return await body(session)
        finally:
            await engine.dispose()

    return asyncio.run(_main())


def _detail(**kwargs) -> OfferDetail:
    defaults = {
        "title": "Développeur Fullstack",
        "company": "Scoop Afrique",
        "city": "Abidjan",
        "country": "Côte d'Ivoire",
        "contract_type": "CDI",
        "education_level": "Bac+5",
        "experience": "3 ans d'expérience",
        "sector": "informatique",
        "description": "Un poste de développement.",
        "missions": ["Développer"],
        "profile": ["Python"],
        "how_to_apply": "Postuler sur le site.",
        "application_url": "https://example.com/apply",
    }
    defaults.update(kwargs)
    return OfferDetail(**defaults)


def test_a_new_offer_is_written_with_every_extracted_field():
    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        result = await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(),
            origin_url="https://example.com/job/1",
            raw_html="<html>page</html>",
        )
        await db.commit()
        offer = (await db.execute(select(Offer))).scalar_one()
        return result, offer

    result, offer = _run(body)
    assert result.created is True
    assert offer.title == "Développeur Fullstack"
    assert offer.company == "Scoop Afrique"
    assert offer.city == "Abidjan"
    assert offer.country == "Côte d'Ivoire"
    assert offer.contract_type == "CDI"
    assert offer.education_level == "Bac+5"
    assert offer.experience == "3 ans d'expérience"
    assert offer.sector == "informatique"
    assert offer.description == "Un poste de développement."
    assert offer.missions == ["Développer"]
    assert offer.profile == ["Python"]
    assert offer.how_to_apply == "Postuler sur le site."
    assert offer.application_url == "https://example.com/apply"
    assert offer.origin_url == "https://example.com/job/1"
    assert offer.status == "nouvelle"
    assert offer.fingerprint
    assert offer.score is not None


def test_the_raw_page_is_stored():
    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(),
            origin_url="https://example.com/job/1",
            raw_html="<html>page</html>",
        )
        await db.commit()
        return (await db.execute(select(RawDocument))).scalars().all()

    documents = _run(body)
    assert len(documents) == 1
    assert documents[0].content == "<html>page</html>"
    assert documents[0].content_type == "text/html"


def test_the_same_url_is_updated_and_not_duplicated():
    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        first = await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(),
            origin_url="https://example.com/job/1",
            raw_html="<html>v1</html>",
        )
        second = await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(title="Développeur Fullstack Senior"),
            origin_url="https://example.com/job/1",
            raw_html="<html>v2</html>",
        )
        await db.commit()
        offers = (await db.execute(select(Offer))).scalars().all()
        return first, second, offers

    first, second, offers = _run(body)
    assert first.created is True
    assert second.created is False
    assert len(offers) == 1
    assert offers[0].title == "Développeur Fullstack Senior"


def test_a_different_url_with_the_same_fingerprint_is_flagged_not_merged():
    """Two postings that look alike are two rows.

    The spec requires the near-duplicates to be signalled in the dashboard,
    never silently merged: the second posting is a different one, with its
    own deadline and its own application link.
    """

    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        first = await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(),
            origin_url="https://example.com/job/1",
            raw_html="<html>a</html>",
        )
        second = await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(),
            origin_url="https://example.com/job/2",
            raw_html="<html>b</html>",
        )
        await db.commit()
        offers = (await db.execute(select(Offer))).scalars().all()
        return first, second, offers

    first, second, offers = _run(body)
    assert first.created is True
    assert second.created is True
    assert len(offers) == 2
    duplicate = next(o for o in offers if o.duplicate_of is not None)
    canonical = next(o for o in offers if o.id == duplicate.duplicate_of)
    assert canonical.origin_url == "https://example.com/job/1"
    assert duplicate.origin_url == "https://example.com/job/2"


def test_a_missing_value_does_not_erase_a_previously_written_one():
    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(sector="informatique"),
            origin_url="https://example.com/job/1",
            raw_html="<html>a</html>",
        )
        await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(sector=None),
            origin_url="https://example.com/job/1",
            raw_html="<html>b</html>",
        )
        await db.commit()
        return (await db.execute(select(Offer))).scalar_one()

    offer = _run(body)
    assert offer.sector == "informatique"


def test_the_score_and_the_suspicion_are_computed_on_write():
    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(contact_email=None, application_url=None),
            origin_url="https://example.com/job/1",
            raw_html="<html>a</html>",
        )
        await db.commit()
        return (await db.execute(select(Offer))).scalar_one()

    offer = _run(body)
    assert offer.score is not None
    assert 0.0 <= offer.score <= 1.0
    assert offer.suspicious is True
    assert "contact uniquement par messagerie privée" in offer.suspicion_reasons


def test_an_offer_without_a_company_is_flagged_as_suspicious():
    async def body(db: AsyncSession):
        source_id = await ensure_source(db, "jobivoire")
        await persist_offer_detail(
            db,
            source_uuid=source_id,
            detail=_detail(company=None),
            origin_url="https://example.com/job/1",
            raw_html="<html>a</html>",
        )
        await db.commit()
        return (await db.execute(select(Offer))).scalar_one()

    offer = _run(body)
    assert offer.suspicious is True
    assert "aucune entreprise identifiable" in offer.suspicion_reasons
