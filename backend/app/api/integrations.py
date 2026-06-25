"""Facebook and Telegram integration endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.models.project import Project
from app.models.user import User
from app.schemas.common import ok
from app.schemas.content import (
    FacebookCommentOut,
    FacebookDiscoveredPage,
    FacebookEngagementUpdate,
    FacebookImportRequest,
    FacebookPageCreate,
    FacebookPageOut,
    TelegramConfigIn,
    TelegramConfigOut,
    TelegramTestRequest,
)
from app.services.facebook_engagement_service import FacebookEngagementService
from app.services.facebook_service import FacebookService
from app.services.messenger_service import MessengerService
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


@router.post("/projects/{project_id}/facebook/discover")
async def discover_pages(
    payload: FacebookImportRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    """List the Pages a token can manage so the operator can pick which to import."""
    pages = await FacebookService(db).discover_pages(project.id, payload.token)
    return ok(
        [FacebookDiscoveredPage.model_validate(p).model_dump() for p in pages],
        f"Found {len(pages)} page(s)",
    )


@router.post("/projects/{project_id}/facebook/import")
async def import_pages(
    payload: FacebookImportRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    """Auto-discover and connect the operator's Pages from a single token."""
    pages = await FacebookService(db).import_pages(project.id, payload.token, payload.page_ids)
    return ok(
        [FacebookPageOut.model_validate(p).model_dump() for p in pages],
        f"Imported {len(pages)} page(s)",
    )


@router.delete("/facebook/pages/{page_id}")
def delete_page(page_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    FacebookService(db).delete_page(page_id)
    return ok(message="Page disconnected")


@router.patch("/facebook/pages/{page_id}/engagement")
def update_engagement(
    page_id: str,
    payload: FacebookEngagementUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable/disable auto-like, comment auto-reply and Messenger auto-reply."""
    page = FacebookEngagementService(db).update_settings(
        page_id,
        auto_like_comments=payload.auto_like_comments,
        auto_reply_comments=payload.auto_reply_comments,
        auto_reply_messages=payload.auto_reply_messages,
        reply_persona=payload.reply_persona,
    )
    return ok(FacebookPageOut.model_validate(page).model_dump(), "Engagement updated")


@router.get("/facebook/pages/{page_id}/comments")
def list_comments(
    page_id: str,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List comments the engagement poller has seen on this page's posts."""
    comments = FacebookEngagementService(db).list_comments(page_id, limit=limit)
    return ok([FacebookCommentOut.model_validate(c).model_dump() for c in comments])


@router.post("/facebook/pages/{page_id}/engage-now")
async def engage_now(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the comment poll for one page immediately (manual trigger)."""
    svc = FacebookEngagementService(db)
    page = svc.pages.get(page_id)
    if not page:
        raise NotFoundException("Facebook page not found")
    result = await svc.engage_page(page)
    if result.get("error"):
        message = f"Could not read the page's posts. {str(result['error'])[:200]}"
    elif not result["scanned"]:
        message = "No recent posts found on this page to scan."
    else:
        message = f"Processed {result['processed']} new comment(s)"
    return ok(result, message)


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


@router.get("/messenger/webhook")
async def verify_messenger_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """Meta's one-time webhook verification handshake (GET challenge)."""
    if hub_mode == "subscribe" and hub_verify_token == MessengerService.verify_token():
        return PlainTextResponse(hub_challenge or "")
    return PlainTextResponse("forbidden", status_code=403)


@router.post("/messenger/webhook")
async def messenger_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
):
    """Public endpoint Meta calls with incoming Messenger events.

    Authenticated via the app-secret HMAC signature. Always returns 200 so Meta
    does not retry; processing errors are swallowed and logged.
    """
    raw = await request.body()
    if not MessengerService.verify_signature(raw, x_hub_signature_256):
        return {"status": "ok"}
    try:
        payload = json.loads(raw or b"{}")
        if payload.get("object") == "page":
            await MessengerService(db).handle_event(payload)
    except Exception:  # noqa: BLE001 - never surface errors to Meta
        pass
    return {"status": "ok"}


@router.post("/projects/{project_id}/telegram/test")
async def test_telegram(
    payload: TelegramTestRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    sent = await TelegramService(db).send(project.id, payload.message, type_="test")
    return ok({"sent": sent}, "Test message dispatched" if sent else "Send failed")
