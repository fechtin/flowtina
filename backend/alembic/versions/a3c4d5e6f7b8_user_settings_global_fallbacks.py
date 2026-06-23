"""user settings global provider key and telegram fallbacks

Revision ID: a3c4d5e6f7b8
Revises: f2b3c4d5e6a7
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a3c4d5e6f7b8"
down_revision: str | None = "f2b3c4d5e6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("default_api_key_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("default_base_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("telegram_bot_token_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("telegram_chat_id", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                "telegram_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.drop_column("telegram_enabled")
        batch_op.drop_column("telegram_chat_id")
        batch_op.drop_column("telegram_bot_token_encrypted")
        batch_op.drop_column("default_base_url")
        batch_op.drop_column("default_api_key_encrypted")
