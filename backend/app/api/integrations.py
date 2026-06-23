"""Facebook and Telegram integration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.common import ok
from app.schemas.content import (
    FacebookImportRequest,
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


@router.post("/projects/{project_id}/facebook/import")
async def import_pages(
    payload: FacebookImportRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    """Auto-discover and connect the operator's Pages from a single token."""
    pages = await FacebookService(db).import_pages(project.id, payload.token)
    return ok(
        [FacebookPageOut.model_validate(p).model_dump() for p in pages],
        f"Imported {len(pages)} page(s)",
    )


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
async def set_telegram(
    payload: TelegramConfigIn,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    svc = TelegramService(db)
    config = svc.upsert_config(project.id, payload)
    # Best-effort: register the approval webhook if a public URL is configured.
    webhook_registered = await svc.set_webhook(project.id)
    data = TelegramConfigOut.model_validate(config).model_dump()
    data["webhook_registered"] = webhook_registered
    return ok(data, "Telegram configured")


@router.post("/projects/{project_id}/telegram/setup-webhook")
async def setup_telegram_webhook(
    project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
):
    registered = await TelegramService(db).set_webhook(project.id)
    return ok({"registered": registered}, "Webhook configured" if registered else "Webhook not set")


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Public endpoint Telegram calls for approve/reject button presses.

    Authenticated only via the shared secret token header; never exposes data.
    Always returns 200 so Telegram does not retry indefinitely.
    """
    if x_telegram_bot_api_secret_token != TelegramService.webhook_secret():
        return {"ok": True}
    try:
        update = await request.json()
        await TelegramService(db).handle_callback(update)
    except Exception:  # noqa: BLE001 - never surface errors to Telegram
        pass
    return {"ok": True}


@router.post("/projects/{project_id}/telegram/test")
async def test_telegram(
    payload: TelegramTestRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    sent = await TelegramService(db).send(project.id, payload.message, type_="test")
    return ok({"sent": sent}, "Test message dispatched" if sent else "Send failed")
