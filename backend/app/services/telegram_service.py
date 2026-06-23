"""Telegram bot integration for reports and alerts (Bot API only)."""

from __future__ import annotations

import hashlib
import time

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundException, TelegramException
from app.core.logger import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.models.integration import TelegramConfig
from app.models.post import Post
from app.repositories.repositories import (
    PostRepository,
    ProjectRepository,
    TelegramConfigRepository,
    TelegramLogRepository,
    UserSettingsRepository,
)
from app.schemas.content import TelegramConfigIn
from app.utils.retry import retry_async

log = get_logger("telegram")

TELEGRAM_API = "https://api.telegram.org"


class TelegramService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.configs = TelegramConfigRepository(db)
        self.logs = TelegramLogRepository(db)

    def get_config(self, project_id: str) -> TelegramConfig | None:
        return self.configs.get_for_project(project_id)

    def _resolve(self, project_id: str) -> tuple[str, str] | None:
        """Effective (bot_token, chat_id): project config first, else global fallback.

        Returns None when neither the project nor the owner's global settings have an
        enabled Telegram bot configured.
        """
        config = self.configs.get_for_project(project_id)
        if config:
            return decrypt_secret(config.bot_token_encrypted), config.chat_id
        project = ProjectRepository(self.db).get(project_id)
        if not project:
            return None
        prefs = UserSettingsRepository(self.db).get_by(user_id=project.user_id)
        if (
            prefs
            and prefs.telegram_enabled
            and prefs.telegram_bot_token_encrypted
            and prefs.telegram_chat_id
        ):
            return decrypt_secret(prefs.telegram_bot_token_encrypted), prefs.telegram_chat_id
        return None

    def upsert_config(self, project_id: str, payload: TelegramConfigIn) -> TelegramConfig:
        existing = self.configs.get_by(project_id=project_id)
        if existing:
            existing.bot_token_encrypted = encrypt_secret(payload.bot_token)
            existing.chat_id = payload.chat_id
            existing.enabled = payload.enabled
            config = existing
        else:
            config = self.configs.create(
                project_id=project_id,
                bot_token_encrypted=encrypt_secret(payload.bot_token),
                chat_id=payload.chat_id,
                enabled=payload.enabled,
            )
        self.db.commit()
        self.db.refresh(config)
        return config

    async def send(self, project_id: str, message: str, *, type_: str = "manual") -> bool:
        resolved = self._resolve(project_id)
        if not resolved:
            raise NotFoundException("Telegram is not configured for this project")
        token, chat_id = resolved
        return await self._deliver(project_id, token, chat_id, message, type_)

    @staticmethod
    def webhook_secret() -> str:
        """Shared secret Telegram echoes in X-Telegram-Bot-Api-Secret-Token."""
        if settings.telegram_webhook_secret:
            return settings.telegram_webhook_secret
        return hashlib.sha256(f"tg-webhook:{settings.jwt_secret}".encode()).hexdigest()[:48]

    async def set_webhook(self, project_id: str) -> bool:
        """Register the approval webhook with Telegram for this project's bot."""
        resolved = self._resolve(project_id)
        if not resolved:
            raise NotFoundException("Telegram is not configured for this project")
        if not settings.public_base_url:
            log.warning("public_base_url not set; cannot register Telegram webhook")
            return False
        token, _ = resolved
        url = f"{TELEGRAM_API}/bot{token}/setWebhook"
        payload = {
            "url": f"{settings.public_base_url.rstrip('/')}/api/v1/telegram/webhook",
            "secret_token": self.webhook_secret(),
            "allowed_updates": ["callback_query"],
        }
        try:
            await self._post(url, payload)
            log.info(f"Telegram webhook registered for project {project_id}")
            return True
        except Exception as exc:  # noqa: BLE001 - non-fatal
            log.warning(f"setWebhook failed: {exc}")
            return False

    async def send_approval_request(self, project_id: str, post: Post, page_name: str) -> bool:
        """Send a post for approval with inline Approve/Reject buttons."""
        resolved = self._resolve(project_id)
        if not resolved:
            raise NotFoundException("Telegram is not configured for this project")
        token, chat_id = resolved
        preview = post.content if len(post.content) <= 600 else post.content[:600] + "…"
        message = (
            "📝 *Approval needed*\n\n"
            f"*Page:* {page_name}\n"
            f"*Title:* {post.title or '(none)'}\n\n"
            f"{preview}\n\n"
            f"{post.hashtags or ''}"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve:{post.id}"},
                    {"text": "❌ Reject", "callback_data": f"reject:{post.id}"},
                ]
            ]
        }
        return await self._deliver(
            project_id,
            token,
            chat_id,
            message,
            "approval_request",
            reply_markup=reply_markup,
        )

    async def handle_callback(self, update: dict) -> None:
        """Process an approve/reject inline-button callback from Telegram."""
        callback = update.get("callback_query")
        if not callback:
            return
        action, _, post_id = str(callback.get("data", "")).partition(":")
        if action not in {"approve", "reject"} or not post_id:
            return

        post = PostRepository(self.db).get(post_id)
        if not post:
            return
        resolved = self._resolve(post.project_id)
        if not resolved:
            return
        token, _ = resolved
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        message_id = message.get("message_id")

        if post.status != "pending_approval":
            await self._answer(token, callback.get("id"), "Already processed")
            return

        if action == "reject":
            post.status = "archived"
            self.db.commit()
            await self._answer(token, callback.get("id"), "Rejected")
            await self._edit(token, chat_id, message_id, "❌ *Rejected* — post archived.")
            return

        # Approve -> publish to the page recorded on the post.
        await self._answer(token, callback.get("id"), "Publishing…")
        from app.services.facebook_service import FacebookService

        try:
            await FacebookService(self.db).publish(post.id, post.facebook_page_id or "")
            await self._edit(token, chat_id, message_id, "✅ *Approved* — published to Facebook.")
        except Exception as exc:  # noqa: BLE001 - report failure back to the chat
            await self._edit(token, chat_id, message_id, f"⚠️ Publish failed: {str(exc)[:200]}")

    async def _answer(self, token: str, callback_id: str | None, text: str) -> None:
        if not callback_id:
            return
        url = f"{TELEGRAM_API}/bot{token}/answerCallbackQuery"
        try:
            await self._post(url, {"callback_query_id": callback_id, "text": text})
        except Exception:  # noqa: BLE001 - best effort
            pass

    async def _edit(self, token: str, chat_id, message_id, text: str) -> None:  # noqa: ANN001
        if chat_id is None or message_id is None:
            return
        url = f"{TELEGRAM_API}/bot{token}/editMessageText"
        try:
            await self._post(
                url,
                {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"},
            )
        except Exception:  # noqa: BLE001 - best effort
            pass

    async def _deliver(
        self,
        project_id: str,
        token: str,
        chat_id: str,
        message: str,
        type_: str,
        reply_markup: dict | None = None,
    ) -> bool:
        url = f"{TELEGRAM_API}/bot{token}/sendMessage"
        payload: dict = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        start = time.perf_counter()
        try:
            await retry_async(lambda: self._post(url, payload), attempts=3)
            duration = int((time.perf_counter() - start) * 1000)
            self.logs.create(
                project_id=project_id, type=type_, message=message[:2000],
                status="sent", duration_ms=duration,
            )
            self.db.commit()
            return True
        except Exception as exc:  # noqa: BLE001 - telegram failures are non-fatal
            self.logs.create(
                project_id=project_id, type=type_, message=message[:2000],
                status="failed", error_message=str(exc)[:500],
            )
            self.db.commit()
            log.warning(f"Telegram send failed: {exc}")
            return False

    @staticmethod
    async def _post(url: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            raise TelegramException(f"Telegram HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()
