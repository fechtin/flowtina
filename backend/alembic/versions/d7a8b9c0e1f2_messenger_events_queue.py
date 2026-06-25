"""messenger inbound event queue

Revision ID: d7a8b9c0e1f2
Revises: c6f7a8b9d0e1
Create Date: 2026-06-25 12:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d7a8b9c0e1f2"
down_revision: str | None = "c6f7a8b9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messenger_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.String(length=36), nullable=False),
        sa.Column("sender_id", sa.String(length=64), nullable=False),
        sa.Column("mid", sa.String(length=191), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mid"),
    )
    op.create_index("ix_messenger_events_page_id", "messenger_events", ["page_id"])
    op.create_index("ix_messenger_events_sender_id", "messenger_events", ["sender_id"])
    op.create_index("ix_messenger_events_status", "messenger_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_messenger_events_status", table_name="messenger_events")
    op.drop_index("ix_messenger_events_sender_id", table_name="messenger_events")
    op.drop_index("ix_messenger_events_page_id", table_name="messenger_events")
    op.drop_table("messenger_events")
