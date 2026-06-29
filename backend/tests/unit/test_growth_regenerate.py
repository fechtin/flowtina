"""Unit tests for manual draft image (re)generation."""

import asyncio

import pytest

from app.core.config import settings
from app.growth.models import ContentDraft
from app.growth.service import GrowthService
from app.utils.media import upload_abs_path


async def _fake_generate(prompt: str) -> bytes:
    return b"generated-image-bytes"


def _draft(image_prompt: str | None) -> ContentDraft:
    return ContentDraft(
        page_id="p1", content_type="post", body="x",
        status="pending_review", image_prompt=image_prompt,
    )


def test_regenerate_image_saves_and_updates_prompt(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr("app.growth.service.generate_image", _fake_generate)
    svc = GrowthService(db_session)
    draft = _draft("old prompt")
    db_session.add(draft)
    db_session.commit()

    updated = asyncio.run(svc.regenerate_image(draft.id, "p1", "new edited prompt"))

    assert updated.image_prompt == "new edited prompt"
    assert updated.media_url and updated.media_url.startswith("p1/")
    assert upload_abs_path(updated.media_url).read_bytes() == b"generated-image-bytes"


def test_regenerate_image_prunes_old_file(db_session, monkeypatch):
    monkeypatch.setattr("app.growth.service.generate_image", _fake_generate)
    paths = iter(["p1/first.jpg", "p1/second.jpg"])
    monkeypatch.setattr("app.growth.service.save_bytes", lambda data, owner, ext=".jpg": next(paths))
    removed: list[str] = []
    monkeypatch.setattr("app.growth.service.remove_upload", removed.append)
    svc = GrowthService(db_session)
    draft = _draft("prompt")
    db_session.add(draft)
    db_session.commit()

    first_url = asyncio.run(svc.regenerate_image(draft.id, "p1", None)).media_url
    second_url = asyncio.run(svc.regenerate_image(draft.id, "p1", None)).media_url

    assert first_url == "p1/first.jpg"
    assert second_url == "p1/second.jpg"
    assert removed == ["p1/first.jpg"]  # the previous image is pruned on regen


def test_regenerate_image_requires_a_prompt(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr("app.growth.service.generate_image", _fake_generate)
    svc = GrowthService(db_session)
    draft = _draft(None)
    db_session.add(draft)
    db_session.commit()

    with pytest.raises(ValueError):
        asyncio.run(svc.regenerate_image(draft.id, "p1", "   "))
