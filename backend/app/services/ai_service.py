"""AI generation orchestration: provider selection, fallback chain, usage logging."""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ProviderException
from app.core.logger import get_logger
from app.core.security import decrypt_secret
from app.models.project import AIProvider
from app.providers.base import GenerationResult, ProviderConfig
from app.providers.factory import AIProviderFactory
from app.repositories.repositories import AIProviderRepository, AIUsageLogRepository
from app.schemas.project import (
    ProviderModelsRequest,
    ProviderTestRequest,
    ProviderTestResult,
)
from app.utils.retry import retry_async

log = get_logger("ai")


class AIService:
    """Generate text using a project's providers with automatic fallback."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.providers = AIProviderRepository(db)
        self.usage = AIUsageLogRepository(db)

    @staticmethod
    def _to_config(provider: AIProvider) -> ProviderConfig:
        return ProviderConfig(
            provider=provider.provider,
            model=provider.model,
            api_key=decrypt_secret(provider.api_key_encrypted or "") or None,
            base_url=provider.base_url,
            temperature=provider.temperature,
            top_p=provider.top_p,
            max_tokens=provider.max_tokens,
            timeout_seconds=provider.timeout_seconds,
            system_prompt=provider.system_prompt,
            grounding=provider.grounding_enabled,
        )

    async def generate(self, project_id: str, prompt: str) -> GenerationResult:
        """Generate text, trying each enabled provider (by priority) in turn."""
        providers = self.providers.list_enabled(project_id)
        if not providers:
            raise ProviderException("No enabled AI provider configured for this project")

        last_error: Exception | None = None
        for provider in providers:
            config = self._to_config(provider)
            client = AIProviderFactory.create(config)
            start = time.perf_counter()
            try:
                result = await retry_async(
                    lambda c=client: c.generate(prompt),
                    attempts=3,
                    on_error=lambda attempt, exc: log.warning(
                        f"{config.provider} attempt {attempt + 1} failed: {exc}"
                    ),
                )
                duration_ms = int((time.perf_counter() - start) * 1000)
                self._log_usage(project_id, config.provider, result, duration_ms)
                self.db.commit()
                return result
            except Exception as exc:  # noqa: BLE001 - try next provider
                last_error = exc
                log.error(f"Provider {config.provider} exhausted retries: {exc}")
                continue

        raise ProviderException(f"All providers failed. Last error: {last_error}")

    def _log_usage(
        self, project_id: str, provider: str, result: GenerationResult, duration_ms: int
    ) -> None:
        cost = AIProviderFactory.estimate_cost(provider, result.total_tokens)
        self.usage.create(
            project_id=project_id,
            provider=provider,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost=cost,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _resolve_api_key(provider: str, api_key: str | None) -> str | None:
        """Use the typed-in key, falling back to the env-configured one."""
        return api_key or settings.provider_api_key(provider) or None

    @staticmethod
    async def list_models(payload: ProviderModelsRequest) -> list[str]:
        """List the models a provider exposes (no persistence)."""
        config = ProviderConfig(
            provider=payload.provider,
            model="",
            api_key=AIService._resolve_api_key(payload.provider, payload.api_key),
            base_url=payload.base_url,
            timeout_seconds=30,
        )
        client = AIProviderFactory.create(config)
        return await client.list_models()

    @staticmethod
    async def test_connection(payload: ProviderTestRequest) -> ProviderTestResult:
        """One-shot connectivity test for a provider config (no persistence)."""
        config = ProviderConfig(
            provider=payload.provider,
            model=payload.model,
            api_key=AIService._resolve_api_key(payload.provider, payload.api_key),
            base_url=payload.base_url,
            max_tokens=32,
            timeout_seconds=30,
        )
        client = AIProviderFactory.create(config)
        start = time.perf_counter()
        try:
            result = await client.generate(payload.prompt)
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderTestResult(success=True, latency_ms=latency, output=result.text[:200])
        except Exception as exc:  # noqa: BLE001 - surface as failed test
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderTestResult(success=False, latency_ms=latency, error=str(exc))
