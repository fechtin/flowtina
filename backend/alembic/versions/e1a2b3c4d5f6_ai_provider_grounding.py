"""ai provider grounding flag

Revision ID: e1a2b3c4d5f6
Revises: d8f1a2b3c4e5
Create Date: 2026-06-23 15:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e1a2b3c4d5f6'
down_revision: str | None = 'd8f1a2b3c4e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('ai_providers', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'grounding_enabled',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('ai_providers', schema=None) as batch_op:
        batch_op.drop_column('grounding_enabled')
