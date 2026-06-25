"""instagram cross-post fields

Adds the Instagram account link and per-platform publish toggles to
``facebook_pages`` so one Page can cross-post to Facebook and Instagram, and a
``platform`` discriminator to ``facebook_posts`` so each publish records one
history row per target platform.

Revision ID: e9b0c1d2f3a4
Revises: d7a8b9c0e1f2
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e9b0c1d2f3a4"
down_revision: str | None = "d7a8b9c0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("instagram_user_id", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("instagram_username", sa.String(length=255), nullable=True)
        )
        # server_default backfills existing rows; the ORM default drives inserts.
        batch_op.add_column(
            sa.Column(
                "publish_facebook",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "publish_instagram",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    with op.batch_alter_table("facebook_posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.String(length=16),
                nullable=False,
                server_default="facebook",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("facebook_posts", schema=None) as batch_op:
        batch_op.drop_column("platform")
    with op.batch_alter_table("facebook_pages", schema=None) as batch_op:
        batch_op.drop_column("publish_instagram")
        batch_op.drop_column("publish_facebook")
        batch_op.drop_column("instagram_username")
        batch_op.drop_column("instagram_user_id")
