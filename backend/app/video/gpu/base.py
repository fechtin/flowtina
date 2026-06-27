"""GPU Provider interface — every GPU cloud provider must implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GPUInstanceSpec:
    gpu_type: str
    min_vram_gb: int = 16
    max_price_per_hour: float = 1.0
    disk_gb: int = 50


@dataclass
class GPUInstanceInfo:
    external_id: str
    provider: str
    status: str
    gpu_type: str
    price_per_hour: float
    api_endpoint: str | None = None
    ssh_host: str | None = None
    ssh_port: int = 22


class BaseGPUProvider(ABC):
    """Abstract GPU cloud provider."""

    name: str = "base"

    @abstractmethod
    async def search(self, spec: GPUInstanceSpec) -> list[dict]:
        """Find available GPU instances matching the spec."""

    @abstractmethod
    async def create(self, offer_id: str, spec: GPUInstanceSpec) -> GPUInstanceInfo:
        """Rent an instance from an offer."""

    @abstractmethod
    async def destroy(self, external_id: str) -> bool:
        """Terminate and release the instance."""

    @abstractmethod
    async def status(self, external_id: str) -> str:
        """Return current status: starting | ready | running | stopped | error."""

    @abstractmethod
    async def execute(self, external_id: str, command: str, env: dict[str, str] | None = None) -> dict:
        """Run a command on the instance. Returns {stdout, stderr, exit_code}."""

    @abstractmethod
    async def upload_files(self, external_id: str, local_paths: list[str], remote_dir: str) -> None:
        """Upload local files to the instance."""

    @abstractmethod
    async def download_files(self, external_id: str, remote_paths: list[str], local_dir: str) -> list[str]:
        """Download files from the instance to local_dir. Returns local paths."""
