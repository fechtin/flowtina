"""Content Planner: decide which topics to turn into content and when.

Uses analytics + learning data to schedule posts. No AI calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.growth.models import LearningRecord, TrendTopic
from app.growth.trend.ranking import ScoredTopic

log = get_logger("growth.planner")

_BEST_HOURS_DEFAULT = [9, 12, 17, 20]


@dataclass
class ContentPlan:
    topic: TrendTopic
    content_format: str
    scheduled_at: datetime
    priority: int


class ContentPlanner:
    """Build a content plan from scored topics using historical performance."""

    def __init__(self, db: Session, page_id: str) -> None:
        self.db = db
        self.page_id = page_id

    def plan(
        self,
        scored_topics: list[ScoredTopic],
        posts_per_day: int = 1,
        horizon_days: int = 3,
    ) -> list[ContentPlan]:
        best_hours = self._best_hours()
        slots = self._generate_slots(posts_per_day, horizon_days, best_hours)
        plans: list[ContentPlan] = []
        for i, (scored, slot) in enumerate(zip(scored_topics, slots)):
            topic = self._upsert_topic(scored)
            plans.append(ContentPlan(
                topic=topic,
                content_format=scored.content_format,
                scheduled_at=slot,
                priority=i,
            ))
        return plans

    def _best_hours(self) -> list[int]:
        records = (
            self.db.query(LearningRecord)
            .filter(LearningRecord.page_id == self.page_id)
            .order_by(LearningRecord.performance_score.desc())
            .limit(100)
            .all()
        )
        if not records:
            return _BEST_HOURS_DEFAULT
        hour_scores: dict[int, list[float]] = {}
        for r in records:
            h = r.publish_hour
            hour_scores.setdefault(h, []).append(r.performance_score)
        ranked = sorted(hour_scores, key=lambda h: sum(hour_scores[h]) / len(hour_scores[h]), reverse=True)
        return ranked[:4] or _BEST_HOURS_DEFAULT

    def _generate_slots(self, posts_per_day: int, days: int, hours: list[int]) -> list[datetime]:
        now = datetime.now(timezone.utc)
        slots: list[datetime] = []
        for d in range(days):
            base = now + timedelta(days=d)
            for i in range(posts_per_day):
                h = hours[i % len(hours)]
                slot = base.replace(hour=h, minute=0, second=0, microsecond=0)
                if slot > now:
                    slots.append(slot)
        return slots

    def _upsert_topic(self, scored: ScoredTopic) -> TrendTopic:
        existing = (
            self.db.query(TrendTopic)
            .filter(
                TrendTopic.page_id == self.page_id,
                TrendTopic.title == scored.topic.title[:500],
            )
            .first()
        )
        if existing:
            existing.trend_score = scored.trend_score
            existing.freshness_score = scored.freshness_score
            existing.audience_match_score = scored.audience_match_score
            existing.total_score = scored.total_score
            existing.content_format = scored.content_format
            self.db.flush()
            return existing

        topic = TrendTopic(
            page_id=self.page_id,
            title=scored.topic.title[:500],
            summary=scored.topic.summary[:1000] if scored.topic.summary else None,
            source_url=scored.topic.source_url,
            source_type=scored.topic.source_type,
            category=scored.topic.category,
            language="en",
            trend_score=scored.trend_score,
            freshness_score=scored.freshness_score,
            audience_match_score=scored.audience_match_score,
            total_score=scored.total_score,
            status="new",
            content_format=scored.content_format,
        )
        self.db.add(topic)
        self.db.flush()
        return topic
