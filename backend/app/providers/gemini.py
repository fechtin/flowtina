"""Google Gemini provider (Generative Language API)."""

from __future__ import annotations

from app.providers.base import BaseAIProvider, GenerationResult


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, prompt: str) -> GenerationResult:
        base = (self.config.base_url or self.default_base_url).rstrip("/")
        model = self.config.model or "gemini-1.5-flash"
        url = f"{base}/models/{model}:generateContent?key={self.config.api_key or ''}"
        headers = {"Content-Type": "application/json"}

        parts_text = prompt
        if self.config.system_prompt:
            parts_text = f"{self.config.system_prompt}\n\n{prompt}"

        payload = {
            "contents": [{"parts": [{"text": parts_text}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "topP": self.config.top_p,
                "maxOutputTokens": self.config.max_tokens,
            },
        }
        data = await self._post_json(url, headers, payload)
        candidates = data.get("candidates") or [{}]
        content = (candidates[0].get("content") or {}).get("parts") or [{}]
        text = content[0].get("text", "") or ""
        usage = data.get("usageMetadata") or {}
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))
        return GenerationResult(
            text=text.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=int(usage.get("totalTokenCount", prompt_tokens + completion_tokens)),
            model=model,
            provider=self.config.provider,
            raw=data,
        )
