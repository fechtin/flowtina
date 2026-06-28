"""Image generation via Cloudflare Workers AI (FLUX.1-schnell).

Cloudflare exposes FLUX.1-schnell as a serverless model, so no local GPU is
required. The REST endpoint returns the generated image base64-encoded inside a
JSON body, which we decode to raw bytes for storage. Generation is best-effort:
callers treat a failure (quota exhausted, timeout, unconfigured) as "no image"
rather than failing the surrounding draft.
"""

from __future__ import annotations

import base64

import httpx

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("growth.image")

_API_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
_MAX_PROMPT = 2048  # Cloudflare hard limit for the prompt field.
_MAX_STEPS = 8  # FLUX.1-schnell accepts 1..8 inference steps.


class ImageGenerationError(RuntimeError):
    """Raised when Cloudflare image generation fails or returns no image."""


async def generate_image(prompt: str) -> bytes:
    """Generate an image from ``prompt`` via Cloudflare FLUX.1-schnell.

    Returns the raw image bytes (JPEG). Raises :class:`ImageGenerationError`
    when the feature is unconfigured or the API call fails, so callers can
    degrade to a text-only draft.
    """
    account_id = settings.cloudflare_account_id.strip()
    api_token = settings.cloudflare_api_token.strip()
    if not account_id or not api_token:
        raise ImageGenerationError("Cloudflare credentials are not configured")

    clean_prompt = (prompt or "").strip()[:_MAX_PROMPT]
    if not clean_prompt:
        raise ImageGenerationError("Empty image prompt")

    url = _API_TEMPLATE.format(account_id=account_id, model=settings.flux_model)
    steps = max(1, min(settings.flux_steps, _MAX_STEPS))
    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_token}"},
                json={"prompt": clean_prompt, "steps": steps},
            )
    except httpx.HTTPError as exc:
        raise ImageGenerationError(f"Cloudflare request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise ImageGenerationError(
            f"Cloudflare HTTP {resp.status_code}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise ImageGenerationError(f"Cloudflare returned non-JSON: {exc}") from exc

    image_b64 = (data.get("result") or {}).get("image")
    if not image_b64:
        raise ImageGenerationError("Cloudflare response contained no image")
    try:
        return base64.b64decode(image_b64)
    except (ValueError, TypeError) as exc:
        raise ImageGenerationError(f"Invalid base64 image: {exc}") from exc
