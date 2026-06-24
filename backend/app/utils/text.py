"""Text helpers: hashing, post-processing and lightweight quality scoring."""

from __future__ import annotations

import hashlib
import re

_HASHTAG_RE = re.compile(r"#\w+")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")
# Chain-of-thought blocks emitted by reasoning models (Qwen, DeepSeek-R1, ...).
_REASONING_RE = re.compile(
    r"<(think|thinking|reasoning)>.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)
_OPEN_REASONING_RE = re.compile(
    r"^\s*<(think|thinking|reasoning)>",
    flags=re.IGNORECASE,
)
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]",
    flags=re.UNICODE,
)

# --- Markdown stripping (Facebook renders plain text only) ---
_CODE_FENCE_RE = re.compile(r"^\s*```[^\n]*$", flags=re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
# A horizontal rule: a line of 3+ repeats of -, * or _ (optionally spaced).
_HR_RE = re.compile(r"^\s{0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$", flags=re.MULTILINE)
# ATX heading marker; requires whitespace after the #'s so "#hashtag" survives.
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}[ \t]+", flags=re.MULTILINE)
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>[ \t]?", flags=re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
# Emphasis: *, ** or *** wrapping non-space-bounded text (protects "2 * 3" and "* bullet").
_ASTERISK_EMPHASIS_RE = re.compile(r"(\*{1,3})(\S(?:.*?\S)?)\1")
# Bold via double underscore; single _ is left alone to spare snake_case and URLs.
_UNDERSCORE_BOLD_RE = re.compile(r"__(\S(?:.*?\S)?)__")


def content_hash(text: str) -> str:
    """SHA-256 hash of normalized content for deduplication."""
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def strip_reasoning(text: str) -> str:
    """Remove chain-of-thought blocks from reasoning models' output.

    Handles closed ``<think>...</think>`` blocks and an unterminated leading
    ``<think>`` (truncated output, where the whole response is reasoning).
    """
    if not text:
        return text
    cleaned = _REASONING_RE.sub("", text)
    if _OPEN_REASONING_RE.match(cleaned):
        return ""
    return cleaned.strip()


def clean_content(text: str) -> str:
    """Normalize spacing and trim markdown artifacts."""
    text = (text or "").replace("\r\n", "\n").strip()
    text = _MULTISPACE_RE.sub(" ", text)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _link_replacement(match: re.Match[str]) -> str:
    text, url = match.group(1).strip(), match.group(2).strip()
    if not text or text == url:
        return url
    return f"{text} ({url})"


def strip_markdown(text: str) -> str:
    """Flatten Markdown to plain text for Facebook, which renders no formatting.

    Removes emphasis (**bold**, *italic*, __bold__), ATX headings, horizontal
    rules, blockquote markers, inline code and code fences, and rewrites
    ``[label](url)`` links to ``label (url)``. Intended for post *content*; do
    not run it over a hashtags string, whose leading ``#`` it must not touch.
    """
    if not text:
        return text
    text = text.replace("\r\n", "\n")
    text = _CODE_FENCE_RE.sub("", text)
    text = _HR_RE.sub("", text)
    text = _HEADING_RE.sub("", text)
    text = _BLOCKQUOTE_RE.sub("", text)
    text = _LINK_RE.sub(_link_replacement, text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _ASTERISK_EMPHASIS_RE.sub(r"\2", text)
    text = _UNDERSCORE_BOLD_RE.sub(r"\1", text)
    return clean_content(text)


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
