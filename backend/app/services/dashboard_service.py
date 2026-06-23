"""Dashboard statistics and report generation/sending."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.repositories import (
    AIUsageLogRepository,
    FacebookPageRepository,
    PostRepository,
    ReportRepository,
    SchedulerJobRepository,
)
from app.schemas.content import DashboardStats


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.posts = PostRepository(db)
        self.usage = AIUsageLogRepository(db)
        self.pages = FacebookPageRepository(db)
        self.jobs = SchedulerJobRepository(db)

    def stats(self, project_id: str) -> DashboardStats:
        today = _start_of_today()
        posts_today = self.posts.count_since(project_id, today)
        published_today = self.posts.count_since(project_id, today, status="published")
        failed_today = self.posts.count_since(project_id, today, status="failed")
        total_posts = self.posts.count(project_id=project_id)
        tokens, cost = self.usage.totals(project_id)
        denom = published_today + failed_today
        success_rate = round((published_today / denom) * 100, 1) if denom else 0.0
        return DashboardStats(
            posts_today=posts_today,
            published_today=published_today,
            failed_today=failed_today,
            success_rate=success_rate,
            total_posts=total_posts,
            total_tokens=tokens,
            total_cost=round(cost, 4),
            facebook_pages=self.pages.count(project_id=project_id),
            active_jobs=self.jobs.count(project_id=project_id, enabled=True),
        )

    def charts(self, project_id: str, days: int = 7) -> dict:
        """Posts-per-day series for the last ``days`` days."""
        labels: list[str] = []
        values: list[int] = []
        for offset in range(days - 1, -1, -1):
            day = _start_of_today() - timedelta(days=offset)
            next_day = day + timedelta(days=1)
            count = self.posts.count_since(project_id, day) - self.posts.count_since(
                project_id, next_day
            )
            labels.append(day.strftime("%m-%d"))
            values.append(max(0, count))
        return {"labels": labels, "posts": values}

    def recent_posts(self, project_id: str, limit: int = 10) -> list:
        return self.posts.list(project_id=project_id, limit=limit)


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reports = ReportRepository(db)
        self.dashboard = DashboardService(db)

    def generate(self, project_id: str, type_: str = "daily") -> str:
        stats = self.dashboard.stats(project_id)
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(type_, 1)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=period_days)
        content = (
            f"📊 *{type_.title()} Report*\n\n"
            f"Generated Posts: {stats.posts_today}\n"
            f"Published Posts: {stats.published_today}\n"
            f"Failed Posts: {stats.failed_today}\n"
            f"Success Rate: {stats.success_rate}%\n"
            f"Token Usage: {stats.total_tokens}\n"
            f"AI Cost: ${stats.total_cost}\n"
        )
        self.reports.create(
            project_id=project_id, type=type_, period_start=start, period_end=end, content=content
        )
        self.db.commit()
        return content
