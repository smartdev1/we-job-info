"""Initial schema (V0 tables).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "raw_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_raw_documents_url", "raw_documents", ["url"])

    op.create_table(
        "offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("company", sa.Text, nullable=True),
        sa.Column("location", sa.Text, nullable=True),
        sa.Column("city", sa.Text, nullable=True),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("contract_type", sa.Text, nullable=True),
        sa.Column("education_level", sa.Text, nullable=True),
        sa.Column("experience", sa.Text, nullable=True),
        sa.Column("sector", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("missions", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("profile", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("benefits", sa.Text, nullable=True),
        sa.Column("how_to_apply", sa.Text, nullable=True),
        sa.Column("contact_email", sa.Text, nullable=True),
        sa.Column("application_url", sa.Text, nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("origin_url", sa.Text, nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("raw_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fingerprint", sa.String(128), nullable=True),
        sa.Column("extraction_model", sa.Text, nullable=True),
        sa.Column("confidence", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="nouvelle"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("suspicious", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("suspicion_reasons", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("duplicate_of", postgresql.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("internal_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_offers_fingerprint", "offers", ["fingerprint"])
    op.create_index("idx_offers_status_created", "offers", ["status", "created_at"])
    op.create_index("idx_offers_origin_url", "offers", ["origin_url"])
    op.create_index(
        "idx_offers_title_company_trgm",
        "offers",
        ["title", "company"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops", "company": "gin_trgm_ops"},
    )

    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("html", sa.Text, nullable=False),
        sa.Column("css", sa.Text, nullable=True),
        sa.Column("fonts", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "style_guides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("examples", postgresql.JSONB, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "generated_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("style_guide_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("style_guides.id", ondelete="SET NULL"), nullable=True),
        sa.Column("image_path", sa.Text, nullable=True),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("variant", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_model", sa.Text, nullable=True),
        sa.Column("tokens_input", sa.Integer, nullable=True),
        sa.Column("tokens_output", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "publications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "jobs_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for t in ("jobs_log", "publications", "generated_assets", "style_guides", "templates", "offers", "raw_documents", "sources", "users"):
        op.drop_table(t)
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
