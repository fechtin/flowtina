"""Messenger direct-message auto-reply (Graph API only, webhook-driven).

Meta delivers each incoming DM to our webhook; we generate an AI reply that is
personalized from the follower's long-term memory and send it back via the Send
API. The same per-follower memory scope as comments is reused, keyed by the
sender's page-scoped id (PSID) with ``channel="messenger"``.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.core.security import decrypt_secret
from app.models.integration import FacebookPage, MessengerEvent
from app.models.memory import CHANNEL_IG_MESSAGE, CHANNEL_MESSENGER, Conversation
from app.prompts.defaults import (
    DEFAULT_DM_REPLY_PROMPT,
    DEFAULT_DM_REPLY_WITH_MEMORY_PROMPT,
)
from app.prompts.engine import prompt_engine
from app.repositories.repositories import (
    FacebookPageRepository,
    MessengerEventRepository,
)
from app.services.ai_service import AIService
from app.services.facebook_service import GRAPH_API
from app.services.memory.service import MemoryService
from app.utils.text import strip_markdown

log = get_logger("facebook")

# Messenger hard limit on a single text message.
_MAX_MESSAGE_CHARS = 2000
# Cap on stored inbound text so a huge paste cannot bloat the queue.
_MAX_INBOUND_CHARS = 4000


def _as_utc(value: datetime) -> datetime:
    """Treat a stored (possibly tz-naive, from SQLite) timestamp as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class MessengerService:
    """Reply to Messenger DMs with memory-aware, human-like messages."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.pages = FacebookPageRepository(db)
        self.events = MessengerEventRepository(db)
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

    # --- enqueue (webhook path, fast) ---

    def enqueue_event(self, payload: dict) -> int:
        """Persist each inbound DM and return immediately; replies are sent later.

        Handles both Facebook Messenger (``object == "page"``) and Instagram
        (``object == "instagram"``) webhooks: the two share the same envelope but
        Instagram keys ``entry.id`` by the IG account id and is gated by a
        separate per-page toggle. The webhook must answer Meta within seconds, so
        this does no AI/network work — just dedupe-and-store. The inbox poller
        generates and sends the replies out of band (see :meth:`process_inbox`).
        """
        is_instagram = payload.get("object") == "instagram"
        channel = CHANNEL_IG_MESSAGE if is_instagram else CHANNEL_MESSENGER
        queued = 0
        for entry in payload.get("entry", []) or []:
            entry_id = str(entry.get("id", ""))
            if is_instagram:
                page = self.pages.get_by_instagram_user_id(entry_id)
                enabled = bool(page and page.enabled and page.auto_reply_ig_messages)
                self_id = page.instagram_user_id if page else None
            else:
                page = self.pages.get_by_fb_page_id(entry_id)
                enabled = bool(page and page.enabled and page.auto_reply_messages)
                self_id = page.page_id if page else None
            if not page or not enabled:
                continue
            for event in entry.get("messaging", []) or []:
                if self._enqueue_one(page, event, channel, self_id):
                    queued += 1
        if queued:
            self.db.commit()
        return queued

    def _enqueue_one(
        self, page: FacebookPage, event: dict, channel: str, self_id: str | None
    ) -> bool:
        sender_id = str((event.get("sender") or {}).get("id", ""))
        message = event.get("message") or {}
        text = (message.get("text") or "").strip()
        # Skip echoes of our own messages, delivery/read receipts and non-text.
        if message.get("is_echo") or not sender_id or not text:
            return False
        if self_id and sender_id == self_id:
            return False
        mid = message.get("mid")
        # Meta retries webhook delivery on slow responses; the unique mid makes
        # re-delivery a no-op so a follower is never answered twice.
        if mid and self.events.exists_by_mid(str(mid)):
            return False
        self.events.create(
            page_id=page.id,
            channel=channel,
            sender_id=sender_id,
            mid=str(mid) if mid else None,
            text=text[:_MAX_INBOUND_CHARS],
        )
        return True

    # --- inbox poller (background reply path) ---

    async def process_inbox(self) -> int:
        """Reply to queued DMs that have settled, coalescing per follower.

        Returns the number of followers replied to this run. A follower's
        messages are held until they pause for ``messenger_debounce_seconds`` so
        rapid-fire lines become one in-context reply; messages whose previous
        send failed are retried regardless of the debounce window.
        """
        pending = self.events.list_pending()
        if not pending:
            return 0
        groups: dict[tuple[str, str], list[MessengerEvent]] = {}
        for ev in pending:
            groups.setdefault((ev.page_id, ev.sender_id), []).append(ev)

        now = datetime.now(timezone.utc)
        debounce = timedelta(seconds=settings.messenger_debounce_seconds)
        sent = 0
        for (page_id, sender_id), events in groups.items():
            newest = max(_as_utc(ev.created_at) for ev in events)
            retrying = any(ev.attempts > 0 for ev in events)
            if not retrying and (now - newest) < debounce:
                continue  # follower may still be typing — wait for the next tick
            if await self._reply_to_group(page_id, sender_id, events):
                sent += 1
        return sent

    async def _reply_to_group(
        self, page_id: str, sender_id: str, events: list[MessengerEvent]
    ) -> bool:
        page = self.pages.get(page_id)
        channel = events[0].channel or CHANNEL_MESSENGER
        is_instagram = channel == CHANNEL_IG_MESSAGE
        enabled = page and page.enabled and (
            page.auto_reply_ig_messages if is_instagram else page.auto_reply_messages
        )
        if not page or not enabled:
            # Page was removed or auto-reply turned off after queueing: drop these.
            self._finish(events, "processed")
            self.db.commit()
            return False

        ordered = sorted(events, key=lambda e: _as_utc(e.created_at))
        combined = "\n".join(e.text for e in ordered[: settings.messenger_coalesce_max])
        token = decrypt_secret(page.access_token_encrypted)
        url = self._messages_url(page, is_instagram)
        try:
            # Acknowledge the follower so the bubble shows "Seen" + typing while we
            # generate; both are best-effort and never block the actual reply.
            await self._send_action(url, sender_id, "mark_seen", token)
            await self._send_action(url, sender_id, "typing_on", token)
            reply, conversation = await self._build_reply(
                page, sender_id, combined, channel
            )
            if reply:
                await self._send(url, sender_id, reply, token)
                if conversation is not None and self.memory is not None:
                    await self.memory.record_exchange(conversation, combined, reply)
            self._finish(events, "processed")
            self.db.commit()
            return bool(reply)
        except Exception as exc:  # noqa: BLE001 - retry/cap instead of losing the message
            self.db.rollback()
            self._fail(events, str(exc))
            self.db.commit()
            log.warning(
                f"Messenger reply failed (page {page.page_id}, sender {sender_id}): {exc}"
            )
            return False

    def _finish(self, events: list[MessengerEvent], status: str) -> None:
        now = datetime.now(timezone.utc)
        for ev in events:
            ev.status = status
            ev.processed_at = now

    def _fail(self, events: list[MessengerEvent], error: str) -> None:
        now = datetime.now(timezone.utc)
        for ev in events:
            ev.attempts += 1
            ev.error_message = error[:1000]
            if ev.attempts >= settings.messenger_max_attempts:
                ev.status = "failed"  # give up so it stops blocking the queue
                ev.processed_at = now

    # --- AI reply ---

    async def _build_reply(
        self, page: FacebookPage, sender_id: str, text: str, channel: str
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
            channel=channel,
            external_user_id=sender_id,
        )
        # First contact: use the plain prompt so the reply does not pretend to
        # remember a follower we have never talked to. The exchange is still
        # recorded (conversation returned) so memory builds up for next time.
        if not self.memory.has_context(conversation):
            prompt = prompt_engine.render(
                DEFAULT_DM_REPLY_PROMPT, {"persona": persona, "comment": text[:1500]}
            )
            result = await self.ai.generate(page.project_id, prompt)
            return self._clean(result.text), conversation

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

    @staticmethod
    def _messages_url(page: FacebookPage, is_instagram: bool) -> str:
        """Select the Send endpoint: Instagram posts to the IG account id.

        Both use the page access token; Facebook Messenger uses ``/me/messages``
        while Instagram messaging targets ``/{ig-user-id}/messages``.
        """
        if is_instagram:
            return f"{GRAPH_API}/{page.instagram_user_id}/messages"
        return f"{GRAPH_API}/me/messages"

    async def _send(self, url: str, recipient_id: str, message: str, token: str) -> None:
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": message},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params={"access_token": token}, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Send API HTTP {resp.status_code}: {resp.text[:300]}")

    async def _send_action(
        self, url: str, recipient_id: str, action: str, token: str
    ) -> None:
        """Send a sender_action (mark_seen / typing_on). Best-effort, never raises."""
        payload = {"recipient": {"id": recipient_id}, "sender_action": action}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, params={"access_token": token}, json=payload)
        except Exception as exc:  # noqa: BLE001 - cosmetic ack, must not block the reply
            log.debug(f"sender_action {action} failed for {recipient_id}: {exc}")
