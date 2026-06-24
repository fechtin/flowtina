"""Unit tests for security, prompt engine, text utils and provider factory."""

from __future__ import annotations

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    mask_secret,
    verify_password,
)
from app.core.exceptions import AuthenticationException, ProviderException
from app.prompts.engine import PromptEngine, prompt_engine
from app.providers.base import ProviderConfig
from app.providers.factory import AIProviderFactory
from app.utils.text import (
    content_hash,
    normalize_hashtags,
    score_quality,
    strip_markdown,
)


def test_password_hash_roundtrip():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_encryption_roundtrip():
    cipher = encrypt_secret("sk-test-12345")
    assert cipher != "sk-test-12345"
    assert decrypt_secret(cipher) == "sk-test-12345"
    assert decrypt_secret("") == ""


def test_mask_secret():
    assert mask_secret("sk-abcdef") == "sk-a*****"
    assert mask_secret("ab") == "**"


def test_jwt_roundtrip_and_type_check():
    token = create_access_token("user-1", extra={"email": "a@b.com"})
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-1"
    with pytest.raises(AuthenticationException):
        decode_token(token, expected_type="refresh")


def test_prompt_engine_renders_and_defaults_missing():
    out = prompt_engine.render("Hello {{topic}} in {{language}}", {"topic": "AI", "language": "English"})
    assert out == "Hello AI in English"
    # Missing variable resolves to empty, never raises.
    out2 = prompt_engine.render("X {{unknown_var}} Y", {})
    assert "X" in out2 and "Y" in out2


def test_prompt_engine_layer_merge():
    final = prompt_engine.build_final_prompt(
        global_prompt="GLOBAL",
        project_prompt="PROJECT",
        content_prompt="Write about {{topic}}",
        variables={"topic": "crypto"},
    )
    assert "GLOBAL" in final and "PROJECT" in final and "crypto" in final


def test_extract_variables():
    assert PromptEngine.extract_variables("{{a}} {{ b }} {{a}}") == ["a", "b"]


def test_content_hash_stable():
    assert content_hash("Hello World") == content_hash("hello   world")
    assert content_hash("a") != content_hash("b")


def test_normalize_hashtags_dedup():
    assert normalize_hashtags("#AI #ai #ML extra #AI") == "#ai #ml"


def test_strip_markdown_flattens_formatting():
    assert strip_markdown("**Bold** and *italic*") == "Bold and italic"
    assert strip_markdown("# Heading\nBody") == "Heading\nBody"
    assert strip_markdown("Before\n\n---\n\nAfter") == "Before\n\nAfter"
    assert strip_markdown("See [site](https://x.io)") == "See site (https://x.io)"
    assert strip_markdown("Run `pip install`") == "Run pip install"


def test_strip_markdown_preserves_non_markdown():
    # snake_case, URLs, math and hashtags must survive untouched.
    assert strip_markdown("field image_url stays") == "field image_url stays"
    assert strip_markdown("area = 2 * 3 * 4") == "area = 2 * 3 * 4"
    assert strip_markdown("#brand and #growth") == "#brand and #growth"


def test_score_quality_bounds():
    assert score_quality("") == 0
    long_text = " ".join(f"word{i}" for i in range(200))
    assert 0 <= score_quality(long_text) <= 100


def test_provider_factory_creates_and_rejects_unknown():
    cfg = ProviderConfig(provider="openai", model="gpt-4o-mini")
    provider = AIProviderFactory.create(cfg)
    assert provider.name == "openai"
    with pytest.raises(ProviderException):
        AIProviderFactory.create(ProviderConfig(provider="nope", model="x"))


def test_provider_factory_cost_estimate():
    assert AIProviderFactory.estimate_cost("ollama", 1000) == 0.0
    assert AIProviderFactory.estimate_cost("openai", 1000) > 0
