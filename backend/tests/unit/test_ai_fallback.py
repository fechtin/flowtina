"""Global default-provider model fallback chain."""

from __future__ import annotations

from app.core.security import encrypt_secret
from app.repositories.repositories import (
    ProjectRepository,
    UserRepository,
    UserSettingsRepository,
)
from app.services.ai_service import AIService


def _seed(db, *, provider: str, model: str) -> str:
    user = UserRepository(db).create(email="o@example.com", password_hash="x", name="Owner")
    project = ProjectRepository(db).create(user_id=user.id, name="P")
    UserSettingsRepository(db).create(
        user_id=user.id,
        default_provider=provider,
        default_model=model,
        default_api_key_encrypted=encrypt_secret("gsk_test"),
    )
    db.commit()
    return project.id


def test_groq_default_yields_priority_model_chain(db_session):
    project_id = _seed(db_session, provider="groq", model="qwen/qwen3-32b")
    configs = AIService(db_session)._global_fallback_configs(project_id)

    models = [c.model for c in configs]
    assert models == [
        "qwen/qwen3-32b",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
    ]
    # The owner's key is reused for every fallback model (same provider).
    assert all(c.provider == "groq" and c.api_key == "gsk_test" for c in configs)


def test_non_groq_default_yields_single_config(db_session):
    project_id = _seed(db_session, provider="openai", model="gpt-4o-mini")
    configs = AIService(db_session)._global_fallback_configs(project_id)

    assert [c.model for c in configs] == ["gpt-4o-mini"]
