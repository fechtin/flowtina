"""Vast.ai GPU provider implementation.

API docs: https://vast.ai/docs/api
Uses REST API for instance management and SSH for file transfer / execution.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.exceptions import ProviderException
from app.core.logger import get_logger
from app.video.gpu.base import BaseGPUProvider, GPUInstanceInfo, GPUInstanceSpec

log = get_logger("video.vast")

_VAST_API = "https://console.vast.ai/api/v0"
_WAIT_READY_TIMEOUT = 300
_POLL_INTERVAL = 10


class VastProvider(BaseGPUProvider):
    name = "vast"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def _get(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{_VAST_API}{path}", headers=self._headers)
        if resp.status_code >= 400:
            raise ProviderException(f"Vast API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{_VAST_API}{path}", headers=self._headers, json=payload)
        if resp.status_code >= 400:
            raise ProviderException(f"Vast API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def _delete(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(f"{_VAST_API}{path}", headers=self._headers)
        return resp.json() if resp.content else {}

    async def search(self, spec: GPUInstanceSpec) -> list[dict]:
        data = await self._get(
            f"/bundles/?q={{\"gpu_ram\":\">={spec.min_vram_gb}\","
            f"\"dph_total\":\"<={spec.max_price_per_hour}\","
            f"\"disk_space\":\">={spec.disk_gb}\","
            f"\"rentable\":\"=true\",\"rented\":\"=false\","
            f"\"num_gpus\":\">=1\"}}&order=dph_total,asc&limit=20"
        )
        return data.get("offers", [])

    async def create(self, offer_id: str, spec: GPUInstanceSpec) -> GPUInstanceInfo:
        payload = {
            "id": int(offer_id),
            "image": "pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime",
            "disk": spec.disk_gb,
            "label": "flowtina-video-worker",
            "onstart": "pip install edge-tts ffmpeg-python Pillow requests 2>/dev/null",
        }
        data = await self._post("/asks/", payload)
        instance_id = str(data.get("new_contract", offer_id))
        log.info(f"Vast instance created: {instance_id}")
        return await self._wait_ready(instance_id)

    async def _wait_ready(self, external_id: str) -> GPUInstanceInfo:
        deadline = asyncio.get_event_loop().time() + _WAIT_READY_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            info = await self._fetch_instance(external_id)
            if info and info.status == "ready":
                return info
            await asyncio.sleep(_POLL_INTERVAL)
        raise ProviderException(f"Vast instance {external_id} did not become ready in time")

    async def _fetch_instance(self, external_id: str) -> GPUInstanceInfo | None:
        try:
            data = await self._get(f"/instances/{external_id}/")
            inst = data.get("instance") or data
            cur_state = inst.get("cur_state", "unknown")
            actual_status = inst.get("actual_status", "")
            status = "ready" if actual_status == "running" or cur_state == "running" else "starting"
            return GPUInstanceInfo(
                external_id=external_id,
                provider="vast",
                status=status,
                gpu_type=inst.get("gpu_name", "unknown"),
                price_per_hour=float(inst.get("dph_total", 0)),
                ssh_host=inst.get("ssh_host"),
                ssh_port=int(inst.get("ssh_port", 22)),
            )
        except Exception as exc:
            log.warning(f"Fetch instance failed: {exc}")
            return None

    async def destroy(self, external_id: str) -> bool:
        try:
            await self._delete(f"/instances/{external_id}/")
            log.info(f"Vast instance {external_id} destroyed")
            return True
        except Exception as exc:
            log.error(f"Destroy failed for {external_id}: {exc}")
            return False

    async def status(self, external_id: str) -> str:
        info = await self._fetch_instance(external_id)
        return info.status if info else "error"

    async def execute(self, external_id: str, command: str, env: dict[str, str] | None = None) -> dict:
        info = await self._fetch_instance(external_id)
        if not info or not info.ssh_host:
            raise ProviderException(f"Instance {external_id} has no SSH host")
        env_prefix = " ".join(f"{k}={v}" for k, v in (env or {}).items())
        full_cmd = f"{env_prefix} {command}".strip()
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-p", str(info.ssh_port),
            f"root@{info.ssh_host}", full_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "exit_code": proc.returncode,
        }

    async def upload_files(self, external_id: str, local_paths: list[str], remote_dir: str) -> None:
        info = await self._fetch_instance(external_id)
        if not info or not info.ssh_host:
            raise ProviderException(f"No SSH info for instance {external_id}")
        for path in local_paths:
            proc = await asyncio.create_subprocess_exec(
                "scp", "-o", "StrictHostKeyChecking=no", "-P", str(info.ssh_port),
                path, f"root@{info.ssh_host}:{remote_dir}/",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)

    async def download_files(self, external_id: str, remote_paths: list[str], local_dir: str) -> list[str]:
        info = await self._fetch_instance(external_id)
        if not info or not info.ssh_host:
            raise ProviderException(f"No SSH info for instance {external_id}")
        local_files: list[str] = []
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        for rpath in remote_paths:
            fname = Path(rpath).name
            local_path = str(Path(local_dir) / fname)
            proc = await asyncio.create_subprocess_exec(
                "scp", "-o", "StrictHostKeyChecking=no", "-P", str(info.ssh_port),
                f"root@{info.ssh_host}:{rpath}", local_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=300)
            local_files.append(local_path)
        return local_files
