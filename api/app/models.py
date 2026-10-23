"""SQLAlchemy ORM models for we-info-jobs (V0 schema)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(tz=__import__("datetime").timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class RawDocument(Base, TimestampMixin):
    __tablename__ = "raw_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_raw_documents_url", "url"),)


class Offer(Base, TimestampMixin):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    sector: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    missions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    profile: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    how_to_apply: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    origin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    raw_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_documents.id", ondelete="SET NULL"), nullable=True
    )
    fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extraction_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="nouvelle", nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suspicion_reasons: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="SET NULL"), nullable=True
    )
    internal_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_offers_fingerprint", "fingerprint"),
        Index("idx_offers_status_created", "status", "created_at"),
        Index("idx_offers_origin_url", "origin_url"),
        Index("idx_offers_title_company_trgm", "title", "company", postgresql_using="gin"),
    )


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    markup: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    css: Mapped[str | None] = mapped_column(Text, nullable=True)
    fonts: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StyleGuide(Base, TimestampMixin):
    __tablename__ = "style_guides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GeneratedAsset(Base, TimestampMixin):
    __tablename__ = "generated_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    style_guide_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("style_guides.id", ondelete="SET NULL"), nullable=True
    )
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Publication(Base, TimestampMixin):
    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generated_assets.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)


class JobLog(Base, TimestampMixin):
    __tablename__ = "jobs_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
