"""project facebook system token

Revision ID: d8f1a2b3c4e5
Revises: c522a2195f06
Create Date: 2026-06-23 14:30:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd8f1a2b3c4e5'
down_revision: str | None = 'c522a2195f06'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('facebook_system_token_encrypted', sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('facebook_system_token_encrypted')
