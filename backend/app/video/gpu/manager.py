"""GPU Resource Manager: provision, monitor, and auto-destroy GPU instances.

Responsibilities:
- Select cheapest available GPU matching requirements
- Auto-scale: create when queue grows, destroy after idle timeout
- Provider fallback: vast → runpod
- Track instances in DB
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.video.gpu.base import BaseGPUProvider, GPUInstanceSpec
from app.video.gpu.vast import VastProvider
from app.video.gpu.runpod import RunPodProvider
from app.video.models import GPUInstance

log = get_logger("video.gpu.manager")

_IDLE_TIMEOUT_SECONDS = 300
_MAX_INSTANCES = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GPUResourceManager:
    def __init__(self, db: Session, vast_key: str = "", runpod_key: str = "") -> None:
        self.db = db
        self._providers: list[BaseGPUProvider] = []
        if vast_key:
            self._providers.append(VastProvider(vast_key))
        if runpod_key:
            self._providers.append(RunPodProvider(runpod_key))

    def _get_providers(self) -> list[BaseGPUProvider]:
        if not self._providers:
            raise RuntimeError("No GPU providers configured. Set VAST_API_KEY or RUNPOD_API_KEY.")
        return self._providers

    async def acquire(self, spec: GPUInstanceSpec) -> GPUInstance:
        """Return a ready GPU instance — reuse idle or create new."""
        idle = self._find_idle_instance()
        if idle:
            idle.status = "running"
            idle.idle_since = None
            self.db.flush()
            log.info(f"Reusing idle GPU instance {idle.id}")
            return idle

        running = self.db.query(GPUInstance).filter_by(status="running").count()
        if running >= _MAX_INSTANCES:
            raise RuntimeError(f"Max GPU instances ({_MAX_INSTANCES}) already running")

        return await self._create_instance(spec)

    def _find_idle_instance(self) -> GPUInstance | None:
        return self.db.query(GPUInstance).filter_by(status="idle").first()

    async def _create_instance(self, spec: GPUInstanceSpec) -> GPUInstance:
        last_error: Exception | None = None
        for provider in self._get_providers():
            try:
                log.info(f"Searching {provider.name} for GPU...")
                offers = await provider.search(spec)
                if not offers:
                    log.warning(f"No offers from {provider.name}")
                    continue
                best_offer = offers[0]
                offer_id = str(best_offer.get("id", best_offer.get("gpuTypeId", "")))
                info = await provider.create(offer_id, spec)

                instance = GPUInstance(
                    provider=provider.name,
                    external_id=info.external_id,
                    status="running",
                    gpu_type=info.gpu_type,
                    price_per_hour=info.price_per_hour,
                    ssh_host=info.ssh_host,
                    ssh_port=info.ssh_port,
                )
                self.db.add(instance)
                self.db.flush()
                log.info(f"GPU instance {instance.id} created via {provider.name}")
                return instance
            except Exception as exc:
                log.warning(f"{provider.name} failed: {exc}")
                last_error = exc
                continue
        raise RuntimeError(f"All GPU providers failed. Last error: {last_error}")

    async def release(self, instance_id: str) -> None:
        """Mark instance as idle; destroy if idle too long."""
        instance = self.db.query(GPUInstance).filter_by(id=instance_id).first()
        if not instance:
            return
        instance.status = "idle"
        instance.idle_since = _now_iso()
        self.db.flush()

    async def cleanup_idle(self) -> int:
        """Destroy instances that have been idle past the timeout. Returns count destroyed."""
        now = datetime.now(timezone.utc)
        idle_instances = self.db.query(GPUInstance).filter_by(status="idle").all()
        destroyed = 0
        for inst in idle_instances:
            if not inst.idle_since:
                continue
            idle_dt = datetime.fromisoformat(inst.idle_since)
            if (now - idle_dt).total_seconds() >= _IDLE_TIMEOUT_SECONDS:
                for provider in self._get_providers():
                    if provider.name == inst.provider and inst.external_id:
                        await provider.destroy(inst.external_id)
                        break
                inst.status = "stopped"
                inst.idle_since = None
                self.db.flush()
                destroyed += 1
                log.info(f"Destroyed idle GPU instance {inst.id}")
        return destroyed

    def get_provider(self, name: str) -> BaseGPUProvider | None:
        for p in self._providers:
            if p.name == name:
                return p
        return self._providers[0] if self._providers else None
