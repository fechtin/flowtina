"""Messenger direct-message auto-reply (Graph API only, webhook-driven).

Meta delivers each incoming DM to our webhook; we generate an AI reply that is
personalized from the follower's long-term memory and send it back via the Send
API. The same per-follower memory scope as comments is reused, keyed by the
sender's page-scoped id (PSID) with ``channel="messenger"``.
"""

from __future__ import annotations

import hashlib
import hmac

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.core.security import decrypt_secret
from app.models.integration import FacebookPage
from app.models.memory import CHANNEL_MESSENGER, Conversation
from app.prompts.defaults import (
    DEFAULT_DM_REPLY_PROMPT,
    DEFAULT_DM_REPLY_WITH_MEMORY_PROMPT,
)
from app.prompts.engine import prompt_engine
from app.repositories.repositories import FacebookPageRepository
from app.services.ai_service import AIService
from app.services.facebook_service import GRAPH_API
from app.services.memory.service import MemoryService
from app.utils.text import strip_markdown

log = get_logger("facebook")

# Messenger hard limit on a single text message.
_MAX_MESSAGE_CHARS = 2000


class MessengerService:
    """Reply to Messenger DMs with memory-aware, human-like messages."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.pages = FacebookPageRepository(db)
        self.ai = AIService(db)
        self.memory = MemoryService(db) if settings.memory_enabled else None

    # --- webhook auth ---

    @staticmethod
    def verify_token() -> str:
        return settings.messenger_verify_token

    @staticmethod
    def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
        """Validate Meta's ``X-Hub-Signature-256`` HMAC over the raw request body.

        When no app secret is configured the check is skipped (self-host/dev),
        matching how the rest of the app treats optional Facebook credentials.
        """
        secret = settings.facebook_app_secret
        if not secret:
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header.split("=", 1)[1])

    # --- event handling ---

    async def handle_event(self, payload: dict) -> int:
        """Process a webhook payload; returns the number of replies sent."""
        sent = 0
        for entry in payload.get("entry", []) or []:
            page = self.pages.get_by_fb_page_id(str(entry.get("id", "")))
            if not page or not page.enabled or not page.auto_reply_messages:
                continue
            for event in entry.get("messaging", []) or []:
                try:
                    if await self._process_event(page, event):
                        sent += 1
                except Exception as exc:  # noqa: BLE001 - one bad event must not abort the batch
                    log.warning(f"Messenger event failed on page {page.page_id}: {exc}")
        return sent

    async def _process_event(self, page: FacebookPage, event: dict) -> bool:
        sender_id = str((event.get("sender") or {}).get("id", ""))
        message = event.get("message") or {}
        text = (message.get("text") or "").strip()
        # Skip echoes of our own messages, delivery/read receipts and non-text.
        if message.get("is_echo") or not sender_id or not text:
            return False
        if sender_id == page.page_id:
            return False

        token = decrypt_secret(page.access_token_encrypted)
        reply, conversation = await self._build_reply(page, sender_id, text)
        if not reply:
            return False
        await self._send(sender_id, reply, token)
        if conversation is not None and self.memory is not None:
            await self.memory.record_exchange(conversation, text, reply)
        self.db.commit()
        return True

    # --- AI reply ---

    async def _build_reply(
        self, page: FacebookPage, sender_id: str, text: str
    ) -> tuple[str, Conversation | None]:
        persona = (
            f"Voice and guidance: {page.reply_persona}" if page.reply_persona else ""
        )
        if self.memory is None:
            prompt = prompt_engine.render(
                DEFAULT_DM_REPLY_PROMPT, {"persona": persona, "comment": text[:1500]}
            )
            result = await self.ai.generate(page.project_id, prompt)
            return self._clean(result.text), None

        conversation = self.memory.get_conversation(
            project_id=page.project_id,
            page_id=page.id,
            channel=CHANNEL_MESSENGER,
            external_user_id=sender_id,
        )
        context = await self.memory.build_context(conversation, text)
        prompt = prompt_engine.render(
            DEFAULT_DM_REPLY_WITH_MEMORY_PROMPT,
            {
                "persona": persona,
                "user_name": conversation.user_name or "this follower",
                "memory_context": context["memory_context"],
                "history": context["history"],
                "comment": text[:1500],
            },
        )
        result = await self.ai.generate(page.project_id, prompt)
        return self._clean(result.text), conversation

    @staticmethod
    def _clean(text: str) -> str:
        return strip_markdown(text).strip()[:_MAX_MESSAGE_CHARS]

    # --- Send API ---

    async def _send(self, recipient_id: str, message: str, token: str) -> None:
        url = f"{GRAPH_API}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": message},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params={"access_token": token}, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Send API HTTP {resp.status_code}: {resp.text[:300]}")
