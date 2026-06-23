"""Factory that builds a provider instance from a name + config.

Also exposes a rough per-1K-token cost table used for cost estimation in usage
logs and reports.
"""

from __future__ import annotations

from app.core.exceptions import ProviderException
from app.providers.base import BaseAIProvider, ProviderConfig
from app.providers.claude import ClaudeProvider
from app.providers.gemini import GeminiProvider
from app.providers.openai_compatible import (
    CustomProvider,
    DeepSeekProvider,
    LMStudioProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    VLLMProvider,
)

_REGISTRY: dict[str, type[BaseAIProvider]] = {
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "openrouter": OpenRouterProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
    "vllm": VLLMProvider,
    "custom": CustomProvider,
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
}

# Approximate blended cost per 1K total tokens (USD). Local providers are free.
_COST_PER_1K: dict[str, float] = {
    "openai": 0.0025,
    "claude": 0.006,
    "gemini": 0.0007,
    "deepseek": 0.00027,
    "openrouter": 0.002,
    "ollama": 0.0,
    "lmstudio": 0.0,
    "vllm": 0.0,
    "custom": 0.0,
}


class AIProviderFactory:
    """Create provider instances and estimate costs."""

    @staticmethod
    def available() -> list[str]:
        return sorted(_REGISTRY.keys())

    @staticmethod
    def create(config: ProviderConfig) -> BaseAIProvider:
        provider_cls = _REGISTRY.get(config.provider.lower())
        if not provider_cls:
            raise ProviderException(f"Unknown provider: {config.provider}")
        return provider_cls(config)

    @staticmethod
    def estimate_cost(provider: str, total_tokens: int) -> float:
        rate = _COST_PER_1K.get(provider.lower(), 0.0)
        return round((total_tokens / 1000.0) * rate, 6)
