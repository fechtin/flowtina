"""Model Router: select the appropriate provider+model based on task type.

Cost tiers (cheapest first):
  cheap   → smallest/free model (grammar, classification)
  medium  → balanced model (hook generation, short content)
  best    → most capable model (long scripts, reel scripts)
"""

from __future__ import annotations

from dataclasses import dataclass

TASK_TIERS: dict[str, str] = {
    "classification": "cheap",
    "grammar_fix": "cheap",
    "duplicate_check": "cheap",
    "keyword_extraction": "cheap",
    "topic_cluster": "cheap",
    "sentiment": "cheap",
    "hook_generation": "medium",
    "caption_generation": "medium",
    "hashtag_generation": "medium",
    "cta_generation": "medium",
    "content_review": "medium",
    "post_generation": "medium",
    "reel_script": "best",
    "long_content": "best",
    "brand_review": "best",
}

_PROVIDER_TIERS: dict[str, dict[str, tuple[str, str]]] = {
    "groq": {
        "cheap": ("groq", "llama-3.1-8b-instant"),
        "medium": ("groq", "llama-3.3-70b-versatile"),
        "best": ("groq", "qwen/qwen3-32b"),
    },
    "gemini": {
        "cheap": ("gemini", "gemini-1.5-flash-8b"),
        "medium": ("gemini", "gemini-1.5-flash"),
        "best": ("gemini", "gemini-1.5-pro"),
    },
    "openai": {
        "cheap": ("openai", "gpt-4o-mini"),
        "medium": ("openai", "gpt-4o-mini"),
        "best": ("openai", "gpt-4o"),
    },
    "claude": {
        "cheap": ("claude", "claude-haiku-4-5-20251001"),
        "medium": ("claude", "claude-sonnet-4-6"),
        "best": ("claude", "claude-opus-4-8"),
    },
    "deepseek": {
        "cheap": ("deepseek", "deepseek-chat"),
        "medium": ("deepseek", "deepseek-chat"),
        "best": ("deepseek", "deepseek-reasoner"),
    },
}

_DEFAULT_PROVIDER = "groq"


@dataclass
class RouteDecision:
    provider: str
    model: str
    tier: str
    task_type: str


class ModelRouter:
    """Map a task type to the cheapest appropriate provider+model."""

    def __init__(self, preferred_provider: str | None = None) -> None:
        self.preferred_provider = (preferred_provider or _DEFAULT_PROVIDER).lower()

    def route(self, task_type: str) -> RouteDecision:
        tier = TASK_TIERS.get(task_type, "medium")
        provider_key = self.preferred_provider
        if provider_key not in _PROVIDER_TIERS:
            provider_key = _DEFAULT_PROVIDER
        provider, model = _PROVIDER_TIERS[provider_key][tier]
        return RouteDecision(provider=provider, model=model, tier=tier, task_type=task_type)

    def route_with_fallback(self, task_type: str) -> list[RouteDecision]:
        """Return an ordered list of fallback decisions for a task."""
        tier = TASK_TIERS.get(task_type, "medium")
        decisions: list[RouteDecision] = []
        for provider_key, tiers in _PROVIDER_TIERS.items():
            p, m = tiers[tier]
            decisions.append(RouteDecision(provider=p, model=m, tier=tier, task_type=task_type))
        return decisions
