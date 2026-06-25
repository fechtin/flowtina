"""Long-term memory models: conversations, raw transcript and distilled memories.

Two storage tiers (see Long-Term Memory Architecture):

* ``conversation_messages`` — verbatim transcript (Tier 1): cheap, append-only,
  used for short-term context and traceability. Safe to rotate.
* ``memories`` — distilled, scored, deduped facts (Tier 2): the real long-term
  recall, retrieved with a small prompt footprint across sessions.

A ``Conversation`` is channel-agnostic: it keys a single end user on a page by
``(page_id, channel, external_user_id)`` so the same person is remembered whether
they reach the page through public comments or Messenger.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BaseModelMixin

# Memory categories (kept as plain strings for SQLite portability).
MEMORY_TYPES = ("semantic", "episodic", "emotional", "relationship")
# Conversation channels.
CHANNEL_COMMENT = "comment"
CHANNEL_MESSENGER = "messenger"


class Conversation(Base, BaseModelMixin):
    """One end user talking to one page through one channel.

    Acts as the per-user memory scope: every transcript message and memory row
    references its ``conversation_id``.
    """

    __tablename__ = "conversations"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    page_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(16), default=CHANNEL_COMMENT, nullable=False)
    # Facebook page-scoped user id (PSID/ASID) — stable per page, our user key.
    external_user_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Consolidation outputs (regenerated nightly from memories).
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConversationMessage(Base, BaseModelMixin):
    """A single verbatim turn (Tier 1 transcript)."""

    __tablename__ = "conversation_messages"

    conversation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Memory(Base, BaseModelMixin):
    """A distilled, scored long-term memory (Tier 2).

    The embedding is stored as a JSON array of floats so semantic search runs as
    an in-process brute-force cosine over one conversation's small memory set —
    no native vector extension required, which keeps the 1GB VM lean.
    """

    __tablename__ = "memories"

    conversation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="semantic", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # How many times this memory has been reinforced (repeated / re-recalled).
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    # JSON-encoded list[float]; dim recorded so a backend swap can be detected.
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_dim: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_decay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
