"""AI Review: quality check before content is approved/published.

Checks: grammar, brand consistency, duplicate, sensitive content, readability, engagement prediction.
Uses AI for the combined review in one call to minimize costs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.growth.content.content_generator import GeneratedContent
from app.growth.gateway.gateway import AIGateway
from app.growth.models import ContentDraft

log = get_logger("growth.review")


@dataclass
class ReviewResult:
    passed: bool
    score: int
    grammar_ok: bool
    brand_ok: bool
    duplicate: bool
    sensitive: bool
    readability_score: int
    engagement_score: int
    notes: str


_REVIEW_SYSTEM = """You are a senior content quality reviewer for social media.
Evaluate the given Facebook content. Return JSON only."""

_REVIEW_PROMPT = """Review this Facebook content:

Hook: {hook}
Body: {body}
Hashtags: {hashtags}
Language: {language}
Brand personality: {brand_personality}
Forbidden topics: {forbidden_topics}

Return JSON:
{{
  "grammar_ok": true,
  "brand_ok": true,
  "duplicate": false,
  "sensitive": false,
  "readability_score": 80,
  "engagement_score": 75,
  "overall_score": 77,
  "notes": "..."
}}

All scores 0-100. Be strict. If sensitive is true, overall_score must be 0."""


def _quick_checks(content: GeneratedContent, blocked_keywords: list[str]) -> tuple[bool, str]:
    combined = f"{content.hook} {content.body}".lower()
    for kw in blocked_keywords:
        if kw.lower() in combined:
            return False, f"Blocked keyword detected: {kw}"
    if len(content.body.strip()) < 20:
        return False, "Content body too short"
    return True, ""


async def review_content(
    gateway: AIGateway,
    content: GeneratedContent,
    brand_personality: str = "",
    forbidden_topics: str = "",
    blocked_keywords: list[str] | None = None,
    quality_threshold: int = 60,
) -> ReviewResult:
    import asyncio

    passed, quick_note = _quick_checks(content, blocked_keywords or [])
    if not passed:
        return ReviewResult(
            passed=False, score=0, grammar_ok=True, brand_ok=False, duplicate=False,
            sensitive=True, readability_score=0, engagement_score=0, notes=quick_note,
        )

    prompt = _REVIEW_PROMPT.format(
        hook=content.hook[:200],
        body=content.body[:800],
        hashtags=", ".join(content.hashtags[:10]),
        language=content.language,
        brand_personality=brand_personality or "friendly and professional",
        forbidden_topics=forbidden_topics or "none",
    )

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(
        None,
        lambda: gateway.generate(
            task_type="content_review",
            prompt=prompt,
            system_prompt=_REVIEW_SYSTEM,
            use_cache=False,
            max_tokens=512,
            temperature=0.2,
        ),
    )

    try:
        text = re.sub(r"```[a-z]*", "", raw).strip().strip("`")
        data = json.loads(text)
    except Exception:
        data = {}

    score = int(data.get("overall_score", 50))
    sensitive = bool(data.get("sensitive", False))
    return ReviewResult(
        passed=score >= quality_threshold and not sensitive,
        score=score,
        grammar_ok=bool(data.get("grammar_ok", True)),
        brand_ok=bool(data.get("brand_ok", True)),
        duplicate=bool(data.get("duplicate", False)),
        sensitive=sensitive,
        readability_score=int(data.get("readability_score", 50)),
        engagement_score=int(data.get("engagement_score", 50)),
        notes=str(data.get("notes", "")),
    )


def check_duplicate_in_db(db: Session, page_id: str, content_body: str, threshold: float = 0.7) -> bool:
    """Simple hash-based duplicate check against recent drafts."""
    recent = (
        db.query(ContentDraft)
        .filter(ContentDraft.page_id == page_id)
        .order_by(ContentDraft.created_at.desc())
        .limit(50)
        .all()
    )
    words_new = set(re.findall(r"\b\w{4,}\b", content_body.lower()))
    for draft in recent:
        if not draft.body:
            continue
        words_old = set(re.findall(r"\b\w{4,}\b", draft.body.lower()))
        if words_new and words_old:
            overlap = len(words_new & words_old) / len(words_new | words_old)
            if overlap >= threshold:
                return True
    return False
