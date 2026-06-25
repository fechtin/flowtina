"""Facebook, Telegram, report, notification and audit/system-log models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BaseModelMixin, TimestampMixin, UUIDMixin


class FacebookPage(Base, BaseModelMixin):
    __tablename__ = "facebook_pages"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    page_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_id: Mapped[str] = mapped_column(String(64), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="healthy", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Auto-engagement: when enabled, the scheduler polls recent posts and likes
    # and/or AI-replies to incoming comments. Requires the page token to carry
    # pages_read_engagement + pages_manage_engagement.
    auto_like_comments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_reply_comments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # When enabled, the Messenger webhook AI-replies to direct messages. Requires
    # the page token to carry pages_messaging.
    auto_reply_messages: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Optional persona/guidance steering AI-generated comment replies.
    reply_persona: Mapped[str | None] = mapped_column(Text, nullable=True)


class FacebookComment(Base, BaseModelMixin):
    """A comment seen on one of the page's posts, with engagement outcome.

    One row per Facebook comment id keeps the poller idempotent: a comment is
    liked/replied at most once even if it is returned again on the next poll.
    """

    __tablename__ = "facebook_comments"

    page_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    facebook_post_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    comment_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    commenter_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    liked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="processed", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FacebookPost(Base, BaseModelMixin):
    __tablename__ = "facebook_posts"

    post_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    page_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    facebook_post_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TelegramConfig(Base, BaseModelMixin):
    __tablename__ = "telegram_configs"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    bot_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TelegramLog(Base, BaseModelMixin):
    __tablename__ = "telegram_logs"

    project_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="sent", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Report(Base, BaseModelMixin):
    __tablename__ = "reports"

    project_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="daily", nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Notification(Base, BaseModelMixin):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)


class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    old_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SystemLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "system_logs"

    level: Mapped[str] = mapped_column(String(16), default="INFO", index=True, nullable=False)
    module: Mapped[str] = mapped_column(String(32), default="system", index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
