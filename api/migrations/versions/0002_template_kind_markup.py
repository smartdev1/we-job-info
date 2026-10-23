"""Add kind and markup columns to templates.

Revision ID: 0002_template_kind_markup
Revises: 0001_initial_schema
Create Date: 2026-10-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_template_kind_markup"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("kind", sa.String(32), nullable=True))
    op.add_column("templates", sa.Column("markup", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("templates", "markup")
    op.drop_column("templates", "kind")
