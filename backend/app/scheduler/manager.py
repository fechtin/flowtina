"""APScheduler manager with a persistent SQLite job store.

Single background scheduler, no Redis/Celery. Jobs persist across restarts so
missed jobs can run on recovery. Exposes helpers to sync DB-defined jobs into
APScheduler.
"""

from __future__ import annotations

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.logger import get_logger
from app.models.post import SchedulerJob
from app.repositories.repositories import SchedulerJobRepository
from app.tasks import jobs as task_jobs

log = get_logger("scheduler")

_TASK_MAP = {
    "generate_content": task_jobs.run_generate_content,
    "daily_report": task_jobs.send_daily_report,
    "cleanup_logs": task_jobs.cleanup_logs,
}


class SchedulerManager:
    """Owns the singleton APScheduler instance."""

    def __init__(self) -> None:
        self._scheduler: BackgroundScheduler | None = None

    @property
    def scheduler(self) -> BackgroundScheduler:
        if self._scheduler is None:
            self._scheduler = self._build()
        return self._scheduler

    def _build(self) -> BackgroundScheduler:
        jobstores = {"default": SQLAlchemyJobStore(engine=engine, tablename="apscheduler_jobs")}
        executors_conf = {"default": {"type": "threadpool", "max_workers": settings.scheduler_max_threads}}
        scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors_conf,
            job_defaults={"coalesce": True, "misfire_grace_time": 3600, "max_instances": 1},
            timezone="UTC",
        )
        return scheduler

    def start(self) -> None:
        if not settings.scheduler_enabled:
            log.info("Scheduler disabled by config")
            return
        if self.scheduler.running:
            return
        self.scheduler.start()
        self.sync_db_jobs()
        self._register_maintenance_jobs()
        log.info("Scheduler started")

    def shutdown(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            log.info("Scheduler stopped")

    def _trigger_for(self, job: SchedulerJob):
        if job.cron_expression:
            return CronTrigger.from_crontab(job.cron_expression, timezone=job.timezone or "UTC")
        if job.interval_seconds:
            return IntervalTrigger(seconds=job.interval_seconds)
        return IntervalTrigger(hours=6)  # sensible default

    def add_or_update(self, job: SchedulerJob) -> None:
        func = _TASK_MAP.get(job.job_type, task_jobs.run_generate_content)
        if not job.enabled:
            self.remove(job.id)
            return
        self.scheduler.add_job(
            func,
            trigger=self._trigger_for(job),
            id=job.id,
            args=[job.id] if job.job_type == "generate_content" else [job.project_id],
            replace_existing=True,
        )
        log.info(f"Scheduled job {job.id} ({job.job_type})")

    def remove(self, job_id: str) -> None:
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    def run_now(self, job_id: str) -> None:
        task_jobs.run_generate_content(job_id)

    def sync_db_jobs(self) -> None:
        """Load enabled jobs from the database into the scheduler."""
        db = SessionLocal()
        try:
            for job in SchedulerJobRepository(db).list_enabled():
                self.add_or_update(job)
        finally:
            db.close()

    def _register_maintenance_jobs(self) -> None:
        self.scheduler.add_job(
            task_jobs.cleanup_logs,
            trigger=CronTrigger.from_crontab("0 3 * * *", timezone="UTC"),
            id="maintenance_cleanup_logs",
            args=[settings.log_retention_days],
            replace_existing=True,
        )
        self.scheduler.add_job(
            task_jobs.engage_comments,
            trigger=IntervalTrigger(minutes=settings.facebook_engage_tick_minutes),
            id="maintenance_engage_comments",
            replace_existing=True,
        )
        if settings.memory_enabled:
            self.scheduler.add_job(
                task_jobs.consolidate_memories,
                trigger=CronTrigger.from_crontab(
                    settings.memory_consolidation_cron, timezone="UTC"
                ),
                id="maintenance_consolidate_memories",
                replace_existing=True,
            )


scheduler_manager = SchedulerManager()
