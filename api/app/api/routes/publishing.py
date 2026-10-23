"""Manual publication (export) endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import GeneratedAsset, Offer, Publication
from app.offers.state_machine import is_allowed

router = APIRouter(prefix="/offers", tags=["publishing"])


class PublishRequest(BaseModel):
    asset_id: uuid.UUID | None = None
    channel: str = "export_manuel"


class PublishResponse(BaseModel):
    publication_id: uuid.UUID
    offer_id: uuid.UUID
    status: str
    channel: str


class AssetResponse(BaseModel):
    id: uuid.UUID
    kind: str = "image"
    image_path: str | None = None
    variant: int = 0


@router.get("/{offer_id}/assets", response_model=list[AssetResponse])
async def list_assets(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[dict[str, Any]]:
    result = await db.execute(select(GeneratedAsset).where(GeneratedAsset.offer_id == offer_id))
    assets = result.scalars().all()
    return [
        {"id": a.id, "kind": "image", "image_path": a.image_path, "variant": a.variant}
        for a in assets
    ]


@router.post("/{offer_id}/publish", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish(
    offer_id: uuid.UUID,
    payload: PublishRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")

    asset = None
    if payload.asset_id is not None:
        a_result = await db.execute(
            select(GeneratedAsset).where(
                GeneratedAsset.id == payload.asset_id, GeneratedAsset.offer_id == offer_id
            )
        )
        asset = a_result.scalar_one_or_none()
        if asset is None:
            raise HTTPException(status_code=404, detail="asset not found")

    if payload.channel != "export_manuel":
        raise HTTPException(status_code=422, detail="unsupported channel")

    if offer.status != "publiee" and not is_allowed(offer.status, "publiee"):
        raise HTTPException(status_code=409, detail="invalid status transition")

    pub = Publication(
        offer_id=offer.id,
        asset_id=asset.id if asset else None,
        channel=payload.channel,
        published_at=datetime.now(tz=timezone.utc),
        status="published",
    )
    db.add(pub)
    if offer.status != "publiee":
        offer.status = "publiee"
        offer.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(pub)
    return {
        "publication_id": pub.id,
        "offer_id": offer.id,
        "status": pub.status,
        "channel": pub.channel,
    }
