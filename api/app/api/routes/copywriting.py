"""Copywriting variant endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.copywriting.service import generate_variants
from app.models import GeneratedAsset, Offer, StyleGuide

router = APIRouter(prefix="/offers", tags=["copywriting"])


class VariantOut(BaseModel):
    id: uuid.UUID
    variant: int
    text: str | None
    style_guide_id: uuid.UUID | None


class GenerateRequest(BaseModel):
    style_guide_id: uuid.UUID | None = None
    count: int = Field(default=3, ge=2, le=3)


class VariantPatchRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/{offer_id}/copywriting", status_code=status.HTTP_201_CREATED)
async def generate(
    offer_id: uuid.UUID,
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(select(Offer).where(Offer.id == offer_id))
    offer = result.scalar_one_or_none()
    if offer is None:
        raise HTTPException(status_code=404, detail="offer not found")

    style_content = None
    style_guide_id = payload.style_guide_id
    if style_guide_id is None:
        sg_result = await db.execute(
            select(StyleGuide).where(StyleGuide.active.is_(True)).order_by(StyleGuide.created_at).limit(1)
        )
        sg = sg_result.scalar_one_or_none()
        if sg is not None:
            style_guide_id = sg.id
            style_content = sg.content
    else:
        sg_result = await db.execute(select(StyleGuide).where(StyleGuide.id == style_guide_id))
        sg = sg_result.scalar_one_or_none()
        if sg is None:
            raise HTTPException(status_code=404, detail="style guide not found")
        style_content = sg.content

    # replace old copywriting variants only (assets without a template),
    # never touch other text assets of the same offer (BUG-016-2).
    await db.execute(
        delete(GeneratedAsset).where(
            GeneratedAsset.offer_id == offer_id,
            GeneratedAsset.template_id.is_(None),
            GeneratedAsset.text.isnot(None),
        )
    )
    await db.commit()

    variants = generate_variants(offer, style_content)
    assets: list[GeneratedAsset] = []
    for i, text in enumerate(variants[: payload.count]):
        asset = GeneratedAsset(
            offer_id=offer.id,
            style_guide_id=style_guide_id,
            text=text,
            variant=i,
        )
        db.add(asset)
        assets.append(asset)
    await db.commit()
    for a in assets:
        await db.refresh(a)
    return {
        "offer_id": offer.id,
        "variants": [
            {"id": a.id, "variant": a.variant, "text": a.text, "style_guide_id": a.style_guide_id}
            for a in assets
        ],
    }


@router.get("/{offer_id}/copywriting")
async def list_variants(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(
        select(GeneratedAsset).where(GeneratedAsset.offer_id == offer_id, GeneratedAsset.text.isnot(None))
    )
    rows = result.scalars().all()
    return {
        "items": [{"id": r.id, "variant": r.variant, "text": r.text, "style_guide_id": r.style_guide_id} for r in rows]
    }


@router.patch("/{offer_id}/copywriting/{asset_id}")
async def patch_variant(
    offer_id: uuid.UUID,
    asset_id: uuid.UUID,
    payload: VariantPatchRequest,
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(
        select(GeneratedAsset).where(GeneratedAsset.id == asset_id, GeneratedAsset.offer_id == offer_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="variant not found")
    asset.text = payload.text
    await db.commit()
    await db.refresh(asset)
    return {"id": asset.id, "variant": asset.variant, "text": asset.text}