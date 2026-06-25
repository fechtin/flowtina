"""per-page engagement cadence and action cap

Revision ID: c6f7a8b9d0e1
Revises: b5e6f7a8c9d0
Create Date: 2026-06-25 12:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c6f7a8b9d0e1"
down_revision: str | None = "b5e6f7a8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "engage_interval_minutes",
                sa.Integer(),
                nullable=False,
                server_default="30",
            )
        )
        batch_op.add_column(
            sa.Column(
                "engage_max_actions",
                sa.Integer(),
                nullable=False,
                server_default="25",
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_engaged_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.drop_column("last_engaged_at")
        batch_op.drop_column("engage_max_actions")
        batch_op.drop_column("engage_interval_minutes")
