"""Topic Ranking: score discovered topics using rule-based heuristics.

No AI used. Scores are 0–100 for each dimension, combined into total_score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.growth.trend.discovery import DiscoveredTopic


@dataclass
class ScoredTopic:
    topic: DiscoveredTopic
    trend_score: float
    freshness_score: float
    audience_match_score: float
    total_score: float
    content_format: str


def _freshness(published_at: datetime | None) -> float:
    if not published_at:
        return 40.0
    now = datetime.now(timezone.utc)
    age_hours = (now - published_at).total_seconds() / 3600
    if age_hours < 2:
        return 100.0
    if age_hours < 6:
        return 90.0
    if age_hours < 12:
        return 75.0
    if age_hours < 24:
        return 60.0
    if age_hours < 48:
        return 40.0
    if age_hours < 72:
        return 20.0
    return 5.0


def _trend_score(topic: DiscoveredTopic) -> float:
    score = 50.0
    title_lower = topic.title.lower()
    high_signals = ["breaking", "viral", "trending", "new", "record", "first", "launch", "announce"]
    for sig in high_signals:
        if sig in title_lower:
            score += 10.0
    if len(topic.keywords) > 10:
        score += 10.0
    if topic.summary and len(topic.summary) > 100:
        score += 5.0
    return min(score, 100.0)


def _audience_match(topic: DiscoveredTopic, target_categories: list[str], blocked_keywords: list[str]) -> float:
    if not target_categories:
        return 60.0
    combined = f"{topic.title} {topic.summary}".lower()
    for kw in blocked_keywords:
        if kw.lower() in combined:
            return 0.0
    match_count = sum(1 for cat in target_categories if cat.lower() in combined)
    if match_count == 0:
        return 20.0
    return min(40.0 + match_count * 20.0, 100.0)


def _choose_format(topic: DiscoveredTopic) -> str:
    title_lower = topic.title.lower()
    if any(w in title_lower for w in ["video", "watch", "reel", "clip", "tutorial"]):
        return "reel"
    if any(w in title_lower for w in ["top", "best", "tips", "ways", "reasons", "how to"]):
        return "carousel"
    if len(topic.summary) > 200:
        return "long_post"
    return "short_post"


def rank_topics(
    topics: list[DiscoveredTopic],
    target_categories: list[str] | None = None,
    blocked_keywords: list[str] | None = None,
    top_n: int = 20,
) -> list[ScoredTopic]:
    categories = target_categories or []
    blocked = blocked_keywords or []
    scored: list[ScoredTopic] = []
    for t in topics:
        freshness = _freshness(t.published_at)
        trend = _trend_score(t)
        audience = _audience_match(t, categories, blocked)
        if audience == 0.0:
            continue
        total = freshness * 0.4 + trend * 0.35 + audience * 0.25
        scored.append(ScoredTopic(
            topic=t,
            trend_score=round(trend, 2),
            freshness_score=round(freshness, 2),
            audience_match_score=round(audience, 2),
            total_score=round(total, 2),
            content_format=_choose_format(t),
        ))
    scored.sort(key=lambda x: x.total_score, reverse=True)
    return scored[:top_n]
