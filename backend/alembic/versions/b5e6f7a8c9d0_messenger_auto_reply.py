"""messenger auto-reply toggle on pages

Revision ID: b5e6f7a8c9d0
Revises: a4d5e6f7b8c9
Create Date: 2026-06-25 11:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b5e6f7a8c9d0"
down_revision: str | None = "a4d5e6f7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_reply_messages",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.drop_column("auto_reply_messages")
