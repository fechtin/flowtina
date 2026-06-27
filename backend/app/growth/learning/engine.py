"""Learning Engine: record post performance and compute weights for future content.

Completely rule-based — no AI calls. Updates topic/hook/time scoring weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.growth.models import ContentDraft, LearningRecord

log = get_logger("growth.learning")


@dataclass
class PerformanceMetrics:
    reach: int = 0
    impressions: int = 0
    engagement: int = 0
    shares: int = 0
    followers_gained: int = 0
    watch_time_seconds: int = 0
    completion_rate: float = 0.0


def _compute_performance_score(m: PerformanceMetrics) -> float:
    if m.impressions == 0:
        return 0.0
    engagement_rate = m.engagement / m.impressions if m.impressions > 0 else 0
    share_rate = m.shares / m.impressions if m.impressions > 0 else 0
    score = (
        engagement_rate * 50
        + share_rate * 30
        + m.completion_rate * 10
        + min(m.followers_gained / 10, 1.0) * 10
    )
    return round(min(score * 100, 100.0), 2)


class LearningEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_performance(
        self,
        page_id: str,
        draft_id: str | None,
        metrics: PerformanceMetrics,
    ) -> LearningRecord:
        draft: ContentDraft | None = None
        if draft_id:
            draft = self.db.query(ContentDraft).filter_by(id=draft_id).first()

        score = _compute_performance_score(metrics)
        now = datetime.now(timezone.utc)

        record = LearningRecord(
            page_id=page_id,
            draft_id=draft_id,
            topic=draft.caption[:500] if draft and draft.caption else None,
            content_type=draft.content_type if draft else None,
            hook_pattern=self._extract_hook_pattern(draft.hook if draft else None),
            prompt_version=draft.prompt_version if draft else 1,
            model_used=draft.model_used if draft else None,
            publish_hour=now.hour,
            publish_day=now.weekday(),
            reach=metrics.reach,
            impressions=metrics.impressions,
            engagement=metrics.engagement,
            shares=metrics.shares,
            followers_gained=metrics.followers_gained,
            watch_time_seconds=metrics.watch_time_seconds,
            completion_rate=metrics.completion_rate,
            performance_score=score,
        )
        self.db.add(record)
        self.db.flush()
        log.info(f"Learning record created for page={page_id} score={score}")
        return record

    def get_best_content_types(self, page_id: str, limit: int = 5) -> list[dict]:
        records = (
            self.db.query(LearningRecord)
            .filter(LearningRecord.page_id == page_id)
            .all()
        )
        type_scores: dict[str, list[float]] = {}
        for r in records:
            if r.content_type:
                type_scores.setdefault(r.content_type, []).append(r.performance_score)
        result = [
            {"content_type": ct, "avg_score": sum(scores) / len(scores), "count": len(scores)}
            for ct, scores in type_scores.items()
        ]
        result.sort(key=lambda x: x["avg_score"], reverse=True)
        return result[:limit]

    def get_best_posting_times(self, page_id: str) -> dict[str, list[int]]:
        records = (
            self.db.query(LearningRecord)
            .filter(LearningRecord.page_id == page_id)
            .all()
        )
        hour_perf: dict[int, float] = {}
        day_perf: dict[int, float] = {}
        for r in records:
            if r.publish_hour is not None:
                hour_perf[r.publish_hour] = hour_perf.get(r.publish_hour, 0) + r.performance_score
            if r.publish_day is not None:
                day_perf[r.publish_day] = day_perf.get(r.publish_day, 0) + r.performance_score
        best_hours = sorted(hour_perf, key=hour_perf.get, reverse=True)[:4]  # type: ignore[arg-type]
        best_days = sorted(day_perf, key=day_perf.get, reverse=True)[:3]  # type: ignore[arg-type]
        return {"best_hours": best_hours, "best_days": best_days}

    @staticmethod
    def _extract_hook_pattern(hook: str | None) -> str | None:
        if not hook:
            return None
        import re
        if re.search(r"\b(you|your)\b", hook, re.I):
            return "you_focused"
        if re.search(r"^\d+", hook):
            return "numbered"
        if "?" in hook:
            return "question"
        if hook[0].islower() or re.match(r"^(how|what|why|when|where|who)\b", hook, re.I):
            return "question_word"
        return "statement"
