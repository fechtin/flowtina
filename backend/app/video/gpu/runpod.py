"""RunPod GPU provider implementation.

Uses RunPod GraphQL API for pod management.
"""

from __future__ import annotations

import asyncio

import httpx

from app.core.exceptions import ProviderException
from app.core.logger import get_logger
from app.video.gpu.base import BaseGPUProvider, GPUInstanceInfo, GPUInstanceSpec

log = get_logger("video.runpod")

_RUNPOD_GQL = "https://api.runpod.io/graphql"
_WAIT_READY_TIMEOUT = 300
_POLL_INTERVAL = 15


class RunPodProvider(BaseGPUProvider):
    name = "runpod"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    async def _gql(self, query: str, variables: dict | None = None) -> dict:
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_RUNPOD_GQL, headers=self._headers, json=payload)
        if resp.status_code >= 400:
            raise ProviderException(f"RunPod API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        if "errors" in data:
            raise ProviderException(f"RunPod GQL error: {data['errors']}")
        return data.get("data", {})

    async def search(self, spec: GPUInstanceSpec) -> list[dict]:
        query = """
        query GpuTypes {
          gpuTypes {
            id
            displayName
            memoryInGb
            securePrice
          }
        }
        """
        data = await self._gql(query)
        gpus = data.get("gpuTypes", [])
        return [g for g in gpus if g.get("memoryInGb", 0) >= spec.min_vram_gb and (g.get("securePrice") or 99) <= spec.max_price_per_hour]

    async def create(self, offer_id: str, spec: GPUInstanceSpec) -> GPUInstanceInfo:
        mutation = """
        mutation PodFindAndDeployOnDemand($input: PodFindAndDeployOnDemandInput!) {
          podFindAndDeployOnDemand(input: $input) {
            id
            desiredStatus
            runtime { gpus { id gpuUtilPercent } }
          }
        }
        """
        variables = {
            "input": {
                "gpuTypeId": offer_id,
                "name": "flowtina-worker",
                "imageName": "pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime",
                "gpuCount": 1,
                "volumeInGb": spec.disk_gb,
                "containerDiskInGb": 20,
                "startJupyter": False,
                "startSsh": True,
            }
        }
        data = await self._gql(mutation, variables)
        pod = data.get("podFindAndDeployOnDemand", {})
        pod_id = pod["id"]
        return await self._wait_ready(pod_id)

    async def _wait_ready(self, pod_id: str) -> GPUInstanceInfo:
        deadline = asyncio.get_event_loop().time() + _WAIT_READY_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            info = await self._fetch_pod(pod_id)
            if info and info.status == "ready":
                return info
            await asyncio.sleep(_POLL_INTERVAL)
        raise ProviderException(f"RunPod pod {pod_id} not ready in time")

    async def _fetch_pod(self, pod_id: str) -> GPUInstanceInfo | None:
        query = """
        query Pod($podId: String!) {
          pod(input: { podId: $podId }) {
            id
            desiredStatus
            runtime {
              ports { ip isIpPublic privatePort publicPort type }
            }
          }
        }
        """
        try:
            data = await self._gql(query, {"podId": pod_id})
            pod = data.get("pod", {})
            desired = pod.get("desiredStatus", "")
            status = "ready" if desired == "RUNNING" else "starting"
            ssh_host = None
            ssh_port = 22
            for port in (pod.get("runtime") or {}).get("ports", []):
                if port.get("privatePort") == 22 and port.get("isIpPublic"):
                    ssh_host = port["ip"]
                    ssh_port = port["publicPort"]
            return GPUInstanceInfo(
                external_id=pod_id,
                provider="runpod",
                status=status,
                gpu_type="unknown",
                price_per_hour=0.0,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
            )
        except Exception as exc:
            log.warning(f"Fetch RunPod pod failed: {exc}")
            return None

    async def destroy(self, external_id: str) -> bool:
        mutation = """
        mutation PodTerminate($input: PodTerminateInput!) {
          podTerminate(input: $input)
        }
        """
        try:
            await self._gql(mutation, {"input": {"podId": external_id}})
            return True
        except Exception as exc:
            log.error(f"RunPod destroy failed: {exc}")
            return False

    async def status(self, external_id: str) -> str:
        info = await self._fetch_pod(external_id)
        return info.status if info else "error"

    async def execute(self, external_id: str, command: str, env: dict[str, str] | None = None) -> dict:
        info = await self._fetch_pod(external_id)
        if not info or not info.ssh_host:
            raise ProviderException(f"No SSH info for RunPod pod {external_id}")
        env_prefix = " ".join(f"{k}={v}" for k, v in (env or {}).items())
        full_cmd = f"{env_prefix} {command}".strip()
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-p", str(info.ssh_port),
            f"root@{info.ssh_host}", full_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        return {"stdout": stdout.decode(), "stderr": stderr.decode(), "exit_code": proc.returncode}

    async def upload_files(self, external_id: str, local_paths: list[str], remote_dir: str) -> None:
        info = await self._fetch_pod(external_id)
        if not info or not info.ssh_host:
            raise ProviderException(f"No SSH for RunPod {external_id}")
        for path in local_paths:
            proc = await asyncio.create_subprocess_exec(
                "scp", "-o", "StrictHostKeyChecking=no", "-P", str(info.ssh_port),
                path, f"root@{info.ssh_host}:{remote_dir}/",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)

    async def download_files(self, external_id: str, remote_paths: list[str], local_dir: str) -> list[str]:
        from pathlib import Path
        info = await self._fetch_pod(external_id)
        if not info or not info.ssh_host:
            raise ProviderException(f"No SSH for RunPod {external_id}")
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        local_files: list[str] = []
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
