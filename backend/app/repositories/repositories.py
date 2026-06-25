"""Concrete repositories. Each binds a model and adds entity-specific queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.integration import (
    AuditLog,
    FacebookComment,
    FacebookPage,
    FacebookPost,
    Notification,
    Report,
    SystemLog,
    TelegramConfig,
    TelegramLog,
)
from app.models.memory import Conversation, ConversationMessage, Memory
from app.models.post import (
    AIUsageLog,
    Post,
    PostVersion,
    SchedulerHistory,
    SchedulerJob,
)
from app.models.project import (
    AIProvider,
    Project,
    PromptTemplate,
    SystemPrompt,
)
from app.models.source import KeywordSource, RSSSource, SourceCache, Topic
from app.models.user import RefreshToken, User, UserSettings
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.get_by(email=email.lower().strip())


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_active(self, token: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token == token, RefreshToken.revoked.is_(False)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke_all(self, user_id: str) -> None:
        for tok in self.list(user_id=user_id):
            tok.revoked = True
        self.db.flush()


class UserSettingsRepository(BaseRepository[UserSettings]):
    model = UserSettings


class ProjectRepository(BaseRepository[Project]):
    model = Project


class AIProviderRepository(BaseRepository[AIProvider]):
    model = AIProvider

    def list_enabled(self, project_id: str) -> list[AIProvider]:
        return self.list(project_id=project_id, enabled=True, order_by="priority", desc=False)


class SystemPromptRepository(BaseRepository[SystemPrompt]):
    model = SystemPrompt

    def get_active(self, project_id: str) -> SystemPrompt | None:
        return self.get_by(project_id=project_id, active=True)


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    model = PromptTemplate

    def get_by_type(self, project_id: str, type_: str) -> PromptTemplate | None:
        return self.get_by(project_id=project_id, type=type_, active=True)


class TopicRepository(BaseRepository[Topic]):
    model = Topic


class RSSSourceRepository(BaseRepository[RSSSource]):
    model = RSSSource


class KeywordSourceRepository(BaseRepository[KeywordSource]):
    model = KeywordSource


class SourceCacheRepository(BaseRepository[SourceCache]):
    model = SourceCache

    def exists(self, project_id: str, hash_: str) -> bool:
        stmt = select(func.count()).select_from(SourceCache).where(
            SourceCache.project_id == project_id, SourceCache.hash == hash_
        )
        return bool(self.db.execute(stmt).scalar())


class PostRepository(BaseRepository[Post]):
    model = Post

    def list_filtered(
        self,
        project_id: str,
        *,
        status: str | None = None,
        language: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Post]:
        stmt = select(Post).where(Post.project_id == project_id, Post.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Post.status == status)
        if language:
            stmt = stmt.where(Post.language == language)
        if keyword:
            stmt = stmt.where(Post.content.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(Post.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count_since(self, project_id: str, since: datetime, status: str | None = None) -> int:
        stmt = select(func.count()).select_from(Post).where(
            Post.project_id == project_id,
            Post.deleted_at.is_(None),
            Post.created_at >= since,
        )
        if status:
            stmt = stmt.where(Post.status == status)
        return int(self.db.execute(stmt).scalar() or 0)


class PostVersionRepository(BaseRepository[PostVersion]):
    model = PostVersion


class SchedulerJobRepository(BaseRepository[SchedulerJob]):
    model = SchedulerJob

    def list_enabled(self) -> list[SchedulerJob]:
        return self.list(enabled=True, limit=None)


class SchedulerHistoryRepository(BaseRepository[SchedulerHistory]):
    model = SchedulerHistory


class AIUsageLogRepository(BaseRepository[AIUsageLog]):
    model = AIUsageLog

    def totals(self, project_id: str, since: datetime | None = None) -> tuple[int, float]:
        stmt = select(
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.cost), 0.0),
        ).where(AIUsageLog.project_id == project_id)
        if since:
            stmt = stmt.where(AIUsageLog.created_at >= since)
        row = self.db.execute(stmt).one()
        return int(row[0]), float(row[1])


class FacebookPageRepository(BaseRepository[FacebookPage]):
    model = FacebookPage

    def get_by_fb_page_id(self, fb_page_id: str) -> FacebookPage | None:
        """Resolve a connected page by its Facebook page id (webhook ``entry.id``)."""
        rows = self.list(page_id=fb_page_id, limit=1)
        return rows[0] if rows else None


class FacebookPostRepository(BaseRepository[FacebookPost]):
    model = FacebookPost


class FacebookCommentRepository(BaseRepository[FacebookComment]):
    model = FacebookComment

    def exists(self, comment_id: str) -> bool:
        stmt = select(func.count()).select_from(FacebookComment).where(
            FacebookComment.comment_id == comment_id
        )
        return bool(self.db.execute(stmt).scalar())

    def list_for_page(self, page_id: str, limit: int = 50) -> list[FacebookComment]:
        return self.list(page_id=page_id, order_by="created_at", desc=True, limit=limit)


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    def get_or_create(
        self,
        *,
        project_id: str,
        page_id: str,
        channel: str,
        external_user_id: str,
        user_name: str | None = None,
    ) -> Conversation:
        """Return the conversation for this user/page/channel, creating it once."""
        existing = self.get_by(
            page_id=page_id, channel=channel, external_user_id=external_user_id
        )
        if existing:
            if user_name and existing.user_name != user_name:
                existing.user_name = user_name
                self.db.flush()
            return existing
        return self.create(
            project_id=project_id,
            page_id=page_id,
            channel=channel,
            external_user_id=external_user_id,
            user_name=user_name,
        )

    def list_active(self, limit: int | None = None) -> list[Conversation]:
        """Conversations with at least one stored message, newest activity first."""
        stmt = (
            self._base_query()
            .where(Conversation.message_count > 0)
            .order_by(Conversation.last_message_at.desc().nullslast())
        )
        if limit:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())


class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    model = ConversationMessage

    def recent(self, conversation_id: str, limit: int = 6) -> list[ConversationMessage]:
        """Most recent turns first; caller reverses for chronological context."""
        return self.list(
            conversation_id=conversation_id, order_by="created_at", desc=True, limit=limit
        )


class MemoryRepository(BaseRepository[Memory]):
    model = Memory

    def list_active(self, conversation_id: str) -> list[Memory]:
        """All non-archived memories for a conversation (for in-process search)."""
        return self.list(
            conversation_id=conversation_id,
            archived=False,
            order_by="importance",
            desc=True,
            limit=None,
        )

    def by_type(self, conversation_id: str, mem_type: str, limit: int) -> list[Memory]:
        return self.list(
            conversation_id=conversation_id,
            archived=False,
            type=mem_type,
            order_by="created_at",
            desc=True,
            limit=limit,
        )

    def recent(self, conversation_id: str, limit: int) -> list[Memory]:
        return self.list(
            conversation_id=conversation_id,
            archived=False,
            order_by="created_at",
            desc=True,
            limit=limit,
        )

    def important(self, conversation_id: str, limit: int) -> list[Memory]:
        return self.list(
            conversation_id=conversation_id,
            archived=False,
            order_by="importance",
            desc=True,
            limit=limit,
        )


class TelegramConfigRepository(BaseRepository[TelegramConfig]):
    model = TelegramConfig

    def get_for_project(self, project_id: str) -> TelegramConfig | None:
        return self.get_by(project_id=project_id, enabled=True)


class TelegramLogRepository(BaseRepository[TelegramLog]):
    model = TelegramLog


class ReportRepository(BaseRepository[Report]):
    model = Report


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def unread_count(self, user_id: str) -> int:
        return self.count(user_id=user_id, read=False)


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog


class SystemLogRepository(BaseRepository[SystemLog]):
    model = SystemLog

    def list_filtered(
        self, *, level: str | None = None, module: str | None = None, limit: int = 100
    ) -> list[SystemLog]:
        stmt = select(SystemLog)
        if level:
            stmt = stmt.where(SystemLog.level == level)
        if module:
            stmt = stmt.where(SystemLog.module == module)
        stmt = stmt.order_by(SystemLog.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def cleanup_older_than(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = self.db.query(SystemLog).filter(SystemLog.created_at < cutoff).delete()
        self.db.flush()
        return int(rows or 0)
