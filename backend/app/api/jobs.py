"""Scheduler job endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.common import ok
from app.schemas.content import JobCreate, JobHistoryOut, JobOut, JobUpdate
from app.services.scheduler_service import SchedulerService

router = APIRouter(tags=["jobs"])


@router.get("/projects/{project_id}/jobs")
def list_jobs(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = SchedulerService(db).list(project.id)
    return ok([JobOut.model_validate(j).model_dump() for j in items])


@router.post("/projects/{project_id}/jobs")
def create_job(
    payload: JobCreate, project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
):
    job = SchedulerService(db).create(project.id, payload)
    return ok(JobOut.model_validate(job).model_dump(), "Job created")


@router.put("/jobs/{job_id}")
def update_job(
    job_id: str,
    payload: JobUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = SchedulerService(db).update(job_id, payload)
    return ok(JobOut.model_validate(job).model_dump(), "Job updated")


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    SchedulerService(db).delete(job_id)
    return ok(message="Job deleted")


@router.post("/jobs/{job_id}/run")
def run_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    SchedulerService(db).run_now(job_id)
    return ok(message="Job executed")


@router.get("/jobs/{job_id}/history")
def job_history(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = SchedulerService(db).history_for(job_id)
    return ok([JobHistoryOut.model_validate(h).model_dump() for h in items])
