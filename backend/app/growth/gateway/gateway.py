"""AI Gateway: single entry point for all AI calls from the Growth Engine.

Responsibilities:
- Provider selection via ModelRouter
- Quota enforcement via QuotaManager
- Prompt caching via PromptCache
- Automatic fallback across providers
- Batch processing support
- Logging and cost tracking
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ProviderException
from app.core.logger import get_logger
from app.core.security import decrypt_secret
from app.models.project import AIProvider
from app.providers.base import GenerationResult, ProviderConfig
from app.providers.factory import AIProviderFactory
from app.repositories.repositories import AIUsageLogRepository, ProjectRepository, UserSettingsRepository
from app.growth.gateway.cache import PromptCache
from app.growth.gateway.quota import QuotaManager
from app.growth.gateway.router import ModelRouter, RouteDecision

log = get_logger("growth.gateway")


class AIGateway:
    """Unified AI gateway used by all Growth Engine modules."""

    def __init__(
        self,
        db: Session,
        project_id: str,
        preferred_provider: str | None = None,
        cache_ttl_hours: int = 24,
    ) -> None:
        self.db = db
        self.project_id = project_id
        self.quota = QuotaManager(db)
        self.cache = PromptCache(db, ttl_hours=cache_ttl_hours)
        self.router = ModelRouter(preferred_provider)
        self._usage_repo = AIUsageLogRepository(db)

    def generate(
        self,
        task_type: str,
        prompt: str,
        system_prompt: str | None = None,
        use_cache: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **cache_kwargs: object,
    ) -> str:
        """Generate text for the given task, with caching and fallback."""
        if use_cache:
            cached = self.cache.get(task_type, prompt, **cache_kwargs)
            if cached is not None:
                return cached

        decisions = self._build_decisions(task_type)
        last_error: Exception | None = None

        for decision in decisions:
            if not self.quota.has_quota(decision.provider, decision.model):
                log.info(f"Skipping {decision.provider}/{decision.model}: quota exhausted")
                continue
            try:
                result = self._call_provider(decision, prompt, system_prompt, max_tokens, temperature)
                self.quota.record_usage(decision.provider, decision.model, result.total_tokens)
                self._log_usage(decision, result)
                if use_cache:
                    self.cache.set(task_type, prompt, result.text, decision.provider, decision.model, **cache_kwargs)
                return result.text
            except Exception as exc:
                log.warning(f"Provider {decision.provider}/{decision.model} failed: {exc}")
                last_error = exc
                continue

        raise ProviderException(f"All providers failed for task={task_type}. Last error: {last_error}")

    def generate_batch(
        self,
        task_type: str,
        prompts: list[str],
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> list[str]:
        """Generate for multiple prompts. Combines them into one request when possible."""
        if not prompts:
            return []
        combined = "\n\n---ITEM---\n\n".join(
            f"[{i + 1}] {p}" for i, p in enumerate(prompts)
        )
        batch_system = (
            (system_prompt or "")
            + "\n\nRespond with each item prefixed by its number [N]: separated by '---ITEM---'."
        )
        raw = self.generate(task_type, combined, system_prompt=batch_system, use_cache=False, max_tokens=max_tokens * len(prompts), temperature=temperature)
        parts = raw.split("---ITEM---")
        results: list[str] = []
        for i, part in enumerate(parts[: len(prompts)]):
            cleaned = part.strip()
            if cleaned.startswith(f"[{i + 1}]"):
                cleaned = cleaned[len(f"[{i + 1}]"):].strip()
            results.append(cleaned)
        while len(results) < len(prompts):
            results.append("")
        return results

    def _build_decisions(self, task_type: str) -> list[RouteDecision]:
        decisions = self.router.route_with_fallback(task_type)
        project_decisions = self._project_provider_decisions(task_type)
        return project_decisions + decisions

    def _project_provider_decisions(self, task_type: str) -> list[RouteDecision]:
        from app.growth.gateway.router import RouteDecision, TASK_TIERS
        providers = (
            self.db.query(AIProvider)
            .filter_by(project_id=self.project_id, enabled=True)
            .order_by(AIProvider.priority)
            .all()
        )
        tier = TASK_TIERS.get(task_type, "medium")
        decisions = []
        for p in providers:
            decisions.append(RouteDecision(provider=p.provider, model=p.model, tier=tier, task_type=task_type))
        return decisions

    def _call_provider(
        self,
        decision: RouteDecision,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
    ) -> GenerationResult:
        import asyncio
        api_key = self._get_api_key(decision.provider)
        config = ProviderConfig(
            provider=decision.provider,
            model=decision.model,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )
        provider = AIProviderFactory.create(config)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(provider.generate(prompt))

    def _get_api_key(self, provider: str) -> str | None:
        from app.core.config import settings
        project = ProjectRepository(self.db).get(self.project_id)
        if project:
            prefs = UserSettingsRepository(self.db).get_by(user_id=project.user_id)
            if prefs and prefs.default_provider == provider:
                key = decrypt_secret(prefs.default_api_key_encrypted or "") or None
                if key:
                    return key
        return settings.provider_api_key(provider) or None

    def _log_usage(self, decision: RouteDecision, result: GenerationResult) -> None:
        try:
            cost = AIProviderFactory.estimate_cost(decision.provider, result.total_tokens)
            from app.models.post import AIUsageLog
            log_entry = AIUsageLog(
                project_id=self.project_id,
                provider=decision.provider,
                model=decision.model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
                cost=cost,
            )
            self.db.add(log_entry)
            self.db.flush()
        except Exception as exc:
            log.debug(f"Usage log skipped: {exc}")
