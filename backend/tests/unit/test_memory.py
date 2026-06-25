"""Unit tests for the long-term memory subsystem."""

from __future__ import annotations

import asyncio

from app.models.memory import CHANNEL_COMMENT
from app.providers.base import GenerationResult
from app.repositories.repositories import (
    ConversationMessageRepository,
    MemoryRepository,
)
from app.services.memory.embeddings import (
    HashEmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
)
from app.services.memory.service import MemoryService
from app.services.memory.store import MemoryCandidate, MemoryStore


# --- embeddings ---


def test_hash_embedding_is_deterministic_and_normalized():
    provider = HashEmbeddingProvider(dim=256)
    a = asyncio.run(provider.embed("I love pho and coffee"))
    b = asyncio.run(provider.embed("I love pho and coffee"))
    assert a == b
    assert len(a) == 256
    assert abs(sum(v * v for v in a) - 1.0) < 1e-6  # unit length


def test_hash_embedding_groups_similar_text():
    provider = HashEmbeddingProvider(dim=256)
    base = asyncio.run(provider.embed("I work as a software engineer in Hanoi"))
    similar = asyncio.run(provider.embed("I am a software engineer working in Hanoi"))
    different = asyncio.run(provider.embed("My cat likes to sleep all day"))
    assert cosine_similarity(base, similar) > cosine_similarity(base, different)


def test_cosine_similarity_edges():
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9


def test_embedding_factory_defaults_to_hash(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "memory_embedding_provider", "hash")
    assert isinstance(get_embedding_provider(), HashEmbeddingProvider)


# --- store: dedupe + retrieval ---


def _store(db) -> MemoryStore:
    return MemoryStore(db, HashEmbeddingProvider(dim=256))


def test_store_dedupes_near_identical_memory(db_session):
    store = _store(db_session)
    cid = "conv-1"
    first = asyncio.run(
        store.save(cid, MemoryCandidate(type="semantic", content="Likes pho", importance=70))
    )
    again = asyncio.run(
        store.save(cid, MemoryCandidate(type="semantic", content="Likes pho", importance=80))
    )
    db_session.flush()
    assert first.id == again.id  # merged, not duplicated
    assert again.hit_count == 1
    assert again.importance == 80  # keeps the max
    assert MemoryRepository(db_session).count(conversation_id=cid) == 1


def test_store_keeps_distinct_memories(db_session):
    store = _store(db_session)
    cid = "conv-2"
    asyncio.run(store.save(cid, MemoryCandidate(type="semantic", content="Works in marketing", importance=70)))
    asyncio.run(store.save(cid, MemoryCandidate(type="episodic", content="Just adopted a puppy", importance=70)))
    assert MemoryRepository(db_session).count(conversation_id=cid) == 2


def test_store_retrieve_ranks_relevant_first(db_session):
    store = _store(db_session)
    cid = "conv-3"
    asyncio.run(store.save(cid, MemoryCandidate(type="semantic", content="Loves hiking in the mountains", importance=65)))
    asyncio.run(store.save(cid, MemoryCandidate(type="semantic", content="Allergic to peanuts", importance=65)))
    results = asyncio.run(store.retrieve(cid, "any good mountain hiking trails?", limit=2))
    assert results
    assert "hiking" in results[0].content.lower()


# --- service: parsing, save rules, exchange, consolidation ---


class _FakeAI:
    """Stand-in for AIService that returns canned text without calling a provider."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def generate(self, project_id: str, prompt: str) -> GenerationResult:
        return GenerationResult(text=self._text)


def test_parse_candidates_handles_fenced_json():
    raw = (
        "Sure!\n```json\n"
        '{"memories": [{"type": "semantic", "content": "Likes tea", "importance": 70, "reason": "stated"}]}'
        "\n```"
    )
    candidates = MemoryService._parse_candidates(raw)
    assert len(candidates) == 1
    assert candidates[0].content == "Likes tea"
    assert candidates[0].importance == 70


def test_parse_candidates_tolerates_garbage():
    assert MemoryService._parse_candidates("no json here") == []


def test_should_save_rules():
    assert MemoryService._should_save(MemoryCandidate("semantic", "x", 60))
    assert not MemoryService._should_save(MemoryCandidate("semantic", "x", 30))
    # Emotional/relationship are always kept regardless of score.
    assert MemoryService._should_save(MemoryCandidate("emotional", "x", 10))
    assert MemoryService._should_save(MemoryCandidate("relationship", "x", 5))


def test_record_exchange_stores_transcript_and_memory(db_session):
    service = MemoryService(db_session)
    service.ai = _FakeAI(
        '{"memories": [{"type": "semantic", "content": "Runs a coffee shop", "importance": 75}]}'
    )
    conv = service.get_conversation(
        project_id="proj-1",
        page_id="page-1",
        channel=CHANNEL_COMMENT,
        external_user_id="fb-user-1",
        user_name="Mai",
    )
    asyncio.run(service.record_exchange(conv, "Hi, I run a coffee shop downtown", "How lovely!"))
    db_session.flush()

    assert conv.message_count == 2
    msgs = ConversationMessageRepository(db_session).list(conversation_id=conv.id)
    assert {m.role for m in msgs} == {"user", "assistant"}
    mems = MemoryRepository(db_session).list_active(conv.id)
    assert any("coffee shop" in m.content.lower() for m in mems)


def test_consolidate_decays_and_summarizes(db_session):
    service = MemoryService(db_session)
    service.ai = _FakeAI("A concise profile summary.")
    conv = service.get_conversation(
        project_id="proj-1",
        page_id="page-1",
        channel=CHANNEL_COMMENT,
        external_user_id="fb-user-2",
    )
    mem = MemoryRepository(db_session).create(
        conversation_id=conv.id, type="semantic", content="Likes jazz", importance=50, embedding="[]"
    )
    db_session.flush()
    asyncio.run(service.consolidate(conv))
    db_session.flush()

    assert mem.importance == 49  # decayed 50 * 0.98 -> 49
    assert mem.last_decay_at is not None
    assert conv.profile_summary == "A concise profile summary."
