"""Facebook and Telegram integration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.common import ok
from app.schemas.content import (
    FacebookPageCreate,
    FacebookPageOut,
    TelegramConfigIn,
    TelegramConfigOut,
    TelegramTestRequest,
)
from app.services.facebook_service import FacebookService
from app.services.telegram_service import TelegramService

router = APIRouter(tags=["integrations"])


# --- Facebook ---


@router.get("/projects/{project_id}/facebook/pages")
def list_pages(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    pages = FacebookService(db).list_pages(project.id)
    return ok([FacebookPageOut.model_validate(p).model_dump() for p in pages])


@router.post("/projects/{project_id}/facebook/pages")
def connect_page(
    payload: FacebookPageCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    page = FacebookService(db).connect_page(project.id, payload)
    return ok(FacebookPageOut.model_validate(page).model_dump(), "Page connected")


@router.delete("/facebook/pages/{page_id}")
def delete_page(page_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    FacebookService(db).delete_page(page_id)
    return ok(message="Page disconnected")


# --- Telegram ---


@router.get("/projects/{project_id}/telegram/config")
def get_telegram(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    config = TelegramService(db).get_config(project.id)
    if not config:
        return ok(None)
    return ok(TelegramConfigOut.model_validate(config).model_dump())


@router.post("/projects/{project_id}/telegram/config")
def set_telegram(
    payload: TelegramConfigIn,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    config = TelegramService(db).upsert_config(project.id, payload)
    return ok(TelegramConfigOut.model_validate(config).model_dump(), "Telegram configured")


@router.post("/projects/{project_id}/telegram/test")
async def test_telegram(
    payload: TelegramTestRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    sent = await TelegramService(db).send(project.id, payload.message, type_="test")
    return ok({"sent": sent}, "Test message dispatched" if sent else "Send failed")
