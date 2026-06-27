"""Quota Manager: real-time tracking of AI provider usage per day."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.growth.models import ProviderQuota

log = get_logger("growth.quota")

_DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    "groq": {"requests": 14400, "tokens": 500_000},
    "gemini": {"requests": 1500, "tokens": 1_000_000},
    "openai": {"requests": 10_000, "tokens": 1_000_000},
    "claude": {"requests": 5_000, "tokens": 500_000},
    "deepseek": {"requests": 10_000, "tokens": 1_000_000},
    "openrouter": {"requests": 10_000, "tokens": 1_000_000},
    "ollama": {"requests": 999_999, "tokens": 999_999_999},
    "lmstudio": {"requests": 999_999, "tokens": 999_999_999},
}


def _date_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class QuotaManager:
    """Track and enforce daily request/token quotas per provider+model."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_or_create(self, provider: str, model: str, date: str) -> ProviderQuota:
        row = (
            self.db.query(ProviderQuota)
            .filter_by(provider=provider, model=model, date_key=date)
            .first()
        )
        if not row:
            limits = _DEFAULT_LIMITS.get(provider.lower(), {"requests": 10_000, "tokens": 1_000_000})
            row = ProviderQuota(
                provider=provider,
                model=model,
                date_key=date,
                requests_used=0,
                tokens_used=0,
                requests_limit=limits["requests"],
                tokens_limit=limits["tokens"],
            )
            self.db.add(row)
            self.db.flush()
        return row

    def has_quota(self, provider: str, model: str) -> bool:
        row = self._get_or_create(provider, model, _date_key())
        if row.requests_limit > 0 and row.requests_used >= row.requests_limit:
            log.warning(f"Quota exhausted (requests) for {provider}/{model}")
            return False
        if row.tokens_limit > 0 and row.tokens_used >= row.tokens_limit:
            log.warning(f"Quota exhausted (tokens) for {provider}/{model}")
            return False
        return True

    def record_usage(self, provider: str, model: str, tokens: int) -> None:
        row = self._get_or_create(provider, model, _date_key())
        row.requests_used += 1
        row.tokens_used += tokens
        self.db.flush()

    def get_status(self, provider: str, model: str) -> dict:
        row = self._get_or_create(provider, model, _date_key())
        return {
            "provider": provider,
            "model": model,
            "date": row.date_key,
            "requests_used": row.requests_used,
            "requests_limit": row.requests_limit,
            "tokens_used": row.tokens_used,
            "tokens_limit": row.tokens_limit,
        }
