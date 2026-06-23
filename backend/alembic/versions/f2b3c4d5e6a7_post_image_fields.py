"""post image fields

Revision ID: f2b3c4d5e6a7
Revises: e1a2b3c4d5f6
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f2b3c4d5e6a7"
down_revision: str | None = "e1a2b3c4d5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("image_url", sa.String(length=1000), nullable=True)
        )
        batch_op.add_column(
            sa.Column("image_path", sa.String(length=500), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("image_path")
        batch_op.drop_column("image_url")
