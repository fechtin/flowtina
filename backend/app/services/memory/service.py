"""MemoryService: orchestrates transcript, recall, extraction and consolidation.

Channel-agnostic. The comment engagement flow (and, later, Messenger) calls:

1. :meth:`get_conversation` to resolve the per-user scope,
2. :meth:`build_context` before generating a reply,
3. :meth:`record_exchange` after replying (stores transcript + extracts memories).

Nightly, :meth:`consolidate` decays stale memories and regenerates summaries.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.models.memory import Conversation
from app.prompts.defaults import (
    DEFAULT_MEMORY_EXTRACTION_PROMPT,
    DEFAULT_PROFILE_SUMMARY_PROMPT,
    DEFAULT_RELATIONSHIP_SUMMARY_PROMPT,
)
from app.prompts.engine import prompt_engine
from app.repositories.repositories import (
    ConversationMessageRepository,
    ConversationRepository,
    MemoryRepository,
)
from app.services.ai_service import AIService
from app.services.memory.embeddings import get_embedding_provider
from app.services.memory.store import MemoryCandidate, MemoryStore

log = get_logger("ai")

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
# Per-week importance decay for non-emotional/relationship memories (§9).
_DECAY_FACTOR = 0.98
_DECAY_INTERVAL_DAYS = 7


def _estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


class MemoryService:
    """Glue between conversations, the memory store and the AI provider."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = ConversationMessageRepository(db)
        self.memory_repo = MemoryRepository(db)
        self.ai = AIService(db)
        self.store = MemoryStore(db, get_embedding_provider())

    # --- conversation scope ---

    def get_conversation(
        self,
        *,
        project_id: str,
        page_id: str,
        channel: str,
        external_user_id: str,
        user_name: str | None = None,
    ) -> Conversation:
        return self.conversations.get_or_create(
            project_id=project_id,
            page_id=page_id,
            channel=channel,
            external_user_id=external_user_id,
            user_name=user_name,
        )

    # --- recall (before reply) ---

    async def build_context(self, conversation: Conversation, query_text: str) -> dict[str, str]:
        """Return ``{memory_context, history}`` strings for the reply prompt."""
        memories = await self.store.retrieve(conversation.id, query_text)
        lines: list[str] = []
        if conversation.profile_summary:
            lines.append(f"Profile: {conversation.profile_summary}")
        if conversation.relationship_summary:
            lines.append(f"Relationship: {conversation.relationship_summary}")
        lines += [f"- [{m.type}] {m.content}" for m in memories]
        memory_context = "\n".join(lines) if lines else "(nothing yet)"

        turns = self.messages.recent(conversation.id, settings.memory_history_turns)
        history = "\n".join(
            f"{'Follower' if m.role == 'user' else 'Page'}: {m.content}"
            for m in reversed(turns)
        )
        return {"memory_context": memory_context, "history": history or "(first message)"}

    def has_context(self, conversation: Conversation) -> bool:
        """True if we already remember this follower (drives prompt selection)."""
        return bool(
            conversation.message_count
            or conversation.profile_summary
            or self.memory_repo.count(conversation_id=conversation.id, archived=False)
        )

    # --- transcript + extraction (after reply) ---

    async def record_exchange(
        self, conversation: Conversation, user_text: str, assistant_text: str
    ) -> None:
        """Persist both turns and asynchronously distill durable memories.

        Best-effort: a failure here never breaks the reply that already went out.
        """
        self._append_message(conversation, "user", user_text)
        self._append_message(conversation, "assistant", assistant_text)
        conversation.last_message_at = datetime.now(timezone.utc)
        self.db.flush()
        try:
            await self._extract(conversation, user_text, assistant_text)
        except Exception as exc:  # noqa: BLE001 - extraction is best-effort
            log.warning(f"memory extraction failed for {conversation.id}: {exc}")

    def _append_message(self, conversation: Conversation, role: str, content: str) -> None:
        text = (content or "").strip()
        if not text:
            return
        self.messages.create(
            conversation_id=conversation.id,
            role=role,
            content=text,
            tokens=_estimate_tokens(text),
        )
        conversation.message_count += 1

    async def _extract(self, conversation: Conversation, user_text: str, assistant_text: str) -> None:
        exchange = f"Follower: {user_text}\nPage: {assistant_text}"
        prompt = prompt_engine.render(
            DEFAULT_MEMORY_EXTRACTION_PROMPT,
            {"user_name": conversation.user_name or "the follower", "exchange": exchange[:2000]},
        )
        result = await self.ai.generate(conversation.project_id, prompt)
        for candidate in self._parse_candidates(result.text):
            if self._should_save(candidate):
                await self.store.save(conversation.id, candidate)
        self.db.flush()

    @staticmethod
    def _parse_candidates(raw: str) -> list[MemoryCandidate]:
        match = _JSON_RE.search(raw or "")
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except (ValueError, TypeError):
            return []
        candidates: list[MemoryCandidate] = []
        for item in data.get("memories", []) or []:
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            candidates.append(
                MemoryCandidate(
                    type=str(item.get("type", "semantic")).lower(),
                    content=content,
                    importance=int(item.get("importance", 0) or 0),
                    reason=str(item.get("reason", "")).strip() or None,
                )
            )
        return candidates

    @staticmethod
    def _should_save(candidate: MemoryCandidate) -> bool:
        return (
            candidate.importance >= settings.memory_save_threshold
            or candidate.type in {"emotional", "relationship"}
        )

    # --- consolidation (nightly) ---

    async def consolidate(self, conversation: Conversation) -> None:
        """Decay stale memories, archive overflow and regenerate summaries."""
        self._apply_decay(conversation)
        self._archive_overflow(conversation)
        await self._refresh_summaries(conversation)
        self.db.flush()

    def _apply_decay(self, conversation: Conversation) -> None:
        now = datetime.now(timezone.utc)
        for memory in self.memory_repo.list_active(conversation.id):
            if memory.type in {"emotional", "relationship"}:
                continue
            last = memory.last_decay_at
            if last and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last and (now - last).days < _DECAY_INTERVAL_DAYS:
                continue
            memory.importance = max(1, int(memory.importance * _DECAY_FACTOR))
            memory.last_decay_at = now

    def _archive_overflow(self, conversation: Conversation) -> None:
        active = self.memory_repo.list_active(conversation.id)
        if len(active) <= settings.memory_archive_cap:
            return
        # Lowest importance first; never archive the strongest memories.
        active.sort(key=lambda m: m.importance)
        for memory in active[: len(active) - settings.memory_archive_cap]:
            if memory.importance <= 85:
                memory.archived = True

    async def _refresh_summaries(self, conversation: Conversation) -> None:
        active = self.memory_repo.list_active(conversation.id)
        if not active:
            return
        facts = "\n".join(f"- [{m.type}] {m.content}" for m in active)
        bonds = "\n".join(
            f"- [{m.type}] {m.content}" for m in active if m.type in {"emotional", "relationship"}
        )
        profile = await self.ai.generate(
            conversation.project_id,
            prompt_engine.render(DEFAULT_PROFILE_SUMMARY_PROMPT, {"memories": facts[:4000]}),
        )
        conversation.profile_summary = profile.text.strip()[:1500]
        if bonds:
            rel = await self.ai.generate(
                conversation.project_id,
                prompt_engine.render(DEFAULT_RELATIONSHIP_SUMMARY_PROMPT, {"memories": bonds[:4000]}),
            )
            conversation.relationship_summary = rel.text.strip()[:1500]
