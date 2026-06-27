"""Video Generation Engine database models."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BaseModelMixin


class VideoJob(Base, BaseModelMixin):
    """A video generation job tracking full lifecycle from queue to completion."""

    __tablename__ = "video_jobs"

    page_id: Mapped[str] = mapped_column(String(36), ForeignKey("facebook_pages.id"), index=True, nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    voice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    character_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="vi", nullable=False)
    # Job lifecycle state machine
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    # Provider and GPU instance
    gpu_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gpu_instance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Generated artifacts
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitle_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Cost and timing
    gpu_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gpu_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When generation finishes, optionally hand off to publish service
    publish_after_generate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Avatar and TTS configuration
    avatar_provider: Mapped[str] = mapped_column(String(32), default="liveportrait", nullable=False)
    tts_provider: Mapped[str] = mapped_column(String(32), default="edge_tts", nullable=False)
    music_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    intro_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    outro_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitle_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GPUInstance(Base, BaseModelMixin):
    """A rented GPU instance managed by the resource manager."""

    __tablename__ = "gpu_instances"

    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="starting", nullable=False, index=True)
    gpu_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_per_hour: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ssh_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    api_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_job_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idle_since: Mapped[str | None] = mapped_column(String(32), nullable=True)


class VideoPageConfig(Base, BaseModelMixin):
    """Per-page video generation configuration."""

    __tablename__ = "video_page_configs"

    page_id: Mapped[str] = mapped_column(String(36), ForeignKey("facebook_pages.id"), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    character_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="vi", nullable=False)
    music_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    intro_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    outro_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitle_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_provider: Mapped[str] = mapped_column(String(32), default="liveportrait", nullable=False)
    tts_provider: Mapped[str] = mapped_column(String(32), default="edge_tts", nullable=False)
    gpu_provider: Mapped[str] = mapped_column(String(32), default="vast", nullable=False)
    publish_after_generate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
