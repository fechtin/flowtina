"""Content Generator: produce Facebook post, caption, hashtags, and CTA."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.core.logger import get_logger
from app.growth.gateway.gateway import AIGateway

log = get_logger("growth.content")


@dataclass
class GeneratedContent:
    hook: str
    body: str
    caption: str
    cta: str
    hashtags: list[str]
    image_prompt: str
    content_type: str
    language: str


_POST_SYSTEM = """You are an expert social media content creator.
Create engaging Facebook content that drives organic reach and engagement.
Return valid JSON only, no markdown fences."""

_POST_PROMPT = """Generate a Facebook {content_type} for this topic:

Title: {title}
Summary: {summary}
Hook: {hook}
Tone: {tone}
Writing style: {style}
Language: {language}
Target audience: {audience}
Emoji level: {emoji_level}
CTA style: {cta_style}

Return JSON:
{{
  "body": "...",
  "caption": "...",
  "cta": "...",
  "hashtags": ["tag1", "tag2"],
  "image_prompt": "detailed image description for AI image generation"
}}"""

_REEL_SYSTEM = """You are an expert short-form video scriptwriter.
Write an engaging reel script with clear visual directions.
Return valid JSON only."""

_REEL_PROMPT = """Write a {duration}s reel script about:

Title: {title}
Hook: {hook}
Language: {language}
Tone: {tone}
Audience: {audience}

Return JSON:
{{
  "script": "Full voiceover script text",
  "captions": ["line1", "line2"],
  "cta": "...",
  "hashtags": ["tag1", "tag2"],
  "image_prompt": "thumbnail visual description"
}}"""


def _parse_json_content(raw: str) -> dict:
    text = re.sub(r"```[a-z]*", "", raw).strip().strip("`")
    try:
        return json.loads(text)
    except Exception:
        body_match = re.search(r'"body"\s*:\s*"([^"]+)"', raw)
        return {
            "body": body_match.group(1) if body_match else raw[:500],
            "caption": "",
            "cta": "Follow us for more!",
            "hashtags": [],
            "image_prompt": "",
        }


async def generate_post(
    gateway: AIGateway,
    title: str,
    summary: str,
    hook: str,
    content_type: str = "short_post",
    tone: str = "friendly",
    style: str = "conversational",
    language: str = "en",
    audience: str = "general public",
    emoji_level: str = "moderate",
    cta_style: str = "soft",
) -> GeneratedContent:
    import asyncio

    task_type = "reel_script" if content_type == "reel" else "post_generation"

    if content_type == "reel":
        prompt = _REEL_PROMPT.format(
            title=title, hook=hook, language=language, tone=tone, audience=audience, duration=60
        )
        system = _REEL_SYSTEM
    else:
        prompt = _POST_PROMPT.format(
            title=title, summary=summary[:300], hook=hook, tone=tone, style=style,
            language=language, audience=audience, emoji_level=emoji_level, cta_style=cta_style,
            content_type=content_type,
        )
        system = _POST_SYSTEM

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(
        None,
        lambda: gateway.generate(
            task_type=task_type,
            prompt=prompt,
            system_prompt=system,
            use_cache=True,
            max_tokens=2000,
            temperature=0.8,
        ),
    )

    data = _parse_json_content(raw)
    body = data.get("script", data.get("body", ""))
    return GeneratedContent(
        hook=hook,
        body=body,
        caption=data.get("caption", ""),
        cta=data.get("cta", ""),
        hashtags=data.get("hashtags", []),
        image_prompt=data.get("image_prompt", ""),
        content_type=content_type,
        language=language,
    )
