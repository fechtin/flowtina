"""Content pipeline and posts tests using a fake AI provider (no real API calls)."""

from __future__ import annotations

import pytest

from app.providers.base import GenerationResult
from app.services.content_service import ContentService
from app.services.post_service import PostService
from app.repositories.repositories import AIProviderRepository, ProjectRepository, UserRepository
from app.schemas.content import PostCreate


class FakeProvider:
    """Returns deterministic text without network access."""

    def __init__(self, config):
        self.config = config

    async def generate(self, prompt: str) -> GenerationResult:
        if "hashtag" in prompt.lower():
            text = "#ai #automation #flowtina"
        else:
            text = " ".join(f"sentence{i} about the topic" for i in range(40))
        return GenerationResult(
            text=text,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            model="fake-model",
            provider="openai",
        )


@pytest.fixture
def project_with_provider(db_session):
    user = UserRepository(db_session).create(
        email="p@x.com", password_hash="x", name="P", is_admin=True
    )
    project = ProjectRepository(db_session).create(user_id=user.id, name="Proj")
    AIProviderRepository(db_session).create(
        project_id=project.id, provider="openai", model="gpt-4o-mini", enabled=True
    )
    db_session.commit()
    return project


async def test_pipeline_generates_draft(db_session, project_with_provider, monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_service.AIProviderFactory.create", lambda config: FakeProvider(config)
    )
    service = ContentService(db_session)
    posts = await service.generate_for_project(
        project_with_provider.id, topic="AI trends", content_type="short_post"
    )
    assert len(posts) == 1
    post = posts[0]
    assert post.status == "draft"
    assert post.quality_score > 0
    assert post.content
    assert post.hashtags.startswith("#")


async def test_pipeline_no_provider_raises(db_session, monkeypatch):
    from app.core.exceptions import ProviderException

    user = UserRepository(db_session).create(email="np@x.com", password_hash="x", name="N")
    project = ProjectRepository(db_session).create(user_id=user.id, name="NoProv")
    db_session.commit()
    with pytest.raises(ProviderException):
        await ContentService(db_session).generate_for_project(project.id, topic="x")


def test_post_versioning(db_session, project_with_provider):
    svc = PostService(db_session)
    post = svc.create(project_with_provider.id, PostCreate(content="original content here"))
    assert post.version == 1
    from app.schemas.content import PostUpdate

    updated = svc.update(post.id, PostUpdate(content="brand new content"))
    assert updated.version == 2
    # Previous version archived.
    from app.repositories.repositories import PostVersionRepository

    versions = PostVersionRepository(db_session).list(post_id=post.id)
    assert len(versions) == 1
    assert versions[0].content == "original content here"
