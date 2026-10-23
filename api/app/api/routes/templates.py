"""Template CRUD endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Template

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    kind: str | None = None
    markup: str | None = None
    html: str = Field(..., min_length=1)
    css: str | None = None
    format: str = "jinja2"
    fonts: list[str] | None = None
    active: bool = True


class TemplateUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    markup: str | None = None
    html: str | None = None
    css: str | None = None
    fonts: list[str] | None = None
    active: bool | None = None


def _to_dict(t: Template) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "kind": t.kind,
        "markup": t.markup,
        "version": t.version,
        "format": t.format,
        "html": t.html,
        "css": t.css,
        "fonts": t.fonts,
        "active": t.active,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("")
async def list_templates(db: AsyncSession = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    result = await db.execute(select(Template).order_by(Template.created_at))
    rows = result.scalars().all()
    return {"items": [_to_dict(r) for r in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(payload: TemplateCreate, db: AsyncSession = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    t = Template(
        name=payload.name,
        kind=payload.kind,
        markup=payload.markup,
        html=payload.html,
        css=payload.css,
        format=payload.format,
        fonts=payload.fonts,
        active=payload.active,
        version=1,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _to_dict(t)


@router.get("/{template_id}")
async def get_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    result = await db.execute(select(Template).where(Template.id == template_id))
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")
    return _to_dict(t)


@router.patch("/{template_id}")
async def update_template(template_id: uuid.UUID, payload: TemplateUpdate, db: AsyncSession = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    result = await db.execute(select(Template).where(Template.id == template_id))
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    t.version = (t.version or 1) + 1
    await db.commit()
    await db.refresh(t)
    return _to_dict(t)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> None:  # noqa: B008
    result = await db.execute(select(Template).where(Template.id == template_id))
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")
    await db.delete(t)
    await db.commit()
    return None