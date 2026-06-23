"""Telegram bot integration for reports and alerts (Bot API only)."""

from __future__ import annotations

import time

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, TelegramException
from app.core.logger import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.models.integration import TelegramConfig
from app.repositories.repositories import TelegramConfigRepository, TelegramLogRepository
from app.schemas.content import TelegramConfigIn
from app.utils.retry import retry_async

log = get_logger("telegram")

TELEGRAM_API = "https://api.telegram.org"


class TelegramService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.configs = TelegramConfigRepository(db)
        self.logs = TelegramLogRepository(db)

    def get_config(self, project_id: str) -> TelegramConfig | None:
        return self.configs.get_for_project(project_id)

    def upsert_config(self, project_id: str, payload: TelegramConfigIn) -> TelegramConfig:
        existing = self.configs.get_by(project_id=project_id)
        if existing:
            existing.bot_token_encrypted = encrypt_secret(payload.bot_token)
            existing.chat_id = payload.chat_id
            existing.enabled = payload.enabled
            config = existing
        else:
            config = self.configs.create(
                project_id=project_id,
                bot_token_encrypted=encrypt_secret(payload.bot_token),
                chat_id=payload.chat_id,
                enabled=payload.enabled,
            )
        self.db.commit()
        self.db.refresh(config)
        return config

    async def send(self, project_id: str, message: str, *, type_: str = "manual") -> bool:
        config = self.configs.get_for_project(project_id)
        if not config:
            raise NotFoundException("Telegram is not configured for this project")
        return await self._deliver(
            project_id, decrypt_secret(config.bot_token_encrypted), config.chat_id, message, type_
        )

    async def _deliver(
        self, project_id: str, token: str, chat_id: str, message: str, type_: str
    ) -> bool:
        url = f"{TELEGRAM_API}/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        start = time.perf_counter()
        try:
            await retry_async(lambda: self._post(url, payload), attempts=3)
            duration = int((time.perf_counter() - start) * 1000)
            self.logs.create(
                project_id=project_id, type=type_, message=message[:2000],
                status="sent", duration_ms=duration,
            )
            self.db.commit()
            return True
        except Exception as exc:  # noqa: BLE001 - telegram failures are non-fatal
            self.logs.create(
                project_id=project_id, type=type_, message=message[:2000],
                status="failed", error_message=str(exc)[:500],
            )
            self.db.commit()
            log.warning(f"Telegram send failed: {exc}")
            return False

    @staticmethod
    async def _post(url: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            raise TelegramException(f"Telegram HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()
