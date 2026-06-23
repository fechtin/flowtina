"""Post, post-version, scheduler and AI-usage models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BaseModelMixin


class Post(Base, BaseModelMixin):
    __tablename__ = "posts"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_ai: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Target Facebook page recorded when a post is queued for (auto) publishing.
    facebook_page_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PostVersion(Base, BaseModelMixin):
    __tablename__ = "post_versions"

    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class SchedulerJob(Base, BaseModelMixin):
    __tablename__ = "scheduler_jobs"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), default="generate_content", nullable=False)
    cron_expression: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Content generation options.
    content_type: Mapped[str] = mapped_column(String(32), default="short_post", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    # Auto-publish: when enabled, generated posts are published to facebook_page_id.
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # When require_approval is set, posts wait for Telegram approval before publishing.
    require_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    facebook_page_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SchedulerHistory(Base, BaseModelMixin):
    __tablename__ = "scheduler_history"

    job_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AIUsageLog(Base, BaseModelMixin):
    __tablename__ = "ai_usage_logs"

    project_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
