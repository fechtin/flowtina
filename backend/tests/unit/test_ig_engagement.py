"""Unit tests for Instagram comment auto-reply (polling + dedup + reply)."""

from __future__ import annotations

import asyncio

from app.core.security import encrypt_secret
from app.providers.base import GenerationResult
from app.repositories.repositories import (
    FacebookCommentRepository,
    FacebookPageRepository,
)
from app.services.facebook_engagement_service import FacebookEngagementService


class _FakeAI:
    async def generate(self, project_id: str, prompt: str) -> GenerationResult:
        return GenerationResult(text="Thanks for your comment!")


def _make_page(db, **overrides):
    data = {
        "project_id": "proj-1",
        "page_name": "Test Page",
        "page_id": "123",
        "access_token_encrypted": encrypt_secret("page-token"),
        "enabled": True,
        "instagram_user_id": "ig-77",
        "instagram_username": "myinsta",
        "auto_reply_ig_comments": True,
    }
    data.update(overrides)
    page = FacebookPageRepository(db).create(**data)
    db.flush()
    return page


def _wire(service: FacebookEngagementService, replied: list) -> None:
    service.ai = _FakeAI()
    service.memory = None  # exercise the plain (memory-off) reply path

    async def _fetch_media(ig_user_id: str, token: str) -> list[dict]:
        return [{"id": "media-1", "caption": "My photo"}]

    async def _fetch_comments(media_id: str, token: str) -> list[dict]:
        return [{"id": "igc-1", "text": "Nice shot!", "username": "fan1", "from": {"id": "u-1"}}]

    async def _reply(comment_id: str, message: str, token: str) -> None:
        replied.append((comment_id, message))

    service._fetch_ig_media = _fetch_media  # type: ignore[method-assign]
    service._fetch_ig_comments = _fetch_comments  # type: ignore[method-assign]
    service._reply_ig_comment = _reply  # type: ignore[method-assign]


def test_ig_comment_auto_reply_and_dedup(db_session):
    page = _make_page(db_session)
    db_session.commit()
    service = FacebookEngagementService(db_session)
    replied: list = []
    _wire(service, replied)

    result = asyncio.run(service.engage_page_all(page))
    assert result["processed"] == 1
    assert replied == [("igc-1", "Thanks for your comment!")]

    # The comment is recorded as replied and not acted on a second time.
    comments = FacebookCommentRepository(db_session).list_for_page(page.id)
    assert len(comments) == 1 and comments[0].replied is True

    again = asyncio.run(service.engage_page_all(page))
    assert again["processed"] == 0
    assert len(replied) == 1


def test_ig_comment_skips_own_comment(db_session):
    """The IG account's own comments/replies must never be answered."""
    page = _make_page(db_session)
    db_session.commit()
    service = FacebookEngagementService(db_session)
    replied: list = []
    _wire(service, replied)

    async def _own_comment(media_id: str, token: str) -> list[dict]:
        return [{"id": "igc-own", "text": "our reply", "username": "myinsta", "from": {"id": "ig-77"}}]

    service._fetch_ig_comments = _own_comment  # type: ignore[method-assign]

    result = asyncio.run(service.engage_page_all(page))
    assert result["processed"] == 0
    assert replied == []
