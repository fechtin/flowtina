"""Video Generation Engine API endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.repositories import ProjectRepository
from app.video.models import VideoJob
from app.video.schemas import (
    GPUInstanceOut,
    VideoJobCreate,
    VideoJobOut,
    VideoPageConfigBase,
    VideoPageConfigOut,
)
from app.video.service import VideoService

router = APIRouter(prefix="/video", tags=["video"])


def _get_service(db: Session = Depends(get_db)) -> VideoService:
    return VideoService(db)


def _check_page_access(page_id: str, user: User, db: Session) -> None:
    from app.models.integration import FacebookPage
    page = db.query(FacebookPage).filter_by(id=page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    project = ProjectRepository(db).get(page.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


# ---- Page Config ----

@router.get("/pages/{page_id}/config", response_model=VideoPageConfigOut)
def get_video_config(
    page_id: str,
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _check_page_access(page_id, user, db)
    cfg = svc.get_page_config(page_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    return cfg


@router.put("/pages/{page_id}/config", response_model=VideoPageConfigOut)
def upsert_video_config(
    page_id: str,
    body: VideoPageConfigBase,
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _check_page_access(page_id, user, db)
    return svc.upsert_page_config(page_id, body.model_dump(exclude_none=True))


# ---- Jobs ----

@router.post("/jobs", response_model=VideoJobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    body: VideoJobCreate,
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _check_page_access(body.page_id, user, db)
    job = svc.create_job(body.model_dump())
    return job


@router.get("/jobs/{job_id}", response_model=VideoJobOut)
def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    job = svc.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _check_page_access(job.page_id, user, db)
    return job


@router.get("/pages/{page_id}/jobs", response_model=list[VideoJobOut])
def list_jobs(
    page_id: str,
    limit: int = 50,
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    _check_page_access(page_id, user, db)
    return svc.list_jobs(page_id, limit=limit)


@router.post("/jobs/{job_id}/cancel", response_model=VideoJobOut)
def cancel_job(
    job_id: str,
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
    db: Session = Depends(get_db),
):
    job = svc.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _check_page_access(job.page_id, user, db)
    cancelled = svc.cancel_job(job_id)
    return cancelled


# ---- GPU Instances (admin view) ----

@router.get("/gpu/instances", response_model=list[GPUInstanceOut])
def list_gpu_instances(
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
):
    return svc.list_gpu_instances()


@router.post("/gpu/cleanup")
async def cleanup_idle_gpus(
    user: User = Depends(get_current_user),
    svc: VideoService = Depends(_get_service),
):
    count = await svc.cleanup_idle_gpus()
    return {"destroyed": count}
