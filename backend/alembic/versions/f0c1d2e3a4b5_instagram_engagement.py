"""instagram comment + DM auto-reply fields

Adds per-page Instagram engagement toggles to ``facebook_pages`` and a channel
discriminator to ``messenger_events`` so the inbox poller knows whether to reply
through the Facebook or Instagram Send endpoint.

Revision ID: f0c1d2e3a4b5
Revises: e9b0c1d2f3a4
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f0c1d2e3a4b5"
down_revision: str | None = "e9b0c1d2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_reply_ig_comments",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "auto_reply_ig_messages",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    with op.batch_alter_table("messenger_events", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "channel",
                sa.String(length=16),
                nullable=False,
                server_default="messenger",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("messenger_events", schema=None) as batch_op:
        batch_op.drop_column("channel")
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.drop_column("auto_reply_ig_messages")
        batch_op.drop_column("auto_reply_ig_comments")
