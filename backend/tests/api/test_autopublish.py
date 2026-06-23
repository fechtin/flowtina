"""Tests for auto-publish, Telegram approval, and webhook approve/reject.

All external calls (AI provider, Facebook Graph API, Telegram Bot API) are mocked.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationException
from app.providers.base import GenerationResult
from app.repositories.repositories import (
    AIProviderRepository,
    FacebookPageRepository,
    PostRepository,
    ProjectRepository,
    TelegramConfigRepository,
    TelegramLogRepository,
    UserRepository,
)
from app.core.security import encrypt_secret
from app.schemas.content import JobCreate
from app.services.content_service import ContentService
from app.services.scheduler_service import SchedulerService
from app.services.telegram_service import TelegramService


class FakeProvider:
    def __init__(self, config):
        self.config = config

    async def generate(self, prompt: str) -> GenerationResult:
        text = "#tag" if "hashtag" in prompt.lower() else " ".join(
            f"word{i} of the article body" for i in range(40)
        )
        return GenerationResult(text=text, total_tokens=30, model="fake", provider="openai")


@pytest.fixture
def project_setup(db_session, monkeypatch):
    """Project with an enabled provider, a Facebook page and a Telegram config."""
    monkeypatch.setattr(
        "app.services.ai_service.AIProviderFactory.create", lambda config: FakeProvider(config)
    )
    user = UserRepository(db_session).create(email="ap@x.com", password_hash="x", name="AP")
    project = ProjectRepository(db_session).create(user_id=user.id, name="Proj")
    AIProviderRepository(db_session).create(
        project_id=project.id, provider="openai", model="gpt-4o-mini", enabled=True
    )
    page = FacebookPageRepository(db_session).create(
        project_id=project.id, page_name="My Page", page_id="111",
        access_token_encrypted=encrypt_secret("tok"),
    )
    TelegramConfigRepository(db_session).create(
        project_id=project.id, bot_token_encrypted=encrypt_secret("123:abc"),
        chat_id="999", enabled=True,
    )
    db_session.commit()
    return project, page


async def test_auto_publish_immediate(db_session, project_setup, monkeypatch):
    project, page = project_setup

    async def fake_graph(url, data):
        return {"id": "fb_post_1"}

    monkeypatch.setattr(
        "app.services.facebook_service.FacebookService._call_graph", staticmethod(fake_graph)
    )
    posts = await ContentService(db_session).generate_for_project(
        project.id, topic="AI", auto_publish=True, require_approval=False, target_page_id=page.id
    )
    assert len(posts) == 1
    assert posts[0].status == "published"
    assert posts[0].facebook_page_id == page.id


async def test_require_approval_holds_post(db_session, project_setup, monkeypatch):
    project, page = project_setup

    async def fake_tg(url, payload):
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.telegram_service.TelegramService._post", staticmethod(fake_tg)
    )
    posts = await ContentService(db_session).generate_for_project(
        project.id, topic="AI", auto_publish=True, require_approval=True, target_page_id=page.id
    )
    assert posts[0].status == "pending_approval"
    assert posts[0].facebook_page_id == page.id
    logs = TelegramLogRepository(db_session).list(project_id=project.id)
    assert any(log.type == "approval_request" and log.status == "sent" for log in logs)


async def test_webhook_approve_publishes(db_session, project_setup, monkeypatch):
    project, page = project_setup
    calls: list[str] = []

    async def fake_post(url, payload):
        calls.append(url)
        return {"ok": True}

    async def fake_graph(url, data):
        return {"id": "fb_post_2"}

    monkeypatch.setattr(
        "app.services.telegram_service.TelegramService._post", staticmethod(fake_post)
    )
    monkeypatch.setattr(
        "app.services.facebook_service.FacebookService._call_graph", staticmethod(fake_graph)
    )
    post = PostRepository(db_session).create(
        project_id=project.id, content="pending content here for approval test",
        status="pending_approval", facebook_page_id=page.id,
    )
    db_session.commit()

    update = {
        "callback_query": {
            "id": "cb1",
            "data": f"approve:{post.id}",
            "message": {"chat": {"id": 999}, "message_id": 7},
        }
    }
    await TelegramService(db_session).handle_callback(update)
    db_session.refresh(post)
    assert post.status == "published"


async def test_webhook_reject_archives(db_session, project_setup, monkeypatch):
    project, page = project_setup

    async def fake_post(url, payload):
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.telegram_service.TelegramService._post", staticmethod(fake_post)
    )
    post = PostRepository(db_session).create(
        project_id=project.id, content="content to be rejected",
        status="pending_approval", facebook_page_id=page.id,
    )
    db_session.commit()
    update = {
        "callback_query": {
            "id": "cb2",
            "data": f"reject:{post.id}",
            "message": {"chat": {"id": 999}, "message_id": 8},
        }
    }
    await TelegramService(db_session).handle_callback(update)
    db_session.refresh(post)
    assert post.status == "archived"


def test_job_rejects_foreign_page(db_session):
    user = UserRepository(db_session).create(email="j2@x.com", password_hash="x", name="J2")
    project = ProjectRepository(db_session).create(user_id=user.id, name="P")
    other = ProjectRepository(db_session).create(user_id=user.id, name="Other")
    foreign_page = FacebookPageRepository(db_session).create(
        project_id=other.id, page_name="X", page_id="9", access_token_encrypted=encrypt_secret("t")
    )
    db_session.commit()
    with pytest.raises(ValidationException):
        SchedulerService(db_session).create(
            project.id,
            JobCreate(name="J", auto_publish=True, facebook_page_id=foreign_page.id),
        )
