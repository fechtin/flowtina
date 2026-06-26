"""Unit tests for Messenger DM auto-reply: enqueue, debounce, dedupe, coalesce."""

from __future__ import annotations

import asyncio
import hashlib
import hmac

from app.core.config import settings
from app.core.security import encrypt_secret
from app.models.memory import CHANNEL_MESSENGER
from app.providers.base import GenerationResult
from app.repositories.repositories import (
    ConversationRepository,
    FacebookPageRepository,
    MessengerEventRepository,
)
from app.services.messenger_service import MessengerService


class _FakeAI:
    def __init__(self, text: str) -> None:
        self._text = text

    async def generate(self, project_id: str, prompt: str) -> GenerationResult:
        return GenerationResult(text=self._text)


def _make_page(db, **overrides):
    data = {
        "project_id": "proj-1",
        "page_name": "Test Page",
        "page_id": "123",
        "access_token_encrypted": encrypt_secret("page-token"),
        "enabled": True,
        "auto_reply_messages": True,
    }
    data.update(overrides)
    page = FacebookPageRepository(db).create(**data)
    db.flush()
    return page


def _wire(service: MessengerService) -> list:
    """Stub AI + Send API + sender actions so the flow runs without network."""
    service.ai = _FakeAI("Jazz is wonderful, glad you enjoy it!")
    service.memory.ai = _FakeAI(
        '{"memories": [{"type": "semantic", "content": "Loves jazz music", "importance": 70}]}'
    )
    sent: list = []

    async def _fake_send(url: str, recipient_id: str, message: str, token: str) -> None:
        sent.append((recipient_id, message, token))

    async def _fake_action(
        url: str, recipient_id: str, action: str, token: str
    ) -> None:
        return None

    service._send = _fake_send  # type: ignore[method-assign]
    service._send_action = _fake_action  # type: ignore[method-assign]
    return sent


def _payload(text: str = "Hi, I love jazz", sender: str = "psid-1", **msg):
    message = {"text": text}
    message.update(msg)
    return {
        "object": "page",
        "entry": [{"id": "123", "messaging": [{"sender": {"id": sender}, "message": message}]}],
    }


# --- signature / verify token ---


def test_verify_signature_matches_app_secret(monkeypatch):
    monkeypatch.setattr(settings, "facebook_app_secret", "shh")
    body = b'{"object":"page"}'
    good = "sha256=" + hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    assert MessengerService.verify_signature(body, good)
    assert not MessengerService.verify_signature(body, "sha256=deadbeef")
    assert not MessengerService.verify_signature(body, None)


def test_verify_signature_skipped_without_secret(monkeypatch):
    monkeypatch.setattr(settings, "facebook_app_secret", "")
    assert MessengerService.verify_signature(b"anything", None)


# --- enqueue (webhook path) ---


def test_enqueue_skips_echo_empty_and_unknown_page(db_session):
    _make_page(db_session)
    service = MessengerService(db_session)
    _wire(service)
    assert service.enqueue_event(_payload(text="", is_echo=True)) == 0
    assert service.enqueue_event(_payload(text="   ")) == 0
    unknown = _payload()
    unknown["entry"][0]["id"] = "999"
    assert service.enqueue_event(unknown) == 0


def test_enqueue_ignored_when_disabled(db_session):
    _make_page(db_session, auto_reply_messages=False)
    service = MessengerService(db_session)
    _wire(service)
    assert service.enqueue_event(_payload()) == 0


def test_enqueue_dedupes_by_mid(db_session):
    _make_page(db_session)
    service = MessengerService(db_session)
    _wire(service)
    assert service.enqueue_event(_payload(mid="m-1")) == 1
    # Meta re-delivers the same message id -> must not queue a second time.
    assert service.enqueue_event(_payload(mid="m-1")) == 0
    assert MessengerEventRepository(db_session).count(status="pending") == 1


# --- inbox poller ---


def test_process_inbox_replies_and_records_memory(db_session, monkeypatch):
    monkeypatch.setattr(settings, "messenger_debounce_seconds", 0)
    _make_page(db_session)
    service = MessengerService(db_session)
    sent = _wire(service)

    assert service.enqueue_event(_payload()) == 1
    assert asyncio.run(service.process_inbox()) == 1

    assert sent and sent[0][0] == "psid-1"
    conv = ConversationRepository(db_session).get_by(
        channel=CHANNEL_MESSENGER, external_user_id="psid-1"
    )
    assert conv is not None
    assert conv.message_count == 2
    assert MessengerEventRepository(db_session).count(status="pending") == 0


def test_debounce_holds_unsettled_messages(db_session, monkeypatch):
    # A fresh message is younger than the debounce window -> hold, do not reply yet.
    monkeypatch.setattr(settings, "messenger_debounce_seconds", 600)
    _make_page(db_session)
    service = MessengerService(db_session)
    sent = _wire(service)

    assert service.enqueue_event(_payload()) == 1
    assert asyncio.run(service.process_inbox()) == 0
    assert sent == []
    assert MessengerEventRepository(db_session).count(status="pending") == 1


def test_first_contact_uses_plain_prompt_then_memory(db_session, monkeypatch):
    """First DM must not feign prior familiarity; later DMs use memory context."""
    monkeypatch.setattr(settings, "messenger_debounce_seconds", 0)
    _make_page(db_session)
    service = MessengerService(db_session)
    _wire(service)

    prompts: list[str] = []
    fixed = service.ai

    class _Recording:
        async def generate(self, project_id: str, prompt: str):
            prompts.append(prompt)
            return await fixed.generate(project_id, prompt)

    service.ai = _Recording()
    marker = "talked with before"  # only present in the memory-aware prompt

    service.enqueue_event(_payload(text="Hi", mid="a"))
    asyncio.run(service.process_inbox())
    assert prompts and marker not in prompts[-1]  # first contact -> plain prompt

    service.enqueue_event(_payload(text="Tell me more", mid="b"))
    asyncio.run(service.process_inbox())
    assert marker in prompts[-1]  # now remembered -> memory-aware prompt


def test_instagram_dm_replies_via_send_api(db_session, monkeypatch):
    """An object=="instagram" webhook is routed by IG account id, tagged with the
    ig_dm channel, and replied to through the page Send API, gated by its own
    toggle. Instagram messaging via Facebook login uses /me/messages, the same
    endpoint as Messenger (recipient is an IGSID)."""
    monkeypatch.setattr(settings, "messenger_debounce_seconds", 0)
    _make_page(
        db_session,
        instagram_user_id="ig-77",
        instagram_username="myinsta",
        auto_reply_messages=False,
        auto_reply_ig_messages=True,
    )
    service = MessengerService(db_session)
    _wire(service)
    captured: list = []

    async def _capture_send(url: str, recipient_id: str, message: str, token: str) -> None:
        captured.append((url, recipient_id, message))

    service._send = _capture_send  # type: ignore[method-assign]

    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "ig-77",
                "messaging": [
                    {"sender": {"id": "igsid-1"}, "message": {"text": "hello", "mid": "ig-m1"}}
                ],
            }
        ],
    }
    assert service.enqueue_event(payload) == 1
    ev = MessengerEventRepository(db_session).list_pending()[0]
    assert ev.channel == "ig_dm"

    assert asyncio.run(service.process_inbox()) == 1
    assert captured and captured[0][0].endswith("/me/messages")  # page Send API
    assert captured[0][1] == "igsid-1"  # replied to the IGSID


def test_instagram_dm_ignored_when_ig_toggle_off(db_session):
    """IG DMs are not queued when only the Facebook DM toggle is on."""
    _make_page(
        db_session,
        instagram_user_id="ig-77",
        auto_reply_messages=True,
        auto_reply_ig_messages=False,
    )
    service = MessengerService(db_session)
    _wire(service)
    payload = {
        "object": "instagram",
        "entry": [
            {"id": "ig-77", "messaging": [{"sender": {"id": "igsid-1"}, "message": {"text": "hi"}}]}
        ],
    }
    assert service.enqueue_event(payload) == 0


def test_rapid_messages_coalesce_into_one_reply(db_session, monkeypatch):
    monkeypatch.setattr(settings, "messenger_debounce_seconds", 0)
    _make_page(db_session)
    service = MessengerService(db_session)
    sent = _wire(service)

    # Three quick lines from the same follower before any reply.
    assert service.enqueue_event(_payload(text="Hi", mid="m-1")) == 1
    assert service.enqueue_event(_payload(text="I love jazz", mid="m-2")) == 1
    assert service.enqueue_event(_payload(text="and blues", mid="m-3")) == 1

    assert asyncio.run(service.process_inbox()) == 1
    # Exactly one reply, not three — no duplicate-reply storm.
    assert len(sent) == 1
    conv = ConversationRepository(db_session).get_by(
        channel=CHANNEL_MESSENGER, external_user_id="psid-1"
    )
    assert conv.message_count == 2  # one combined follower turn + one page reply
    assert MessengerEventRepository(db_session).count(status="pending") == 0
