"""Growth Engine database models.

Tables covering per-page growth config, prompt management, trend topics,
content drafts, learning records, and AI usage quota.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BaseModelMixin


class PageGrowthConfig(Base, BaseModelMixin):
    """Per-page growth engine configuration."""

    __tablename__ = "page_growth_configs"

    page_id: Mapped[str] = mapped_column(String(36), ForeignKey("facebook_pages.id"), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_personality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tone: Mapped[str] = mapped_column(String(64), default="friendly", nullable=False)
    writing_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emoji_level: Mapped[str] = mapped_column(String(16), default="moderate", nullable=False)
    content_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_content_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    reel_frequency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posts_per_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality_threshold: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    image_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    video_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cta_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    forbidden_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitors: Mapped[str | None] = mapped_column(Text, nullable=True)
    trend_sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    video_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tts_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)


class GrowthPromptTemplate(Base, BaseModelMixin):
    """Versioned prompt templates for the growth engine, editable from UI."""

    __tablename__ = "growth_prompt_templates"

    page_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TrendTopic(Base, BaseModelMixin):
    """A discovered trending topic for a page."""

    __tablename__ = "trend_topics"

    page_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="rss", nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audience_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False, index=True)
    content_format: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ContentDraft(Base, BaseModelMixin):
    """AI-generated content draft awaiting review or auto-publish."""

    __tablename__ = "content_drafts"

    page_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    topic_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    content_type: Mapped[str] = mapped_column(String(32), default="post", nullable=False)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    scheduled_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class LearningRecord(Base, BaseModelMixin):
    """Performance record created after each published post."""

    __tablename__ = "learning_records"

    page_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    draft_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hook_pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    publish_hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    publish_day: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watch_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    performance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class ProviderQuota(Base, BaseModelMixin):
    """Daily/monthly AI usage quota tracking per provider."""

    __tablename__ = "provider_quotas"

    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    date_key: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    requests_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requests_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PromptCacheEntry(Base, BaseModelMixin):
    """Cached AI response keyed by prompt hash."""

    __tablename__ = "prompt_cache_entries"

    cache_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
