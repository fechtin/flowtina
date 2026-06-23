"""Content pipeline: collect → summarize → generate → hashtags → quality → draft.

Coordinates the prompt engine, AI service and source service. Designed for
sequential, low-memory execution (no queue/Redis/Celery).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.models.post import Post
from app.prompts.defaults import DEFAULT_HASHTAG_PROMPT, DEFAULT_SUMMARIZE_PROMPT, DEFAULT_TEMPLATES
from app.prompts.engine import prompt_engine
from app.repositories.repositories import (
    PromptTemplateRepository,
    SystemPromptRepository,
    PostRepository,
)
from app.services.ai_service import AIService
from app.services.source_service import SourceDocument, SourceService
from app.utils.text import clean_content, count_words, normalize_hashtags, score_quality

log = get_logger("ai")

_LANG_NAMES = {"en": "English", "vi": "Vietnamese"}


class ContentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ai = AIService(db)
        self.sources = SourceService(db)
        self.system_prompts = SystemPromptRepository(db)
        self.templates = PromptTemplateRepository(db)
        self.posts = PostRepository(db)

    async def generate_for_project(
        self,
        project_id: str,
        *,
        topic: str | None = None,
        content_type: str = "short_post",
        language: str = "en",
        max_posts: int = 1,
    ) -> list[Post]:
        """Run the pipeline and persist draft posts. Returns created posts."""
        documents: list[SourceDocument] = []
        if topic:
            documents = [SourceDocument(title=topic, content="", source="manual")]
        else:
            documents = await self.sources.collect(project_id, max_items=max_posts)
        if not documents:
            log.info(f"No fresh sources for project {project_id}; nothing to generate")
            return []

        created: list[Post] = []
        for doc in documents[:max_posts]:
            post = await self._generate_one(project_id, doc, content_type, language)
            if post:
                created.append(post)
        return created

    async def _generate_one(
        self, project_id: str, doc: SourceDocument, content_type: str, language: str
    ) -> Post | None:
        source_content = doc.content
        # Summarize long source content with the (cheap) provider first.
        if len(source_content) > 3000:
            source_content = await self._summarize(project_id, source_content, language)

        variables = {
            "topic": doc.title,
            "source_content": source_content,
            "language": _LANG_NAMES.get(language, language),
        }
        template = self._resolve_template(project_id, content_type)
        global_prompt = self._global_prompt(project_id)
        final_prompt = prompt_engine.build_final_prompt(
            global_prompt=global_prompt,
            project_prompt=None,
            content_prompt=template,
            variables=variables,
        )

        content = ""
        score = 0
        for attempt in range(settings.quality_max_retries + 1):
            result = await self.ai.generate(project_id, final_prompt)
            content = clean_content(result.text)
            score = score_quality(content)
            if score >= settings.quality_threshold:
                break
            log.warning(f"Quality {score} below threshold; retry {attempt + 1}")

        if not content:
            return None

        hashtags = await self._generate_hashtags(project_id, content, language)
        title = doc.title[:200] if doc.title else content.split("\n", 1)[0][:200]
        post = self.posts.create(
            project_id=project_id,
            title=title,
            content=content,
            hashtags=hashtags,
            language=language,
            status="draft",
            quality_score=score,
            created_by_ai=True,
        )
        self.db.commit()
        self.db.refresh(post)
        log.info(f"Generated draft post {post.id} ({count_words(content)} words, score {score})")
        return post

    async def _summarize(self, project_id: str, text: str, language: str) -> str:
        prompt = prompt_engine.render(
            DEFAULT_SUMMARIZE_PROMPT,
            {"source_content": text[:8000], "language": _LANG_NAMES.get(language, language)},
        )
        try:
            result = await self.ai.generate(project_id, prompt)
            return result.text or text[:3000]
        except Exception as exc:  # noqa: BLE001 - fall back to truncation
            log.warning(f"Summarization failed, truncating: {exc}")
            return text[:3000]

    async def _generate_hashtags(self, project_id: str, content: str, language: str) -> str:
        prompt = prompt_engine.render(
            DEFAULT_HASHTAG_PROMPT,
            {"source_content": content[:2000], "language": _LANG_NAMES.get(language, language)},
        )
        try:
            result = await self.ai.generate(project_id, prompt)
            return normalize_hashtags(result.text)
        except Exception as exc:  # noqa: BLE001 - hashtags are optional
            log.warning(f"Hashtag generation failed: {exc}")
            return ""

    def _resolve_template(self, project_id: str, content_type: str) -> str:
        tmpl = self.templates.get_by_type(project_id, content_type)
        if tmpl:
            return tmpl.template
        return DEFAULT_TEMPLATES.get(content_type, DEFAULT_TEMPLATES["short_post"])

    def _global_prompt(self, project_id: str) -> str | None:
        active = self.system_prompts.get_active(project_id)
        return active.content if active else None
