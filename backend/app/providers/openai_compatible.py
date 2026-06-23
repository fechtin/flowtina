"""OpenAI-compatible chat completions provider.

Covers OpenAI, DeepSeek, OpenRouter, Ollama, LM Studio, vLLM and any custom
endpoint that speaks the ``/chat/completions`` protocol. Concrete providers only
need to declare their default base URL.
"""

from __future__ import annotations

from app.providers.base import BaseAIProvider, GenerationResult


class OpenAICompatibleProvider(BaseAIProvider):
    name = "openai_compatible"
    default_base_url = "https://api.openai.com/v1"

    def _resolve_base_url(self) -> str:
        base = (self.config.base_url or self.default_base_url).rstrip("/")
        return base

    def _build_messages(self, prompt: str) -> list[dict]:
        messages: list[dict] = []
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def list_models(self) -> list[str]:
        url = f"{self._resolve_base_url()}/models"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        data = await self._get_json(url, headers)
        items = data.get("data") or data.get("models") or []
        ids = [
            str(m.get("id") or m.get("name"))
            for m in items
            if isinstance(m, dict) and (m.get("id") or m.get("name"))
        ]
        return sorted(set(ids))

    async def generate(self, prompt: str) -> GenerationResult:
        url = f"{self._resolve_base_url()}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = {
            "model": self.config.model,
            "messages": self._build_messages(prompt),
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
        }
        data = await self._post_json(url, headers, payload)
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "") or ""
        usage = data.get("usage") or {}
        return GenerationResult(
            text=text.strip(),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            model=self.config.model,
            provider=self.config.provider,
            raw=data,
        )


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"


class OllamaProvider(OpenAICompatibleProvider):
    name = "ollama"
    default_base_url = "http://localhost:11434/v1"


class LMStudioProvider(OpenAICompatibleProvider):
    name = "lmstudio"
    default_base_url = "http://localhost:1234/v1"


class VLLMProvider(OpenAICompatibleProvider):
    name = "vllm"
    default_base_url = "http://localhost:8001/v1"


class CustomProvider(OpenAICompatibleProvider):
    name = "custom"
    default_base_url = "http://localhost:8000/v1"

    def _resolve_base_url(self) -> str:
        if not self.config.base_url:
            from app.core.exceptions import ProviderException

            raise ProviderException("custom provider requires base_url")
        return self.config.base_url.rstrip("/")
