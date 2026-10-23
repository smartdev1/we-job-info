"""Offer ingestion endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Offer, Source
from app.offers.state_machine import allowed_targets, is_allowed
from app.models import JobLog
from app.services.offer_service import (
    create_extraction_job,
    create_extraction_job_from_url,
    create_extraction_job_from_image,
    ALLOWED_IMAGE_MIMES,
    MAX_IMAGE_BYTES,
    validate_image_magic_bytes,
)

router = APIRouter(prefix="/offers", tags=["offers"])


def _encode_cursor(row: Offer) -> str:
    """Return the pagination cursor of a row.

    The offers are listed from the most recent to the oldest, so the cursor
    carries the creation date. The identifier is added because several offers
    created in the same batch share the same date.
    """
    return f"{row.created_at.isoformat()}|{row.id}"


def _decode_cursor(cursor: str) -> tuple[datetime, UUID] | None:
    """Return the (date, id) pair a cursor stands for, or ``None``."""
    try:
        stamp, identifier = cursor.split("|", 1)
        return datetime.fromisoformat(stamp), UUID(identifier)
    except (ValueError, TypeError):
        return None



class FromTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)


class FromTextResponse(BaseModel):
    job_id: uuid.UUID


class FromUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class FromUrlResponse(BaseModel):
    job_id: uuid.UUID | None = None
    offer_id: uuid.UUID | None = None
    existing: bool = False


@router.post("/from-text", response_model=FromTextResponse, status_code=status.HTTP_202_ACCEPTED)
async def from_text(
    payload: FromTextRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    if not payload.text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="text must not be empty")
    job = await create_extraction_job(db, payload.text)
    return {"job_id": job.id}


@router.post("/from-url", response_model=FromUrlResponse, status_code=status.HTTP_202_ACCEPTED)
async def from_url(
    payload: FromUrlRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    from app.services.url_safety import UnsafeUrlError

    try:
        job, existing_offer, existing = await create_extraction_job_from_url(db, payload.url)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if existing and existing_offer is not None:
        return {"job_id": None, "offer_id": existing_offer.id, "existing": True}
    if job is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="job creation failed")
    return {"job_id": job.id, "offer_id": None, "existing": False}


class FromImageResponse(BaseModel):
    job_id: uuid.UUID


@router.post("/from-image", response_model=FromImageResponse, status_code=status.HTTP_202_ACCEPTED)
async def from_image(
    file: UploadFile = File(...),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    if file.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid mime type")
    content = await file.read()
    if not validate_image_magic_bytes(content, file.content_type):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid file content")
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid file size")
    job = await create_extraction_job_from_image(db, content, file.content_type)
    return {"job_id": job.id}


class StatusUpdateRequest(BaseModel):
    status: str


class OfferPatchRequest(BaseModel):
    title: str | None = None
    company: str | None = None
    city: str | None = None
    contract_type: str | None = None
    sector: str | None = None
    description: str | None = None
    internal_note: str | None = None
    score: float | None = None
    application_url: str | None = None

    @field_validator("application_url")
    @classmethod
    def _validate_application_url(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        from app.services.url_safety import validate_url
        try:
            return validate_url(v)
        except Exception:
            raise ValueError("application_url must be a valid http/https URL")


@router.get("")
async def list_offers(
    status_filter: str | None = Query(default=None, alias="status"),
    source: UUID | None = None,
    city: str | None = None,
    contract: str | None = Query(default=None, alias="contract"),
    sector: str | None = None,
    date: datetime | None = None,
    suspecte: bool | None = None,
    q: str | None = Query(default=None, description="Full text search on title, company, city and sector"),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    stmt = select(Offer)
    if status_filter:
        stmt = stmt.where(Offer.status == status_filter)
    if source:
        stmt = stmt.where(Offer.source_id == source)
    if city:
        stmt = stmt.where(Offer.city.ilike(city))
    if contract:
        stmt = stmt.where(Offer.contract_type == contract)
    if sector:
        stmt = stmt.where(Offer.sector == sector)
    if date:
        stmt = stmt.where(Offer.created_at >= date)
    if suspecte is not None:
        stmt = stmt.where(Offer.suspicious == suspecte)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Offer.title.ilike(pattern),
                Offer.company.ilike(pattern),
                Offer.city.ilike(pattern),
                Offer.sector.ilike(pattern),
            )
        )
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded is None:
            raise HTTPException(status_code=422, detail="invalid cursor")
        stamp, identifier = decoded
        stmt = stmt.where(
            or_(
                Offer.created_at < stamp,
                and_(Offer.created_at == stamp, Offer.id < identifier),
            )
        )
    stmt = stmt.order_by(Offer.created_at.desc(), Offer.id.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    next_cursor = _encode_cursor(rows[-1]) if rows and len(rows) == limit else None
    return {
        "items": [
            {
                "id": r.id,
                "title": r.title,
                "company": r.company,
                "city": r.city,
                "contract_type": r.contract_type,
                "sector": r.sector,
                "status": r.status,
                "score": r.score,
                "suspicious": r.suspicious,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
        "next_cursor": next_cursor,
    }


@router.get("/stats")
async def offer_stats(
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Return the counters displayed on the dashboard.

    The counts are computed in the database so the dashboard never has to
    download the whole catalogue to know how many offers it holds.

    Declared before the ``/{offer_id}`` routes on purpose: FastAPI matches
    routes in registration order, and ``/stats`` would otherwise be captured
    by ``/{offer_id}`` and rejected as an invalid UUID.
    """
    status_rows = await db.execute(
        select(Offer.status, func.count()).group_by(Offer.status)
    )
    by_status = {status: count for status, count in status_rows.all()}
    contract_rows = await db.execute(
        select(Offer.contract_type, func.count())
        .where(Offer.contract_type.isnot(None))
        .group_by(Offer.contract_type)
        .order_by(func.count().desc())
    )
    source_rows = await db.execute(
        select(Source.name, func.count())
        .select_from(Source)
        .join(Offer, Offer.source_id == Source.id)
        .group_by(Source.name)
        .order_by(func.count().desc())
    )
    suspicious = await db.execute(
        select(func.count()).select_from(Offer).where(Offer.suspicious.is_(True))
    )
    return {
        "total": sum(by_status.values()),
        "suspicious": suspicious.scalar_one(),
        "by_status": by_status,
        "by_contract": [
            {"contract": contract, "count": count} for contract, count in contract_rows.all()
        ],
        "by_source": [{"source": name, "count": count} for name, count in source_rows.all()],
    }


@router.post("/{offer_id}/status")
async def transition_status(
    offer_id: UUID,
    payload: StatusUpdateRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")
    if not is_allowed(offer.status, payload.status):
        raise HTTPException(status_code=409, detail="invalid status transition")
    offer.status = payload.status
    offer.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(offer)
    return {"id": offer.id, "status": offer.status}


@router.get("/{offer_id}")
async def get_offer(
    offer_id: UUID,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")
    dup_result = await db.execute(select(Offer).where(Offer.duplicate_of == offer_id))
    duplicates = dup_result.scalars().all()
    return {
        "id": offer.id,
        "title": offer.title,
        "company": offer.company,
        "location": offer.location,
        "city": offer.city,
        "country": offer.country,
        "contract_type": offer.contract_type,
        "education_level": offer.education_level,
        "experience": offer.experience,
        "sector": offer.sector,
        "description": offer.description,
        "missions": offer.missions,
        "profile": offer.profile,
        "benefits": offer.benefits,
        "how_to_apply": offer.how_to_apply,
        "contact_email": offer.contact_email,
        "application_url": offer.application_url,
        "deadline": offer.deadline,
        "origin_url": offer.origin_url,
        "source_id": offer.source_id,
        "raw_document_id": offer.raw_document_id,
        "fingerprint": offer.fingerprint,
        "extraction_model": offer.extraction_model,
        "confidence": offer.confidence,
        "status": offer.status,
        "score": offer.score,
        "suspicious": offer.suspicious,
        "suspicion_reasons": offer.suspicion_reasons,
        "duplicate_of": offer.duplicate_of,
        "internal_note": offer.internal_note,
        "allowed_transitions": sorted(allowed_targets(offer.status)),
        "created_at": offer.created_at,
        "updated_at": offer.updated_at,
        "duplicates": [{"id": d.id, "title": d.title, "company": d.company} for d in duplicates],
    }


@router.patch("/{offer_id}")
async def patch_offer(
    offer_id: UUID,
    payload: OfferPatchRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(offer, k, v)
    offer.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(offer)
    return {"id": offer.id, "updated_at": offer.updated_at}