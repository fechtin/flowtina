"""Scheduler job CRUD that keeps the DB and APScheduler in sync."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.post import SchedulerJob
from app.repositories.repositories import (
    FacebookPageRepository,
    SchedulerHistoryRepository,
    SchedulerJobRepository,
)
from app.schemas.content import JobCreate, JobUpdate
from app.scheduler.manager import scheduler_manager


class SchedulerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = SchedulerJobRepository(db)
        self.history = SchedulerHistoryRepository(db)
        self.pages = FacebookPageRepository(db)

    def _validate_page(self, project_id: str, page_id: str | None) -> None:
        """Ensure a chosen Facebook page exists and belongs to the project."""
        if not page_id:
            return
        page = self.pages.get(page_id)
        if not page or page.project_id != project_id:
            raise ValidationException("Selected Facebook page does not belong to this project")

    def list(self, project_id: str) -> list[SchedulerJob]:
        return self.jobs.list(project_id=project_id)

    def get(self, job_id: str) -> SchedulerJob:
        job = self.jobs.get(job_id)
        if not job:
            raise NotFoundException("Job not found")
        return job

    def create(self, project_id: str, payload: JobCreate) -> SchedulerJob:
        self._validate_page(project_id, payload.facebook_page_id)
        job = self.jobs.create(project_id=project_id, **payload.model_dump())
        self.db.commit()
        self.db.refresh(job)
        self._sync(job)
        return job

    def update(self, job_id: str, payload: JobUpdate) -> SchedulerJob:
        job = self.get(job_id)
        self._validate_page(job.project_id, payload.facebook_page_id)
        self.jobs.update(job, **payload.model_dump(exclude_none=True))
        self.db.commit()
        self.db.refresh(job)
        self._sync(job)
        return job

    def delete(self, job_id: str) -> None:
        job = self.get(job_id)
        self.jobs.soft_delete(job)
        self.db.commit()
        scheduler_manager.remove(job_id)

    def run_now(self, job_id: str) -> None:
        job = self.get(job_id)
        scheduler_manager.run_now(job.id)

    def history_for(self, job_id: str, limit: int = 50) -> list:
        return self.history.list(job_id=job_id, limit=limit)

    def _sync(self, job: SchedulerJob) -> None:
        try:
            scheduler_manager.add_or_update(job)
            refreshed = scheduler_manager.scheduler.get_job(job.id)
            if refreshed and refreshed.next_run_time:
                job.next_run_at = refreshed.next_run_time
                self.db.commit()
        except Exception:  # noqa: BLE001 - scheduler may be disabled in some contexts
            pass
