"""Pydantic schemas for the Video Generation Engine API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VideoPageConfigBase(BaseModel):
    enabled: bool = False
    character_image_url: str | None = None
    voice_id: str | None = None
    language: str = "vi"
    music_url: str | None = None
    intro_url: str | None = None
    outro_url: str | None = None
    subtitle_enabled: bool = True
    avatar_provider: str = "liveportrait"
    tts_provider: str = "edge_tts"
    gpu_provider: str = "vast"
    publish_after_generate: bool = False


class VideoPageConfigOut(VideoPageConfigBase):
    id: str
    page_id: str

    model_config = {"from_attributes": True}


class VideoJobCreate(BaseModel):
    page_id: str
    script: str = Field(..., min_length=10)
    voice_id: str | None = None
    character_image_url: str | None = None
    language: str = "vi"
    publish_after_generate: bool = False
    avatar_provider: str = "liveportrait"
    tts_provider: str = "edge_tts"
    gpu_provider: str = "vast"
    music_url: str | None = None
    intro_url: str | None = None
    outro_url: str | None = None
    subtitle_enabled: bool = True


class VideoJobOut(BaseModel):
    id: str
    page_id: str
    script: str
    voice_id: str | None
    character_image_url: str | None
    language: str
    status: str
    gpu_provider: str | None
    gpu_instance_id: str | None
    audio_url: str | None
    subtitle_url: str | None
    output_url: str | None
    thumbnail_url: str | None
    duration_seconds: int
    gpu_cost_usd: float
    retry_count: int
    error_message: str | None
    publish_after_generate: bool
    published: bool
    avatar_provider: str
    tts_provider: str

    model_config = {"from_attributes": True}


class GPUInstanceOut(BaseModel):
    id: str
    provider: str
    external_id: str | None
    status: str
    gpu_type: str | None
    price_per_hour: float
    total_jobs: int
    idle_since: str | None

    model_config = {"from_attributes": True}
