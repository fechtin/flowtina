"""growth engine tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-27 00:00:01.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "page_growth_configs",
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("language", sa.String(8), nullable=False, default="en"),
        sa.Column("country", sa.String(64), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("brand_personality", sa.String(255), nullable=True),
        sa.Column("tone", sa.String(64), nullable=False, default="friendly"),
        sa.Column("writing_style", sa.String(64), nullable=True),
        sa.Column("emoji_level", sa.String(16), nullable=False, default="moderate"),
        sa.Column("content_categories", sa.Text(), nullable=True),
        sa.Column("preferred_content_types", sa.Text(), nullable=True),
        sa.Column("reel_frequency", sa.Integer(), nullable=False, default=0),
        sa.Column("posts_per_day", sa.Integer(), nullable=False, default=1),
        sa.Column("auto_publish", sa.Boolean(), nullable=False, default=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, default=True),
        sa.Column("quality_threshold", sa.Integer(), nullable=False, default=60),
        sa.Column("image_style", sa.String(64), nullable=True),
        sa.Column("video_style", sa.String(64), nullable=True),
        sa.Column("cta_style", sa.String(64), nullable=True),
        sa.Column("forbidden_topics", sa.Text(), nullable=True),
        sa.Column("blocked_keywords", sa.Text(), nullable=True),
        sa.Column("competitors", sa.Text(), nullable=True),
        sa.Column("trend_sources", sa.Text(), nullable=True),
        sa.Column("llm_preference", sa.String(64), nullable=True),
        sa.Column("image_model", sa.String(64), nullable=True),
        sa.Column("video_model", sa.String(64), nullable=True),
        sa.Column("tts_provider", sa.String(64), nullable=True),
        sa.Column("page_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["facebook_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id"),
    )
    op.create_index("ix_page_growth_configs_page_id", "page_growth_configs", ["page_id"])

    op.create_table(
        "growth_prompt_templates",
        sa.Column("page_id", sa.String(36), nullable=True),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, default="en"),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_growth_prompt_templates_task_type", "growth_prompt_templates", ["task_type"])
    op.create_index("ix_growth_prompt_templates_page_id", "growth_prompt_templates", ["page_id"])

    op.create_table(
        "trend_topics",
        sa.Column("page_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=False, default="rss"),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("language", sa.String(8), nullable=False, default="en"),
        sa.Column("trend_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("freshness_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("audience_match_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("total_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("status", sa.String(16), nullable=False, default="new"),
        sa.Column("content_format", sa.String(32), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trend_topics_page_id", "trend_topics", ["page_id"])
    op.create_index("ix_trend_topics_total_score", "trend_topics", ["total_score"])
    op.create_index("ix_trend_topics_status", "trend_topics", ["status"])

    op.create_table(
        "content_drafts",
        sa.Column("page_id", sa.String(36), nullable=False),
        sa.Column("topic_id", sa.String(36), nullable=True),
        sa.Column("content_type", sa.String(32), nullable=False, default="post"),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("cta", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=False, default=0),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, default="draft"),
        sa.Column("model_used", sa.String(120), nullable=True),
        sa.Column("provider_used", sa.String(32), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=False, default=1),
        sa.Column("language", sa.String(8), nullable=False, default="en"),
        sa.Column("scheduled_at", sa.String(32), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_drafts_page_id", "content_drafts", ["page_id"])
    op.create_index("ix_content_drafts_topic_id", "content_drafts", ["topic_id"])
    op.create_index("ix_content_drafts_status", "content_drafts", ["status"])

    op.create_table(
        "learning_records",
        sa.Column("page_id", sa.String(36), nullable=False),
        sa.Column("draft_id", sa.String(36), nullable=True),
        sa.Column("topic", sa.String(500), nullable=True),
        sa.Column("content_type", sa.String(32), nullable=True),
        sa.Column("hook_pattern", sa.String(255), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=False, default=1),
        sa.Column("model_used", sa.String(120), nullable=True),
        sa.Column("publish_hour", sa.Integer(), nullable=False, default=0),
        sa.Column("publish_day", sa.Integer(), nullable=False, default=0),
        sa.Column("reach", sa.Integer(), nullable=False, default=0),
        sa.Column("impressions", sa.Integer(), nullable=False, default=0),
        sa.Column("engagement", sa.Integer(), nullable=False, default=0),
        sa.Column("shares", sa.Integer(), nullable=False, default=0),
        sa.Column("followers_gained", sa.Integer(), nullable=False, default=0),
        sa.Column("watch_time_seconds", sa.Integer(), nullable=False, default=0),
        sa.Column("completion_rate", sa.Float(), nullable=False, default=0.0),
        sa.Column("performance_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_records_page_id", "learning_records", ["page_id"])
    op.create_index("ix_learning_records_draft_id", "learning_records", ["draft_id"])

    op.create_table(
        "provider_quotas",
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("date_key", sa.String(16), nullable=False),
        sa.Column("requests_used", sa.Integer(), nullable=False, default=0),
        sa.Column("tokens_used", sa.Integer(), nullable=False, default=0),
        sa.Column("requests_limit", sa.Integer(), nullable=False, default=0),
        sa.Column("tokens_limit", sa.Integer(), nullable=False, default=0),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_quotas_provider", "provider_quotas", ["provider"])
    op.create_index("ix_provider_quotas_date_key", "provider_quotas", ["date_key"])

    op.create_table(
        "prompt_cache_entries",
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("result_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, default=0),
        sa.Column("expires_at", sa.String(32), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index("ix_prompt_cache_entries_cache_key", "prompt_cache_entries", ["cache_key"])


def downgrade() -> None:
    op.drop_table("prompt_cache_entries")
    op.drop_table("provider_quotas")
    op.drop_table("learning_records")
    op.drop_table("content_drafts")
    op.drop_table("trend_topics")
    op.drop_table("growth_prompt_templates")
    op.drop_table("page_growth_configs")
