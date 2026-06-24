"""Source, post, scheduler, integration and dashboard schemas."""

from __future__ import annotations

from datetime import datetime

import re

from pydantic import BaseModel, Field, computed_field, field_validator

from app.schemas.common import TimestampedSchema

# --- Sources ---


class TopicCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=255)
    priority: int = 0


class TopicOut(TimestampedSchema):
    project_id: str
    topic: str
    priority: int
    active: bool


class RSSCreate(BaseModel):
    url: str = Field(min_length=1, max_length=1000)


class RSSOut(TimestampedSchema):
    project_id: str
    url: str
    enabled: bool
    last_sync_at: datetime | None = None


class KeywordCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=255)
    priority: int = 0


class KeywordOut(TimestampedSchema):
    project_id: str
    keyword: str
    priority: int
    enabled: bool


# --- Posts ---


class PostCreate(BaseModel):
    title: str | None = None
    content: str = Field(min_length=1)
    hashtags: str | None = None
    language: str = "en"
    status: str = "draft"
    image_url: str | None = Field(default=None, max_length=1000)


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    hashtags: str | None = None
    language: str | None = None
    status: str | None = None
    publish_at: datetime | None = None
    image_url: str | None = Field(default=None, max_length=1000)


class PostOut(TimestampedSchema):
    project_id: str
    title: str | None = None
    content: str
    hashtags: str | None = None
    language: str
    status: str
    quality_score: int
    publish_at: datetime | None = None
    published_at: datetime | None = None
    created_by_ai: bool
    version: int
    error_message: str | None = None
    facebook_page_id: str | None = None
    image_url: str | None = None
    # Internal local path of an uploaded binary image; never serialised.
    image_path: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_uploaded_image(self) -> bool:
        """True when a binary image was uploaded and is awaiting publish."""
        return bool(self.image_path)


class GenerateRequest(BaseModel):
    topic: str | None = None
    content_type: str = "short_post"
    language: str = "en"
    auto_publish: bool = False
    require_approval: bool = False
    facebook_page_id: str | None = None


# --- Scheduler ---


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    job_type: str = "generate_content"
    cron_expression: str | None = None
    interval_seconds: int | None = None
    timezone: str = "UTC"
    enabled: bool = True
    content_type: str = "short_post"
    language: str = "en"
    auto_publish: bool = False
    require_approval: bool = False
    facebook_page_id: str | None = None


class JobUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    interval_seconds: int | None = None
    timezone: str | None = None
    enabled: bool | None = None
    content_type: str | None = None
    language: str | None = None
    auto_publish: bool | None = None
    require_approval: bool | None = None
    facebook_page_id: str | None = None


class JobOut(TimestampedSchema):
    project_id: str
    name: str
    job_type: str
    cron_expression: str | None = None
    interval_seconds: int | None = None
    timezone: str
    enabled: bool
    content_type: str
    language: str
    auto_publish: bool
    require_approval: bool
    facebook_page_id: str | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class JobHistoryOut(TimestampedSchema):
    job_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    duration_ms: int
    message: str | None = None


# --- Facebook ---


class FacebookPageCreate(BaseModel):
    page_name: str = Field(min_length=1, max_length=255)
    page_id: str = Field(min_length=1, max_length=64)
    access_token: str = Field(min_length=1)


class FacebookPageOut(TimestampedSchema):
    project_id: str
    page_name: str
    page_id: str
    status: str
    enabled: bool
    auto_like_comments: bool = False
    auto_reply_comments: bool = False
    reply_persona: str | None = None


class FacebookEngagementUpdate(BaseModel):
    auto_like_comments: bool | None = None
    auto_reply_comments: bool | None = None
    reply_persona: str | None = Field(default=None, max_length=2000)


class FacebookCommentOut(TimestampedSchema):
    page_id: str
    facebook_post_id: str
    comment_id: str
    commenter_name: str | None = None
    message: str | None = None
    liked: bool
    replied: bool
    reply_text: str | None = None
    status: str
    error_message: str | None = None
    processed_at: datetime | None = None


class FacebookPublishRequest(BaseModel):
    post_id: str
    page_id: str


class FacebookImportRequest(BaseModel):
    # Optional: a System User / long-lived token. If omitted, the server's
    # configured FACEBOOK_SYSTEM_TOKEN is used.
    token: str | None = None
    # Optional: only connect these page IDs. If omitted, every discovered page
    # is connected (and stale ones pruned) — the legacy "import all" behaviour.
    page_ids: list[str] | None = None


class FacebookDiscoveredPage(BaseModel):
    page_id: str
    page_name: str
    already_connected: bool


# --- Telegram ---


class TelegramConfigIn(BaseModel):
    bot_token: str = Field(min_length=1)
    chat_id: str = Field(min_length=1, max_length=64)
    enabled: bool = True

    @field_validator("bot_token")
    @classmethod
    def _validate_bot_token(cls, value: str) -> str:
        token = value.strip()
        if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token):
            raise ValueError(
                "bot_token must look like 123456789:ABCdef... "
                "(digits, a colon, then the secret)"
            )
        return token

    @field_validator("chat_id")
    @classmethod
    def _validate_chat_id(cls, value: str) -> str:
        chat_id = value.strip()
        if not re.fullmatch(r"-?\d+", chat_id):
            raise ValueError(
                "chat_id must be a numeric Telegram chat ID "
                "(e.g. 123456789 or -100123456789), not an email"
            )
        return chat_id


class TelegramConfigOut(TimestampedSchema):
    project_id: str
    chat_id: str
    enabled: bool


class TelegramTestRequest(BaseModel):
    message: str = "Flowtina test message ✅"


# --- Settings ---


class SettingsUpdate(BaseModel):
    theme: str | None = None
    language: str | None = None
    timezone: str | None = None
    default_provider: str | None = None
    default_model: str | None = None
    # Secret: only persisted when a non-empty value is provided.
    default_api_key: str | None = None
    default_base_url: str | None = None
    daily_budget: float | None = None
    retry_count: int | None = None
    random_delay_seconds: int | None = None
    # Secret: only persisted when a non-empty value is provided.
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_enabled: bool | None = None


class SettingsOut(TimestampedSchema):
    user_id: str
    theme: str
    language: str
    timezone: str
    default_provider: str | None = None
    default_model: str | None = None
    default_base_url: str | None = None
    default_api_key_set: bool = False
    daily_budget: float
    retry_count: int
    random_delay_seconds: int
    telegram_chat_id: str | None = None
    telegram_enabled: bool = False
    telegram_bot_token_set: bool = False


# --- Dashboard ---


class DashboardStats(BaseModel):
    posts_today: int = 0
    published_today: int = 0
    failed_today: int = 0
    success_rate: float = 0.0
    total_posts: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    facebook_pages: int = 0
    active_jobs: int = 0
