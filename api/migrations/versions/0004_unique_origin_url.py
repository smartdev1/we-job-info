"""Add unique constraint on offers.origin_url.

Revision ID: 0004_unique_origin_url
Revises: 0003_template_version_on_asset
Create Date: 2026-10-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_unique_origin_url"
down_revision = "0003_template_version_on_asset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_offers_origin_url", "offers", ["origin_url"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_offers_origin_url", "offers", type_="unique")