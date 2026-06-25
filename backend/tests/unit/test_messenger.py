"""Unit tests for Messenger DM auto-reply and webhook handling."""

from __future__ import annotations

import asyncio
import hashlib
import hmac

from app.core.security import encrypt_secret
from app.models.memory import CHANNEL_MESSENGER
from app.providers.base import GenerationResult
from app.repositories.repositories import (
    ConversationRepository,
    FacebookPageRepository,
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
    """Stub AI + Send API so handle_event runs without network calls."""
    service.ai = _FakeAI("Jazz is wonderful, glad you enjoy it!")
    service.memory.ai = _FakeAI(
        '{"memories": [{"type": "semantic", "content": "Loves jazz music", "importance": 70}]}'
    )
    sent: list = []

    async def _fake_send(recipient_id: str, message: str, token: str) -> None:
        sent.append((recipient_id, message, token))

    service._send = _fake_send  # type: ignore[method-assign]
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
    from app.core.config import settings

    monkeypatch.setattr(settings, "facebook_app_secret", "shh")
    body = b'{"object":"page"}'
    good = "sha256=" + hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    assert MessengerService.verify_signature(body, good)
    assert not MessengerService.verify_signature(body, "sha256=deadbeef")
    assert not MessengerService.verify_signature(body, None)


def test_verify_signature_skipped_without_secret(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "facebook_app_secret", "")
    assert MessengerService.verify_signature(b"anything", None)


# --- event handling ---


def test_handle_event_replies_and_records_memory(db_session):
    _make_page(db_session)
    service = MessengerService(db_session)
    sent = _wire(service)

    count = asyncio.run(service.handle_event(_payload()))

    assert count == 1
    assert sent and sent[0][0] == "psid-1"
    conv = ConversationRepository(db_session).get_by(
        channel=CHANNEL_MESSENGER, external_user_id="psid-1"
    )
    assert conv is not None
    assert conv.channel == CHANNEL_MESSENGER
    assert conv.message_count == 2


def test_handle_event_ignores_when_disabled(db_session):
    _make_page(db_session, auto_reply_messages=False)
    service = MessengerService(db_session)
    sent = _wire(service)
    assert asyncio.run(service.handle_event(_payload())) == 0
    assert sent == []


def test_handle_event_skips_echo_and_empty(db_session):
    _make_page(db_session)
    service = MessengerService(db_session)
    sent = _wire(service)
    assert asyncio.run(service.handle_event(_payload(text="", is_echo=True))) == 0
    assert asyncio.run(service.handle_event(_payload(text="   "))) == 0
    assert sent == []


def test_handle_event_ignores_unknown_page(db_session):
    service = MessengerService(db_session)
    sent = _wire(service)
    payload = _payload()
    payload["entry"][0]["id"] = "999"  # no such connected page
    assert asyncio.run(service.handle_event(payload)) == 0
    assert sent == []


# --- webhook verification endpoint ---


def test_webhook_get_challenge(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "messenger_verify_token", "vt-123")
    resp = client.get(
        "/api/v1/messenger/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "vt-123", "hub.challenge": "echo-me"},
    )
    assert resp.status_code == 200
    assert resp.text == "echo-me"

    bad = client.get(
        "/api/v1/messenger/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
    )
    assert bad.status_code == 403
