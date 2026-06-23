"""Text helpers: hashing, post-processing and lightweight quality scoring."""

from __future__ import annotations

import hashlib
import re

_HASHTAG_RE = re.compile(r"#\w+")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]",
    flags=re.UNICODE,
)


def content_hash(text: str) -> str:
    """SHA-256 hash of normalized content for deduplication."""
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clean_content(text: str) -> str:
    """Normalize spacing and trim markdown artifacts."""
    text = (text or "").replace("\r\n", "\n").strip()
    text = _MULTISPACE_RE.sub(" ", text)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def normalize_hashtags(text: str, max_tags: int = 10) -> str:
    """Extract unique hashtags, preserving order, capped at ``max_tags``."""
    seen: list[str] = []
    for tag in _HASHTAG_RE.findall(text or ""):
        lowered = tag.lower()
        if lowered not in seen:
            seen.append(lowered)
    return " ".join(seen[:max_tags])


def count_words(text: str) -> int:
    return len((text or "").split())


def count_emojis(text: str) -> int:
    return len(_EMOJI_RE.findall(text or ""))


def score_quality(text: str, *, min_words: int = 20, max_words: int = 2000) -> int:
    """Heuristic 0-100 content quality score.

    Combines length adequacy, emoji moderation and structure. No external calls.
    """
    if not text or not text.strip():
        return 0
    words = count_words(text)
    score = 100

    if words < min_words:
        score -= min(60, (min_words - words) * 3)
    if words > max_words:
        score -= 20

    emojis = count_emojis(text)
    if emojis > 15:
        score -= 15

    # Penalize obviously repetitive content.
    unique_ratio = len(set(text.split())) / max(1, words)
    if unique_ratio < 0.4:
        score -= 25

    return max(0, min(100, score))
