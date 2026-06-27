"""messenger image attachments

Stores an inbound DM's image attachment URL and lets a message carry only an
image (no text), so the reply path can acknowledge images a follower sends.

Revision ID: a1b2c3d4e5f6
Revises: f0c1d2e3a4b5
Create Date: 2026-06-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0c1d2e3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("messenger_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.Text(), nullable=True))
        # An image-only DM has no text, so text becomes nullable.
        batch_op.alter_column("text", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("messenger_events", schema=None) as batch_op:
        batch_op.alter_column("text", existing_type=sa.Text(), nullable=False)
        batch_op.drop_column("image_url")
