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
    DEFAULT_GENDER_INFERENCE_PROMPT,
)
from app.prompts.engine import prompt_engine
from app.repositories.repositories import (
    FacebookPageRepository,
    MessengerEventRepository,
    ProjectRepository,
    UserSettingsRepository,
)
from app.services.ai_service import AIService
from app.services.facebook_service import GRAPH_API
from app.services.memory.service import MemoryService
from app.services.vision_service import describe_image
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
        self._user_settings = UserSettingsRepository(db)
        self._projects = ProjectRepository(db)

    def _groq_api_key(self, project_id: str) -> str | None:
        """Resolve the owner's Groq API key from DB settings (same as AIService)."""
        project = self._projects.get(project_id)
        if not project:
            return None
        prefs = self._user_settings.get_by(user_id=project.user_id)
        if not prefs or prefs.default_provider != "groq":
            return None
        return (
            decrypt_secret(prefs.default_api_key_encrypted or "")
            or settings.groq_api_key
            or None
        )

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
        attachments = message.get("attachments") or []

        # Extract the first image URL if present.
        image_url = None
        for attachment in attachments:
            if attachment.get("type") == "image":
                image_url = (attachment.get("payload") or {}).get("url")
                if image_url:
                    break

        # Skip echoes of our own messages and delivery/read receipts.
        if message.get("is_echo") or not sender_id:
            return False
        # Skip if both text and image are missing.
        if not text and not image_url:
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
            text=text[:_MAX_INBOUND_CHARS] if text else None,
            image_url=image_url[:2000] if image_url else None,
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
        groq_key = self._groq_api_key(page.project_id)
        lines = []
        for e in ordered[: settings.messenger_coalesce_max]:
            if e.text:
                lines.append(e.text)
            if e.image_url:
                description = await describe_image(e.image_url, api_key=groq_key)
                if description:
                    lines.append(f"[Follower sent an image. Image content: {description}]")
                else:
                    lines.append("[Follower sent an image (could not analyze)]")
        combined = "\n".join(lines)
        token = decrypt_secret(page.access_token_encrypted)
        # Instagram messaging via Facebook login uses the SAME page-scoped Send
        # API as Messenger: POST /me/messages with the page token and the
        # recipient's id (a PSID for Messenger, an IGSID for Instagram). Meta
        # routes by recipient id type. The /{ig-user-id}/messages form is the
        # separate Instagram-login API and fails with "(#3) capability" here.
        url = f"{GRAPH_API}/me/messages"
        try:
            # Acknowledge the follower so the bubble shows "Seen" + typing while we
            # generate; both are best-effort and never block the actual reply.
            await self._send_action(url, sender_id, "mark_seen", token)
            await self._send_action(url, sender_id, "typing_on", token)
            reply, conversation = await self._build_reply(
                page, sender_id, combined, channel, token
            )
            if not reply:
                # A blank AI reply (a transient model glitch or a rate-limited
                # provider returning empty content) must not be swallowed as
                # success: that silently drops the follower's message with no
                # retry. Fail it so the poller retries on the next tick.
                raise RuntimeError("empty AI reply")
            await self._send(url, sender_id, reply, token)
            if conversation is not None and self.memory is not None:
                await self.memory.record_exchange(conversation, combined, reply)
            self._finish(events, "processed")
            self.db.commit()
            return True
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
        self, page: FacebookPage, sender_id: str, text: str, channel: str, token: str
    ) -> tuple[str, Conversation | None]:
        persona = (
            f"Voice and guidance: {page.reply_persona}" if page.reply_persona else ""
        )
        if self.memory is None:
            # No memory store to persist to: still personalize this one reply with
            # the follower's real name when the Graph API exposes it.
            name = await self._fetch_profile_name(sender_id, token, channel)
            prompt = prompt_engine.render(
                DEFAULT_DM_REPLY_PROMPT,
                {
                    "persona": persona,
                    "profile_hint": self._profile_hint(name, None, with_name=True),
                    "comment": text[:1500],
                },
            )
            result = await self.ai.generate(page.project_id, prompt)
            return self._clean(result.text), None

        conversation = self.memory.get_conversation(
            project_id=page.project_id,
            page_id=page.id,
            channel=channel,
            external_user_id=sender_id,
        )
        # Learn the follower's name + gender once so every reply addresses them
        # correctly (e.g. Vietnamese anh/chị). Best-effort; never blocks the reply.
        await self._ensure_profile(conversation, sender_id, token, channel, text)

        # First contact: use the plain prompt so the reply does not pretend to
        # remember a follower we have never talked to. The exchange is still
        # recorded (conversation returned) so memory builds up for next time.
        if not self.memory.has_context(conversation):
            prompt = prompt_engine.render(
                DEFAULT_DM_REPLY_PROMPT,
                {
                    "persona": persona,
                    "profile_hint": self._profile_hint(
                        conversation.user_name, conversation.gender, with_name=True
                    ),
                    "comment": text[:1500],
                },
            )
            result = await self.ai.generate(page.project_id, prompt)
            return self._clean(result.text), conversation

        context = await self.memory.build_context(conversation, text)
        prompt = prompt_engine.render(
            DEFAULT_DM_REPLY_WITH_MEMORY_PROMPT,
            {
                "persona": persona,
                "user_name": conversation.user_name or "this follower",
                "profile_hint": self._profile_hint(
                    conversation.user_name, conversation.gender, with_name=False
                ),
                "memory_context": context["memory_context"],
                "history": context["history"],
                "comment": text[:1500],
            },
        )
        result = await self.ai.generate(page.project_id, prompt)
        return self._clean(result.text), conversation

    # --- follower profile (name + gender for correct addressing) ---

    async def _ensure_profile(
        self,
        conversation: Conversation,
        user_id: str,
        token: str,
        channel: str,
        text: str,
    ) -> None:
        """Learn the follower's name and gender once; persist on the conversation.

        Best-effort: any Graph/AI failure leaves the field unset and the reply
        still goes out. Skipped entirely once both are already known.
        """
        if conversation.user_name and conversation.gender:
            return
        if not conversation.user_name:
            name = await self._fetch_profile_name(user_id, token, channel)
            if name:
                conversation.user_name = name[:255]
        if not conversation.gender and conversation.user_name:
            gender = await self._infer_gender(
                conversation.project_id, conversation.user_name, text
            )
            if gender:
                conversation.gender = gender
        self.db.flush()

    async def _fetch_profile_name(
        self, user_id: str, token: str, channel: str
    ) -> str | None:
        """Resolve a follower's display name via the Graph user-profile endpoint.

        Messenger exposes ``first_name``/``last_name``; Instagram exposes ``name``.
        A page admin's own app (development mode) can read this for the pages they
        manage without extra App Review. Returns None on any error.
        """
        is_instagram = channel == CHANNEL_IG_MESSAGE
        fields = "name" if is_instagram else "first_name,last_name"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{GRAPH_API}/{user_id}",
                    params={"fields": fields, "access_token": token},
                )
            if resp.status_code >= 400:
                log.debug(
                    f"profile fetch HTTP {resp.status_code} for {user_id}: "
                    f"{resp.text[:200]}"
                )
                return None
            data = resp.json()
        except Exception as exc:  # noqa: BLE001 - personalization is best-effort
            log.debug(f"profile fetch failed for {user_id}: {exc}")
            return None
        if is_instagram:
            return (data.get("name") or "").strip() or None
        name = " ".join(
            part for part in (data.get("first_name"), data.get("last_name")) if part
        ).strip()
        return name or None

    async def _infer_gender(self, project_id: str, name: str, text: str) -> str | None:
        """Infer ``"male"``/``"female"`` from the name + a sample message, or None."""
        prompt = prompt_engine.render(
            DEFAULT_GENDER_INFERENCE_PROMPT,
            {"name": name, "message": (text or "")[:500]},
        )
        try:
            result = await self.ai.generate(project_id, prompt)
        except Exception as exc:  # noqa: BLE001 - best-effort
            log.debug(f"gender inference failed for {name}: {exc}")
            return None
        answer = (result.text or "").strip().lower()
        # "female" contains "male", so test the more specific token first.
        if "female" in answer:
            return "female"
        if "male" in answer:
            return "male"
        return None

    @staticmethod
    def _profile_hint(name: str | None, gender: str | None, *, with_name: bool) -> str:
        """Build an addressing instruction from the follower's name and gender."""
        parts: list[str] = []
        if with_name and name:
            parts.append(f"The follower's name is {name}.")
        if gender == "male":
            parts.append("They appear to be male.")
        elif gender == "female":
            parts.append("They appear to be female.")
        if not parts:
            return ""
        parts.append(
            "Address them naturally and consistently in their own language, using "
            "the correct name and gendered honorifics where the language has them "
            "(for Vietnamese: anh for a man, chị for a woman)."
        )
        return " ".join(parts)

    @staticmethod
    def _clean(text: str) -> str:
        return strip_markdown(text).strip()[:_MAX_MESSAGE_CHARS]

    # --- Send API ---

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
