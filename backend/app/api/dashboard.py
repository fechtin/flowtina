"""Dashboard, reports, settings, logs and health endpoints."""

from __future__ import annotations

import os
import time

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.repositories.repositories import (
    SystemLogRepository,
    UserSettingsRepository,
)
from app.schemas.common import ok
from app.schemas.content import PostOut, SettingsOut, SettingsUpdate
from app.scheduler.manager import scheduler_manager
from app.services.dashboard_service import DashboardService, ReportService

router = APIRouter(tags=["dashboard"])
_PROCESS = psutil.Process(os.getpid())


@router.get("/projects/{project_id}/dashboard/stats")
def dashboard_stats(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    return ok(DashboardService(db).stats(project.id).model_dump())


@router.get("/projects/{project_id}/dashboard/charts")
def dashboard_charts(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    return ok(DashboardService(db).charts(project.id))


@router.get("/projects/{project_id}/dashboard/recent-posts")
def recent_posts(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = DashboardService(db).recent_posts(project.id)
    return ok([PostOut.model_validate(p).model_dump() for p in items])


@router.post("/projects/{project_id}/reports/generate")
def generate_report(
    type_: str = "daily",
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    content = ReportService(db).generate(project.id, type_)
    return ok({"content": content}, "Report generated")


# --- Settings ---


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = UserSettingsRepository(db)
    settings_row = repo.get_by(user_id=user.id) or repo.create(user_id=user.id)
    db.commit()
    return ok(SettingsOut.model_validate(settings_row).model_dump())


@router.put("/settings")
def update_settings(
    payload: SettingsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    repo = UserSettingsRepository(db)
    settings_row = repo.get_by(user_id=user.id) or repo.create(user_id=user.id)
    repo.update(settings_row, **payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(settings_row)
    return ok(SettingsOut.model_validate(settings_row).model_dump(), "Settings updated")


# --- Logs ---


@router.get("/logs")
def list_logs(
    level: str | None = None,
    module: str | None = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = SystemLogRepository(db).list_filtered(level=level, module=module, limit=limit)
    return ok(
        [
            {
                "id": log.id,
                "level": log.level,
                "module": log.module,
                "message": log.message,
                "created_at": log.created_at,
            }
            for log in items
        ]
    )


# --- Health ---


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    mem_mb = round(_PROCESS.memory_info().rss / (1024 * 1024), 1)
    return {
        "success": True,
        "data": {
            "database": "ok" if db_ok else "error",
            "scheduler": "ok" if scheduler_manager._scheduler and scheduler_manager._scheduler.running else "stopped",
            "memory_mb": mem_mb,
            "cpu_percent": _PROCESS.cpu_percent(interval=0.0),
            "timestamp": int(time.time()),
        },
    }
