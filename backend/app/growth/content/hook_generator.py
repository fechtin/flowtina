"""Hook Generator: produce multiple hooks, self-evaluate, return the best one.

Uses a single AI call with batch evaluation to minimize API calls.
"""

from __future__ import annotations

import json
import re

from app.core.logger import get_logger
from app.growth.gateway.gateway import AIGateway

log = get_logger("growth.hook")

_HOOK_SYSTEM = """You are an expert social media copywriter.
Generate {count} distinct, attention-grabbing hooks for a Facebook post.
Then evaluate each on a scale 1-10 for: virality, clarity, emotion, curiosity.
Return JSON: {{"hooks": [{{"text": "...", "score": 8.5, "reason": "..."}}]}}
Ordered best first. Return only the JSON, no markdown."""

_HOOK_PROMPT = """Topic: {title}
Summary: {summary}
Tone: {tone}
Language: {language}
Target audience: {audience}
Content format: {content_format}"""


def _parse_hooks(raw: str) -> list[dict]:
    try:
        text = re.sub(r"```[a-z]*", "", raw).strip().strip("`")
        data = json.loads(text)
        return data.get("hooks", [])
    except Exception:
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.strip().startswith("{")]
        return [{"text": l, "score": 5.0, "reason": ""} for l in lines[:5]]


async def generate_best_hook(
    gateway: AIGateway,
    title: str,
    summary: str,
    tone: str = "friendly",
    language: str = "en",
    audience: str = "general public",
    content_format: str = "short_post",
    candidates: int = 10,
) -> str:
    prompt = _HOOK_PROMPT.format(
        title=title,
        summary=summary[:300],
        tone=tone,
        language=language,
        audience=audience,
        content_format=content_format,
    )
    system = _HOOK_SYSTEM.format(count=candidates)

    import asyncio
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(
        None,
        lambda: gateway.generate(
            task_type="hook_generation",
            prompt=prompt,
            system_prompt=system,
            use_cache=True,
            max_tokens=1500,
            temperature=0.9,
        ),
    )
    hooks = _parse_hooks(raw)
    if not hooks:
        return f"You won't believe what happened with {title}..."
    best = max(hooks, key=lambda h: float(h.get("score", 0)))
    return best["text"]
