"""Content source collection and deduplication.

Fetches RSS feeds (feedparser) and normalizes every item into a ``SourceDocument``.
Deduplicates via SHA-256 of content stored in ``source_cache``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.repositories.repositories import (
    KeywordSourceRepository,
    RSSSourceRepository,
    SourceCacheRepository,
    TopicRepository,
)
from app.utils.text import content_hash

log = get_logger("system")


@dataclass
class SourceDocument:
    title: str
    content: str
    source: str
    language: str = "en"
    published_at: datetime | None = None

    @property
    def hash(self) -> str:
        return content_hash(f"{self.title}\n{self.content}")


class SourceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rss = RSSSourceRepository(db)
        self.keywords = KeywordSourceRepository(db)
        self.topics = TopicRepository(db)
        self.cache = SourceCacheRepository(db)

    async def collect(self, project_id: str, *, max_items: int = 10) -> list[SourceDocument]:
        """Collect fresh (non-duplicate) documents for a project."""
        docs = await self._collect_rss(project_id)
        docs.extend(self._collect_topics(project_id))

        fresh: list[SourceDocument] = []
        for doc in docs:
            if self.cache.exists(project_id, doc.hash):
                continue
            self.cache.create(
                project_id=project_id,
                hash=doc.hash,
                title=doc.title[:500],
                content=doc.content,
                source_type=doc.source,
                published_at=doc.published_at,
            )
            fresh.append(doc)
            if len(fresh) >= max_items:
                break
        self.db.commit()
        return fresh

    async def _collect_rss(self, project_id: str) -> list[SourceDocument]:
        sources = self.rss.list(project_id=project_id, enabled=True)
        if not sources:
            return []
        results = await asyncio.gather(
            *(self._parse_feed(src.url) for src in sources), return_exceptions=True
        )
        docs: list[SourceDocument] = []
        for src, result in zip(sources, results):
            if isinstance(result, Exception):
                log.warning(f"RSS fetch failed for {src.url}: {result}")
                continue
            docs.extend(result)
            src.last_sync_at = datetime.now(timezone.utc)
        return docs

    @staticmethod
    async def _parse_feed(url: str) -> list[SourceDocument]:
        # feedparser is blocking; run it off the event loop.
        parsed = await asyncio.to_thread(feedparser.parse, url)
        docs: list[SourceDocument] = []
        for entry in parsed.entries[:20]:
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            if not title and not summary:
                continue
            docs.append(
                SourceDocument(
                    title=title,
                    content=summary,
                    source="rss",
                    published_at=None,
                )
            )
        return docs

    def _collect_topics(self, project_id: str) -> list[SourceDocument]:
        topics = self.topics.list(project_id=project_id, active=True)
        return [
            SourceDocument(title=t.topic, content="", source="topic")
            for t in topics
        ]
