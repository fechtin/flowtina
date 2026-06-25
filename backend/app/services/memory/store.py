"""In-process memory store: embed, dedupe, persist and rank memories.

Semantic search is a brute-force cosine over one conversation's active memories.
Per-user sets are small (deduped + archived beyond a cap), so this stays well
under a millisecond and needs no native vector extension.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.memory import Memory
from app.repositories.repositories import MemoryRepository
from app.services.memory.embeddings import EmbeddingProvider, cosine_similarity

# Recall ranking weights (architecture §8).
_W_SEMANTIC = 0.40
_W_RECENCY = 0.30
_W_IMPORTANCE = 0.20
_W_RELATIONSHIP = 0.10
# Recency half-life in days for the exponential recency term.
_RECENCY_TAU_DAYS = 30.0


@dataclass
class MemoryCandidate:
    """A memory proposed by extraction, before dedupe/scoring decides its fate."""

    type: str
    content: str
    importance: int
    reason: str | None = None


def _encode(vector: list[float]) -> str:
    return json.dumps([round(v, 6) for v in vector])


def _decode(raw: str | None) -> list[float]:
    if not raw:
        return []
    try:
        return [float(v) for v in json.loads(raw)]
    except (ValueError, TypeError):
        return []


def _age_days(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    created = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - created).total_seconds() / 86400.0)


class MemoryStore:
    """Persist and retrieve distilled memories for a single conversation scope."""

    def __init__(self, db: Session, embedder: EmbeddingProvider) -> None:
        self.db = db
        self.memories = MemoryRepository(db)
        self.embedder = embedder

    async def save(self, conversation_id: str, candidate: MemoryCandidate) -> Memory | None:
        """Store a candidate, merging into a near-duplicate when one exists.

        Returns the stored/updated row, or ``None`` if the content is empty.
        """
        content = (candidate.content or "").strip()
        if not content:
            return None

        embedding = await self.embedder.embed(content)
        match = self._find_similar(conversation_id, embedding)
        if match is not None:
            existing, _similarity = match
            return self._merge(existing, candidate, content, embedding)

        return self.memories.create(
            conversation_id=conversation_id,
            type=candidate.type if candidate.type in {"semantic", "episodic", "emotional", "relationship"} else "semantic",
            content=content,
            importance=max(0, min(100, candidate.importance)),
            reason=candidate.reason,
            embedding=_encode(embedding),
            embedding_dim=len(embedding),
        )

    def _merge(
        self, existing: Memory, candidate: MemoryCandidate, content: str, embedding: list[float]
    ) -> Memory:
        """Reinforce a near-duplicate: keep richer content, bump count, max importance."""
        existing.hit_count += 1
        existing.importance = max(existing.importance, max(0, min(100, candidate.importance)))
        if len(content) > len(existing.content or ""):
            existing.content = content
            existing.embedding = _encode(embedding)
            existing.embedding_dim = len(embedding)
        self.db.flush()
        return existing

    def _find_similar(
        self, conversation_id: str, embedding: list[float]
    ) -> tuple[Memory, float] | None:
        """Return the most similar active memory above the dedupe threshold."""
        best: Memory | None = None
        best_sim = 0.0
        for memory in self.memories.list_active(conversation_id):
            sim = cosine_similarity(embedding, _decode(memory.embedding))
            if sim > best_sim:
                best, best_sim = memory, sim
        if best is not None and best_sim >= settings.memory_dedupe_similarity:
            return best, best_sim
        return None

    async def retrieve(
        self, conversation_id: str, query_text: str, limit: int | None = None
    ) -> list[Memory]:
        """Rank active memories for relevance to ``query_text`` and return the top set."""
        active = self.memories.list_active(conversation_id)
        if not active:
            return []
        limit = limit or settings.memory_retrieval_limit
        query_embedding = await self.embedder.embed(query_text) if query_text else []

        scored = [(self._score(memory, query_embedding), memory) for memory in active]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = [memory for _score, memory in scored[:limit]]

        for memory in top:
            memory.hit_count += 1
        self.db.flush()
        return top

    @staticmethod
    def _recency(memory: Memory) -> float:
        return math.exp(-_age_days(memory.created_at) / _RECENCY_TAU_DAYS)

    def _score(self, memory: Memory, query_embedding: list[float]) -> float:
        semantic = (
            cosine_similarity(query_embedding, _decode(memory.embedding))
            if query_embedding
            else 0.0
        )
        relationship = 1.0 if memory.type in {"relationship", "emotional"} else 0.0
        return (
            _W_SEMANTIC * semantic
            + _W_RECENCY * self._recency(memory)
            + _W_IMPORTANCE * (memory.importance / 100.0)
            + _W_RELATIONSHIP * relationship
        )
