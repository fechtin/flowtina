"""Pydantic schemas for the Growth Engine API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PageGrowthConfigBase(BaseModel):
    enabled: bool = False
    brand_name: str | None = None
    language: str = "en"
    country: str | None = None
    target_audience: str | None = None
    brand_personality: str | None = None
    tone: str = "friendly"
    writing_style: str | None = None
    emoji_level: str = "moderate"
    content_categories: str | None = None
    preferred_content_types: str | None = None
    reel_frequency: int = 0
    posts_per_day: int = 1
    auto_publish: bool = False
    approval_required: bool = True
    quality_threshold: int = 60
    image_style: str | None = None
    video_style: str | None = None
    cta_style: str | None = None
    forbidden_topics: str | None = None
    blocked_keywords: str | None = None
    competitors: str | None = None
    trend_sources: str | None = None
    llm_preference: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    tts_provider: str | None = None


class PageGrowthConfigCreate(PageGrowthConfigBase):
    pass


class PageGrowthConfigUpdate(PageGrowthConfigBase):
    pass


class PageGrowthConfigOut(PageGrowthConfigBase):
    id: str
    page_id: str

    model_config = {"from_attributes": True}


class TrendTopicOut(BaseModel):
    id: str
    page_id: str
    title: str
    summary: str | None
    source_url: str | None
    source_type: str
    category: str | None
    trend_score: float
    freshness_score: float
    audience_match_score: float
    total_score: float
    status: str
    content_format: str | None

    model_config = {"from_attributes": True}


class ContentDraftBase(BaseModel):
    content_type: str = "short_post"
    hook: str | None = None
    body: str | None = None
    caption: str | None = None
    cta: str | None = None
    hashtags: str | None = None
    image_prompt: str | None = None
    media_url: str | None = None
    language: str = "en"


class ContentDraftCreate(ContentDraftBase):
    topic_id: str | None = None
    scheduled_at: str | None = None


class ContentDraftUpdate(ContentDraftBase):
    status: str | None = None
    quality_score: int | None = None
    review_notes: str | None = None


class ContentDraftOut(ContentDraftBase):
    id: str
    page_id: str
    topic_id: str | None
    quality_score: int
    review_notes: str | None
    status: str
    model_used: str | None
    provider_used: str | None
    scheduled_at: str | None

    model_config = {"from_attributes": True}


class GenerateDraftRequest(BaseModel):
    topic_id: str
    content_type: str = "short_post"


class RegenerateImageRequest(BaseModel):
    image_prompt: str | None = None


class RunDiscoveryRequest(BaseModel):
    sources: list[str] | None = None
    max_per_source: int = Field(default=10, ge=1, le=50)


class LearningRecordOut(BaseModel):
    id: str
    page_id: str
    draft_id: str | None
    content_type: str | None
    hook_pattern: str | None
    publish_hour: int
    publish_day: int
    reach: int
    engagement: int
    shares: int
    performance_score: float

    model_config = {"from_attributes": True}


class RecordPerformanceRequest(BaseModel):
    draft_id: str | None = None
    reach: int = 0
    impressions: int = 0
    engagement: int = 0
    shares: int = 0
    followers_gained: int = 0
    watch_time_seconds: int = 0
    completion_rate: float = 0.0


class GrowthPromptTemplateOut(BaseModel):
    id: str
    page_id: str | None
    task_type: str
    name: str
    content: str
    language: str
    version: int
    active: bool

    model_config = {"from_attributes": True}


class GrowthPromptTemplateCreate(BaseModel):
    task_type: str
    name: str
    content: str
    language: str = "en"


class GrowthPromptTemplateUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    active: bool | None = None


class QuotaStatusOut(BaseModel):
    provider: str
    model: str
    date: str
    requests_used: int
    requests_limit: int
    tokens_used: int
    tokens_limit: int
