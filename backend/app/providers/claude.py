"""Anthropic Claude provider (Messages API)."""

from __future__ import annotations

from app.providers.base import BaseAIProvider, GenerationResult


class ClaudeProvider(BaseAIProvider):
    name = "claude"
    default_base_url = "https://api.anthropic.com/v1"
    api_version = "2023-06-01"

    async def generate(self, prompt: str) -> GenerationResult:
        base = (self.config.base_url or self.default_base_url).rstrip("/")
        url = f"{base}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key or "",
            "anthropic-version": self.api_version,
        }
        payload: dict = {
            "model": self.config.model or "claude-sonnet-4-6",
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.config.system_prompt:
            payload["system"] = self.config.system_prompt

        data = await self._post_json(url, headers, payload)
        blocks = data.get("content") or [{}]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        return GenerationResult(
            text=text.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=payload["model"],
            provider=self.config.provider,
            raw=data,
        )
