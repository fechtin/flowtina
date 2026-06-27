"""Trend Discovery: collect trending topics from RSS, URLs, and news sources.

No AI used here — pure rule-based scraping and parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser

from app.core.logger import get_logger
from app.utils.http_client import fetch_bytes

log = get_logger("growth.trend")

_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "that", "this", "these",
    "those", "it", "its", "they", "them", "their", "we", "our", "you",
    "your", "he", "she", "his", "her", "not", "no", "nor", "so", "yet",
})


@dataclass
class DiscoveredTopic:
    title: str
    summary: str
    source_url: str
    source_type: str
    published_at: datetime | None = None
    category: str | None = None
    keywords: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    return [w for w in dict.fromkeys(words) if w not in _STOP_WORDS][:20]


def _parse_published(entry: Any) -> datetime | None:
    ts = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if ts:
        try:
            return datetime(*ts[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


async def discover_from_rss(url: str, max_items: int = 20) -> list[DiscoveredTopic]:
    """Fetch and parse an RSS/Atom feed, returning discovered topics."""
    topics: list[DiscoveredTopic] = []
    try:
        raw = await fetch_bytes(url)
        feed = feedparser.parse(raw)
        for entry in feed.entries[:max_items]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            summary = re.sub(r"<[^>]+>", " ", summary).strip()[:500]
            link = getattr(entry, "link", url)
            keywords = _extract_keywords(f"{title} {summary}")
            topics.append(
                DiscoveredTopic(
                    title=title,
                    summary=summary,
                    source_url=link,
                    source_type="rss",
                    published_at=_parse_published(entry),
                    keywords=keywords,
                    raw={"feed_title": getattr(feed.feed, "title", "")},
                )
            )
    except Exception as exc:
        log.warning(f"RSS discovery failed for {url}: {exc}")
    return topics


async def discover_from_url(url: str) -> list[DiscoveredTopic]:
    """Scrape a web page and extract article titles/links as topics."""
    from bs4 import BeautifulSoup

    topics: list[DiscoveredTopic] = []
    try:
        raw = await fetch_bytes(url)
        soup = BeautifulSoup(raw, "html.parser")
        seen: set[str] = set()
        for tag in soup.find_all(["h1", "h2", "h3", "a"], limit=60):
            text = tag.get_text(strip=True)
            href = tag.get("href", "") if tag.name == "a" else ""
            if len(text) < 20 or text in seen:
                continue
            seen.add(text)
            link = href if href.startswith("http") else url
            topics.append(
                DiscoveredTopic(
                    title=text,
                    summary="",
                    source_url=link,
                    source_type="url",
                    keywords=_extract_keywords(text),
                )
            )
            if len(topics) >= 15:
                break
    except Exception as exc:
        log.warning(f"URL scrape failed for {url}: {exc}")
    return topics


_DEFAULT_NEWS_FEEDS: list[str] = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.reuters.com/reuters/topNews",
    "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "https://thanhnien.vn/rss/home.rss",
]


async def discover_trending(
    custom_sources: list[str] | None = None,
    max_per_source: int = 10,
) -> list[DiscoveredTopic]:
    """Aggregate trending topics from all configured sources."""
    import asyncio

    sources = custom_sources or _DEFAULT_NEWS_FEEDS
    tasks = [discover_from_rss(src, max_per_source) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_topics: list[DiscoveredTopic] = []
    for r in results:
        if isinstance(r, list):
            all_topics.extend(r)
    return _deduplicate(all_topics)


def _deduplicate(topics: list[DiscoveredTopic]) -> list[DiscoveredTopic]:
    """Remove near-duplicate topics by title similarity."""
    seen: list[str] = []
    unique: list[DiscoveredTopic] = []
    for t in topics:
        normalized = re.sub(r"\W+", " ", t.title.lower()).strip()
        if any(_similarity(normalized, s) > 0.7 for s in seen):
            continue
        seen.append(normalized)
        unique.append(t)
    return unique


def _similarity(a: str, b: str) -> float:
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
