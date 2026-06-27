"""Image description via Groq vision models.

Calls Groq's vision-capable models to produce a plain-text description of an
image URL. The description is injected into the text prompt so a text-only
model can respond meaningfully to image DMs.

Primary model:  meta-llama/llama-4-scout-17b-16e-instruct
Fallback model: meta-llama/llama-4-maverick-17b-128e-instruct
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("facebook")

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]
_DESCRIBE_PROMPT = (
    "Describe this image in detail. Focus on what you see: objects, people, "
    "text, colors, context, and any notable details. Be concise but thorough."
)


async def describe_image(image_url: str, api_key: str | None = None) -> str | None:
    """Return a plain-text description of *image_url* using a Groq vision model.

    *api_key* should be the Groq key resolved from the DB (UserSettings).
    Falls back to the env-configured ``GROQ_API_KEY`` when not supplied.
    Returns ``None`` when no key is available or all models fail.
    """
    api_key = api_key or settings.groq_api_key
    if not api_key:
        log.debug("vision_service: groq_api_key not configured, skipping image analysis")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload_base = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _DESCRIBE_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "max_tokens": 512,
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        for model in _VISION_MODELS:
            payload = {**payload_base, "model": model}
            try:
                resp = await client.post(_GROQ_CHAT_URL, headers=headers, json=payload)
                if resp.status_code == 429:
                    log.debug(f"vision_service: {model} rate-limited, trying next")
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = (
                    (data.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    or ""
                ).strip()
                if text:
                    log.debug(f"vision_service: described image with {model}")
                    return text
            except Exception as exc:  # noqa: BLE001
                log.warning(f"vision_service: {model} failed: {exc}")

    return None
