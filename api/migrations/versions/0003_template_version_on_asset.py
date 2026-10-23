"""Add template_version column to generated_assets.

Revision ID: 0003_template_version_on_asset
Revises: 0002_template_kind_markup
Create Date: 2026-10-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_template_version_on_asset"
down_revision = "0002_template_kind_markup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generated_assets",
        sa.Column("template_version", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("generated_assets", "template_version")
