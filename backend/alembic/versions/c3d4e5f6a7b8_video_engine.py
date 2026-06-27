"""video generation engine tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-27 00:00:02.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_jobs",
        sa.Column("page_id", sa.String(36), nullable=False),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("voice_id", sa.String(64), nullable=True),
        sa.Column("character_image_url", sa.Text(), nullable=True),
        sa.Column("language", sa.String(8), nullable=False, default="vi"),
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        sa.Column("gpu_provider", sa.String(32), nullable=True),
        sa.Column("gpu_instance_id", sa.String(36), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("subtitle_url", sa.Text(), nullable=True),
        sa.Column("output_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("gpu_cost_usd", sa.Float(), nullable=False, default=0.0),
        sa.Column("gpu_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("publish_after_generate", sa.Boolean(), nullable=False, default=False),
        sa.Column("published", sa.Boolean(), nullable=False, default=False),
        sa.Column("avatar_provider", sa.String(32), nullable=False, default="liveportrait"),
        sa.Column("tts_provider", sa.String(32), nullable=False, default="edge_tts"),
        sa.Column("music_url", sa.Text(), nullable=True),
        sa.Column("intro_url", sa.Text(), nullable=True),
        sa.Column("outro_url", sa.Text(), nullable=True),
        sa.Column("subtitle_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["facebook_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_jobs_page_id", "video_jobs", ["page_id"])
    op.create_index("ix_video_jobs_status", "video_jobs", ["status"])

    op.create_table(
        "gpu_instances",
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="starting"),
        sa.Column("gpu_type", sa.String(64), nullable=True),
        sa.Column("price_per_hour", sa.Float(), nullable=False, default=0.0),
        sa.Column("ssh_host", sa.String(255), nullable=True),
        sa.Column("ssh_port", sa.Integer(), nullable=False, default=22),
        sa.Column("api_endpoint", sa.Text(), nullable=True),
        sa.Column("total_jobs", sa.Integer(), nullable=False, default=0),
        sa.Column("last_job_at", sa.String(32), nullable=True),
        sa.Column("idle_since", sa.String(32), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gpu_instances_provider", "gpu_instances", ["provider"])
    op.create_index("ix_gpu_instances_external_id", "gpu_instances", ["external_id"])
    op.create_index("ix_gpu_instances_status", "gpu_instances", ["status"])

    op.create_table(
        "video_page_configs",
        sa.Column("page_id", sa.String(36), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("character_image_url", sa.Text(), nullable=True),
        sa.Column("voice_id", sa.String(64), nullable=True),
        sa.Column("language", sa.String(8), nullable=False, default="vi"),
        sa.Column("music_url", sa.Text(), nullable=True),
        sa.Column("intro_url", sa.Text(), nullable=True),
        sa.Column("outro_url", sa.Text(), nullable=True),
        sa.Column("subtitle_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("avatar_provider", sa.String(32), nullable=False, default="liveportrait"),
        sa.Column("tts_provider", sa.String(32), nullable=False, default="edge_tts"),
        sa.Column("gpu_provider", sa.String(32), nullable=False, default="vast"),
        sa.Column("publish_after_generate", sa.Boolean(), nullable=False, default=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["facebook_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id"),
    )
    op.create_index("ix_video_page_configs_page_id", "video_page_configs", ["page_id"])


def downgrade() -> None:
    op.drop_table("video_page_configs")
    op.drop_table("gpu_instances")
    op.drop_table("video_jobs")
