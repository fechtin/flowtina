"""Video Job Queue: APScheduler-based async job queue for video generation.

Uses the existing APScheduler instance — no Redis, no Celery.
Jobs are picked from the DB by the scheduler poller.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.video.models import VideoJob

log = get_logger("video.queue")


class VideoJobQueue:
    """Poll pending video jobs and dispatch them for processing."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def next_pending(self) -> VideoJob | None:
        return (
            self.db.query(VideoJob)
            .filter(VideoJob.status.in_(["pending", "waiting_gpu"]))
            .filter(VideoJob.deleted_at.is_(None))
            .order_by(VideoJob.created_at.asc())
            .first()
        )

    def pending_count(self) -> int:
        return (
            self.db.query(VideoJob)
            .filter(VideoJob.status.in_(["pending", "waiting_gpu"]))
            .count()
        )

    async def tick(self) -> None:
        """Called by the APScheduler job on each tick."""
        from app.video.service import VideoService

        job = self.next_pending()
        if not job:
            return
        log.info(f"Video queue tick: dispatching job {job.id}")
        svc = VideoService(self.db)
        try:
            await svc.process_job(job.id)
        except Exception as exc:
            log.error(f"Video queue dispatch error for job {job.id}: {exc}")


def register_video_queue_job(scheduler, db_session_factory) -> None:
    """Register the video queue poller with the APScheduler instance."""
    from apscheduler.triggers.interval import IntervalTrigger

    async def _tick():
        with db_session_factory() as db:
            queue = VideoJobQueue(db)
            await queue.tick()

            from app.video.service import VideoService
            svc = VideoService(db)
            await svc.cleanup_idle_gpus()

    scheduler.add_job(
        _tick,
        trigger=IntervalTrigger(seconds=30),
        id="video_queue_poller",
        replace_existing=True,
        name="Video Queue Poller",
    )
    log.info("Video queue poller registered (30s interval)")
