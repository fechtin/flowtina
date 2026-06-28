"""Unit tests for Growth Engine image generation (Cloudflare FLUX.1-schnell)."""

import asyncio
import base64

import pytest

from app.core.config import settings
from app.growth.content.image_generator import ImageGenerationError, generate_image
from app.utils.media import save_bytes, upload_abs_path


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = "cloudflare error body"

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def post(self, url, headers=None, json=None) -> _FakeResponse:
        return self._response


def _patch_client(monkeypatch, response: _FakeResponse) -> None:
    monkeypatch.setattr(
        "app.growth.content.image_generator.httpx.AsyncClient",
        lambda *a, **k: _FakeClient(response),
    )


def _with_creds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cloudflare_account_id", "acct")
    monkeypatch.setattr(settings, "cloudflare_api_token", "tok")


def test_generate_image_decodes_base64(monkeypatch):
    _with_creds(monkeypatch)
    raw = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
    payload = {"result": {"image": base64.b64encode(raw).decode()}, "success": True}
    _patch_client(monkeypatch, _FakeResponse(200, payload))
    assert asyncio.run(generate_image("a serene beach in Vietnam")) == raw


def test_generate_image_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_account_id", "")
    monkeypatch.setattr(settings, "cloudflare_api_token", "")
    with pytest.raises(ImageGenerationError):
        asyncio.run(generate_image("a cat"))


def test_generate_image_rejects_empty_prompt(monkeypatch):
    _with_creds(monkeypatch)
    with pytest.raises(ImageGenerationError):
        asyncio.run(generate_image("   "))


def test_generate_image_raises_on_http_error(monkeypatch):
    _with_creds(monkeypatch)
    _patch_client(monkeypatch, _FakeResponse(429, {}))
    with pytest.raises(ImageGenerationError):
        asyncio.run(generate_image("a cat"))


def test_generate_image_raises_when_no_image(monkeypatch):
    _with_creds(monkeypatch)
    _patch_client(monkeypatch, _FakeResponse(200, {"result": {}}))
    with pytest.raises(ImageGenerationError):
        asyncio.run(generate_image("a cat"))


def test_save_bytes_writes_and_resolves(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    rel = save_bytes(b"hello-image", "page-123", ".jpg")
    assert rel.startswith("page-123/")
    assert upload_abs_path(rel).read_bytes() == b"hello-image"


def test_save_bytes_rejects_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    from app.core.exceptions import ValidationException

    with pytest.raises(ValidationException):
        save_bytes(b"", "page-123")
