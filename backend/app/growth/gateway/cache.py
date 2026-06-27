"""Prompt Cache: avoid duplicate AI calls for identical prompt+task combinations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.growth.models import PromptCacheEntry

log = get_logger("growth.cache")

_DEFAULT_TTL_HOURS = 24


def _make_key(task_type: str, prompt: str, **kwargs: object) -> str:
    payload = json.dumps({"task": task_type, "prompt": prompt, **kwargs}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:64]


class PromptCache:
    def __init__(self, db: Session, ttl_hours: int = _DEFAULT_TTL_HOURS) -> None:
        self.db = db
        self.ttl_hours = ttl_hours

    def get(self, task_type: str, prompt: str, **kwargs: object) -> str | None:
        key = _make_key(task_type, prompt, **kwargs)
        entry = self.db.query(PromptCacheEntry).filter_by(cache_key=key).first()
        if not entry:
            return None
        if entry.expires_at:
            expires = datetime.fromisoformat(entry.expires_at)
            if datetime.now(timezone.utc) > expires:
                self.db.delete(entry)
                self.db.flush()
                return None
        entry.hit_count += 1
        self.db.flush()
        log.debug(f"Cache hit for task={task_type} key={key[:8]}")
        return entry.result_text

    def set(self, task_type: str, prompt: str, result: str, provider: str, model: str, **kwargs: object) -> None:
        key = _make_key(task_type, prompt, **kwargs)
        expires = (datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)).isoformat()
        entry = self.db.query(PromptCacheEntry).filter_by(cache_key=key).first()
        if entry:
            entry.result_text = result
            entry.expires_at = expires
            entry.provider = provider
            entry.model = model
        else:
            entry = PromptCacheEntry(
                cache_key=key,
                prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:64],
                task_type=task_type,
                result_text=result,
                provider=provider,
                model=model,
                expires_at=expires,
            )
            self.db.add(entry)
        self.db.flush()
