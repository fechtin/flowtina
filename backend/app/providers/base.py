"""Base AI provider interface and shared result type."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from app.core.exceptions import ProviderException


@dataclass
class GenerationResult:
    """Normalized result returned by every provider."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Runtime configuration for a provider instance."""

    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 1024
    timeout_seconds: int = 60
    system_prompt: str | None = None
    # Enable Google Search grounding (provider-specific; currently honored by Gemini).
    grounding: bool = False


class BaseAIProvider:
    """Abstract provider. Implementations override :meth:`generate`."""

    name: str = "base"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    async def generate(self, prompt: str) -> GenerationResult:  # pragma: no cover - interface
        raise NotImplementedError

    async def list_models(self) -> list[str]:
        """Return the model ids this provider exposes. Override where supported."""
        raise ProviderException(f"{self.name} does not support listing models")

    # Shared HTTP helper used by concrete providers.
    async def _get_json(self, url: str, headers: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code >= 400:
                raise ProviderException(
                    f"{self.name} HTTP {resp.status_code}: {resp.text[:300]}"
                )
            return resp.json()
        except httpx.TimeoutException as exc:
            raise ProviderException(f"{self.name} request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderException(f"{self.name} request failed: {exc}") from exc

    async def _post_json(self, url: str, headers: dict, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise ProviderException(
                    f"{self.name} HTTP {resp.status_code}: {resp.text[:300]}"
                )
            return resp.json()
        except httpx.TimeoutException as exc:
            raise ProviderException(f"{self.name} request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderException(f"{self.name} request failed: {exc}") from exc
