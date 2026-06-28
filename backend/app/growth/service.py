"""Growth Engine Service: orchestrate all Growth Engine modules."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.growth.content.content_generator import generate_post
from app.growth.content.hook_generator import generate_best_hook
from app.growth.content.image_generator import ImageGenerationError, generate_image
from app.growth.content.reviewer import check_duplicate_in_db, review_content
from app.growth.gateway.gateway import AIGateway
from app.growth.gateway.quota import QuotaManager
from app.growth.learning.engine import LearningEngine, PerformanceMetrics
from app.growth.models import (
    ContentDraft,
    GrowthPromptTemplate,
    PageGrowthConfig,
    ProviderQuota,
    TrendTopic,
)
from app.growth.planner.planner import ContentPlanner
from app.growth.trend.discovery import discover_from_rss, discover_from_url, discover_trending
from app.growth.trend.ranking import rank_topics
from app.models.integration import FacebookPage
from app.models.source import RSSSource, Topic, URLSource
from app.utils.media import remove_upload, save_bytes

log = get_logger("growth.service")


class GrowthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Page Growth Config
    # ------------------------------------------------------------------

    def get_config(self, page_id: str) -> PageGrowthConfig | None:
        return self.db.query(PageGrowthConfig).filter_by(page_id=page_id).first()

    def upsert_config(self, page_id: str, data: dict) -> PageGrowthConfig:
        cfg = self.get_config(page_id)
        if cfg:
            for k, v in data.items():
                setattr(cfg, k, v)
        else:
            cfg = PageGrowthConfig(page_id=page_id, **data)
            self.db.add(cfg)
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    # ------------------------------------------------------------------
    # Trend Discovery
    # ------------------------------------------------------------------

    def _get_project_id(self, page_id: str) -> str | None:
        page = self.db.query(FacebookPage).filter_by(id=page_id).first()
        return page.project_id if page else None

    async def run_discovery(self, page_id: str, sources: list[str] | None = None, max_per_source: int = 10) -> list[TrendTopic]:
        cfg = self.get_config(page_id)

        # Resolve sources from page's project if not explicitly provided
        if sources:
            custom_sources = sources
            raw_topics = await discover_trending(custom_sources, max_per_source)
        else:
            project_id = self._get_project_id(page_id)
            if project_id:
                rss_urls = [
                    r.url for r in
                    self.db.query(RSSSource).filter_by(project_id=project_id, enabled=True).all()
                ]
                url_sources = [
                    u.url for u in
                    self.db.query(URLSource).filter_by(project_id=project_id, enabled=True).all()
                ]
                rss_tasks = [discover_from_rss(url, max_per_source) for url in rss_urls]
                url_tasks = [discover_from_url(url) for url in url_sources]
                results = await asyncio.gather(*rss_tasks, *url_tasks, return_exceptions=True)
                raw_topics = [t for r in results if isinstance(r, list) for t in r]
            else:
                raw_topics = await discover_trending(None, max_per_source)
        categories = []
        blocked = []
        if cfg:
            if cfg.content_categories:
                categories = [c.strip() for c in cfg.content_categories.split(",") if c.strip()]
            if cfg.blocked_keywords:
                blocked = [k.strip() for k in cfg.blocked_keywords.split(",") if k.strip()]
        # Merge project topics as additional category signals
        project_id = self._get_project_id(page_id)
        if project_id:
            project_topics = [
                t.topic for t in
                self.db.query(Topic).filter_by(project_id=project_id, active=True).all()
            ]
            categories = list(dict.fromkeys(categories + project_topics))
        scored = rank_topics(raw_topics, categories, blocked, top_n=30)
        planner = ContentPlanner(self.db, page_id)
        posts_per_day = cfg.posts_per_day if cfg else 1
        plans = planner.plan(scored, posts_per_day=posts_per_day)
        self.db.commit()
        return [p.topic for p in plans]

    # ------------------------------------------------------------------
    # Content Draft Generation
    # ------------------------------------------------------------------

    async def generate_draft(self, page_id: str, project_id: str, topic_id: str, content_type: str | None = None) -> ContentDraft:
        topic = self.db.query(TrendTopic).filter_by(id=topic_id, page_id=page_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found for page {page_id}")

        cfg = self.get_config(page_id)
        ct = content_type or (topic.content_format or "short_post")
        tone = cfg.tone if cfg else "friendly"
        style = (cfg.writing_style if cfg else None) or "conversational"
        language = cfg.language if cfg else "en"
        audience = (cfg.target_audience if cfg else None) or "general public"
        emoji_level = cfg.emoji_level if cfg else "moderate"
        cta_style = (cfg.cta_style if cfg else None) or "soft"
        brand_personality = (cfg.brand_personality if cfg else None) or "friendly and professional"
        forbidden = (cfg.forbidden_topics if cfg else None) or ""
        blocked_kws = [k.strip() for k in (cfg.blocked_keywords or "").split(",") if k.strip()] if cfg else []
        quality_threshold = cfg.quality_threshold if cfg else 60
        preferred_llm = cfg.llm_preference if cfg else None

        gateway = AIGateway(self.db, project_id, preferred_provider=preferred_llm)

        hook = await generate_best_hook(
            gateway, topic.title, topic.summary or "", tone=tone, language=language,
            audience=audience, content_format=ct,
        )

        content = await generate_post(
            gateway, topic.title, topic.summary or "", hook=hook, content_type=ct,
            tone=tone, style=style, language=language, audience=audience,
            emoji_level=emoji_level, cta_style=cta_style,
        )

        # Duplicate check (rule-based)
        is_dup = check_duplicate_in_db(self.db, page_id, content.body)

        # AI Review
        review = await review_content(
            gateway, content, brand_personality=brand_personality,
            forbidden_topics=forbidden, blocked_keywords=blocked_kws,
            quality_threshold=quality_threshold,
        )

        status = "pending_review"
        if is_dup:
            review.passed = False
            review.notes = f"Duplicate detected. {review.notes}"
        if review.passed and cfg and cfg.auto_publish and not cfg.approval_required:
            status = "approved"

        # Best-effort image generation (FLUX.1-schnell via Cloudflare). A failure
        # — unconfigured, quota exhausted, timeout — degrades to a text-only draft.
        media_url = None
        if settings.growth_image_enabled and content.image_prompt:
            try:
                image_bytes = await generate_image(content.image_prompt)
                media_url = save_bytes(image_bytes, page_id, ".jpg")
            except ImageGenerationError as exc:
                log.warning(f"Image generation skipped for page {page_id}: {exc}")

        draft = ContentDraft(
            page_id=page_id,
            topic_id=topic_id,
            content_type=ct,
            hook=hook,
            body=content.body,
            caption=content.caption,
            cta=content.cta,
            hashtags=",".join(content.hashtags),
            image_prompt=content.image_prompt,
            media_url=media_url,
            quality_score=review.score,
            review_notes=review.notes,
            status=status if review.passed else "rejected",
            model_used=None,
            provider_used=None,
            prompt_version=1,
            language=language,
        )
        self.db.add(draft)
        topic.status = "in_progress"
        self.db.commit()
        self.db.refresh(draft)
        return draft

    # ------------------------------------------------------------------
    # Drafts CRUD
    # ------------------------------------------------------------------

    def list_drafts(self, page_id: str, status: str | None = None, limit: int = 50) -> list[ContentDraft]:
        q = (
            self.db.query(ContentDraft)
            .filter_by(page_id=page_id)
            .filter(ContentDraft.deleted_at.is_(None))
        )
        if status:
            q = q.filter(ContentDraft.status == status)
        return q.order_by(ContentDraft.created_at.desc()).limit(limit).all()

    def get_draft(self, draft_id: str, page_id: str) -> ContentDraft | None:
        return (
            self.db.query(ContentDraft)
            .filter_by(id=draft_id, page_id=page_id)
            .filter(ContentDraft.deleted_at.is_(None))
            .first()
        )

    def delete_draft(self, draft_id: str, page_id: str) -> None:
        """Soft-delete a draft, pruning its generated image file if present."""
        draft = self.get_draft(draft_id, page_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        if draft.media_url:
            remove_upload(draft.media_url)
        draft.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    def delete_all_drafts(self, page_id: str) -> int:
        """Soft-delete every draft on a page; returns the count removed."""
        drafts = self.list_drafts(page_id, limit=10_000)
        now = datetime.now(timezone.utc)
        for draft in drafts:
            if draft.media_url:
                remove_upload(draft.media_url)
            draft.deleted_at = now
        self.db.commit()
        return len(drafts)

    def update_draft(self, draft_id: str, page_id: str, data: dict) -> ContentDraft:
        draft = self.get_draft(draft_id, page_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        for k, v in data.items():
            setattr(draft, k, v)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def approve_draft(self, draft_id: str, page_id: str) -> ContentDraft:
        return self.update_draft(draft_id, page_id, {"status": "approved"})

    def reject_draft(self, draft_id: str, page_id: str, notes: str = "") -> ContentDraft:
        return self.update_draft(draft_id, page_id, {"status": "rejected", "review_notes": notes})

    # ------------------------------------------------------------------
    # Topics
    # ------------------------------------------------------------------

    def list_topics(self, page_id: str, status: str | None = None, limit: int = 50) -> list[TrendTopic]:
        q = (
            self.db.query(TrendTopic)
            .filter_by(page_id=page_id)
            .filter(TrendTopic.deleted_at.is_(None))
        )
        if status:
            q = q.filter(TrendTopic.status == status)
        return q.order_by(TrendTopic.total_score.desc()).limit(limit).all()

    def delete_topic(self, topic_id: str, page_id: str) -> None:
        """Soft-delete a single trend topic."""
        topic = (
            self.db.query(TrendTopic)
            .filter_by(id=topic_id, page_id=page_id)
            .filter(TrendTopic.deleted_at.is_(None))
            .first()
        )
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        topic.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    def delete_all_topics(self, page_id: str) -> int:
        """Soft-delete every trend topic on a page; returns the count removed."""
        topics = self.list_topics(page_id, limit=10_000)
        now = datetime.now(timezone.utc)
        for topic in topics:
            topic.deleted_at = now
        self.db.commit()
        return len(topics)

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def record_performance(self, page_id: str, draft_id: str | None, metrics: PerformanceMetrics):
        engine = LearningEngine(self.db)
        record = engine.record_performance(page_id, draft_id, metrics)
        self.db.commit()
        return record

    def get_insights(self, page_id: str) -> dict:
        engine = LearningEngine(self.db)
        return {
            "best_content_types": engine.get_best_content_types(page_id),
            "best_posting_times": engine.get_best_posting_times(page_id),
        }

    # ------------------------------------------------------------------
    # Prompt Templates
    # ------------------------------------------------------------------

    def list_prompts(self, page_id: str) -> list[GrowthPromptTemplate]:
        return (
            self.db.query(GrowthPromptTemplate)
            .filter(
                (GrowthPromptTemplate.page_id == page_id) | (GrowthPromptTemplate.page_id.is_(None))
            )
            .filter_by(active=True)
            .order_by(GrowthPromptTemplate.task_type)
            .all()
        )

    def create_prompt(self, page_id: str, data: dict) -> GrowthPromptTemplate:
        tpl = GrowthPromptTemplate(page_id=page_id, **data)
        self.db.add(tpl)
        self.db.commit()
        self.db.refresh(tpl)
        return tpl

    def update_prompt(self, prompt_id: str, page_id: str, data: dict) -> GrowthPromptTemplate:
        tpl = self.db.query(GrowthPromptTemplate).filter_by(id=prompt_id, page_id=page_id).first()
        if not tpl:
            raise ValueError(f"Prompt template {prompt_id} not found")
        if "content" in data:
            tpl.version += 1
        for k, v in data.items():
            setattr(tpl, k, v)
        self.db.commit()
        self.db.refresh(tpl)
        return tpl

    # ------------------------------------------------------------------
    # Quota status
    # ------------------------------------------------------------------

    def get_quota_status(self, provider: str, model: str) -> dict:
        qm = QuotaManager(self.db)
        return qm.get_status(provider, model)
