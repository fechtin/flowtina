"""APScheduler manager with an in-memory job store.

Single background scheduler, no Redis/Celery. The jobstore is in-memory rather
than SQLite: the scheduler runs in its own process and a shared SQLite jobstore
caused write contention that could lock the DB and kill the scheduler loop.
Jobs are the source of truth in the ``scheduler_jobs`` table; the scheduler
reconciles them into its store on startup and periodically, so they survive
restarts and reflect API edits without a shared jobstore.
"""

from __future__ import annotations

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal
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
        jobstores = {"default": MemoryJobStore()}
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
        # The jobstore is in-memory and not shared, so only the scheduler process
        # (where it is enabled and running) owns jobs. In the API process this is a
        # no-op; the scheduler picks up DB changes on its next reconcile.
        if not settings.scheduler_enabled:
            return
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
        if not settings.scheduler_enabled:
            return
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    def run_now(self, job_id: str) -> None:
        task_jobs.run_generate_content(job_id)

    def sync_db_jobs(self) -> None:
        """Reconcile DB-defined jobs into the scheduler's in-memory store.

        Adds/updates every enabled job, removes any user job that was disabled or
        deleted since the last pass, and refreshes ``next_run_at`` for display.
        Runs on startup and on ``scheduler_resync_seconds`` so API edits take
        effect without restarting the scheduler.
        """
        db = SessionLocal()
        try:
            enabled = SchedulerJobRepository(db).list_enabled()
            enabled_ids = {job.id for job in enabled}
            for job in enabled:
                self.add_or_update(job)
                scheduled = self.scheduler.get_job(job.id)
                next_run = getattr(scheduled, "next_run_time", None) if scheduled else None
                if next_run and job.next_run_at != next_run:
                    job.next_run_at = next_run
            db.commit()
            # Drop user jobs that are no longer enabled (maintenance jobs are kept).
            for existing in self.scheduler.get_jobs():
                if not existing.id.startswith("maintenance_") and existing.id not in enabled_ids:
                    self.remove(existing.id)
        finally:
            db.close()

    def _register_maintenance_jobs(self) -> None:
        self.scheduler.add_job(
            self.sync_db_jobs,
            trigger=IntervalTrigger(seconds=settings.scheduler_resync_seconds),
            id="maintenance_resync_jobs",
            replace_existing=True,
        )
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
        self.scheduler.add_job(
            task_jobs.process_messenger_inbox,
            trigger=IntervalTrigger(seconds=settings.messenger_inbox_tick_seconds),
            id="maintenance_process_messenger_inbox",
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
