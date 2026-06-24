"""facebook comment engagement

Revision ID: f3c4d5e6a7b8
Revises: a3c4d5e6f7b8
Create Date: 2026-06-24 10:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3c4d5e6a7b8"
down_revision: str | None = "a3c4d5e6f7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_like_comments",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "auto_reply_comments",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("reply_persona", sa.Text(), nullable=True))

    op.create_table(
        "facebook_comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("page_id", sa.String(length=36), nullable=False),
        sa.Column("facebook_post_id", sa.String(length=120), nullable=False),
        sa.Column("comment_id", sa.String(length=120), nullable=False),
        sa.Column("commenter_name", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("liked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("replied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="processed"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_facebook_comments_page_id", "facebook_comments", ["page_id"])
    op.create_index(
        "ix_facebook_comments_comment_id", "facebook_comments", ["comment_id"]
    )
    op.create_index(
        "ix_facebook_comments_facebook_post_id",
        "facebook_comments",
        ["facebook_post_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_facebook_comments_facebook_post_id", table_name="facebook_comments")
    op.drop_index("ix_facebook_comments_comment_id", table_name="facebook_comments")
    op.drop_index("ix_facebook_comments_page_id", table_name="facebook_comments")
    op.drop_table("facebook_comments")

    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.drop_column("reply_persona")
        batch_op.drop_column("auto_reply_comments")
        batch_op.drop_column("auto_like_comments")
