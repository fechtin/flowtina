"""long-term memory: conversations, transcript and memories

Revision ID: a4d5e6f7b8c9
Revises: f3c4d5e6a7b8
Create Date: 2026-06-25 10:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a4d5e6f7b8c9"
down_revision: str | None = "f3c4d5e6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False, server_default="comment"),
        sa.Column("external_user_id", sa.String(length=120), nullable=False),
        sa.Column("user_name", sa.String(length=255), nullable=True),
        sa.Column("profile_summary", sa.Text(), nullable=True),
        sa.Column("relationship_summary", sa.Text(), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])
    op.create_index("ix_conversations_page_id", "conversations", ["page_id"])
    op.create_index(
        "ix_conversations_external_user_id", "conversations", ["external_user_id"]
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id",
        "conversation_messages",
        ["conversation_id"],
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False, server_default="semantic"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_decay_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memories_conversation_id", "memories", ["conversation_id"])
    op.create_index("ix_memories_archived", "memories", ["archived"])


def downgrade() -> None:
    op.drop_index("ix_memories_archived", table_name="memories")
    op.drop_index("ix_memories_conversation_id", table_name="memories")
    op.drop_table("memories")

    op.drop_index(
        "ix_conversation_messages_conversation_id", table_name="conversation_messages"
    )
    op.drop_table("conversation_messages")

    op.drop_index("ix_conversations_external_user_id", table_name="conversations")
    op.drop_index("ix_conversations_page_id", table_name="conversations")
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_table("conversations")
