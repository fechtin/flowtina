"""Video Job Service: manage video generation jobs through their state machine.

States: pending → waiting_gpu → starting_gpu → uploading → processing
        → downloading → completed → published
        → failed (on error, with retry)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.video.gpu.base import GPUInstanceSpec
from app.video.gpu.manager import GPUResourceManager
from app.video.models import GPUInstance, VideoJob, VideoPageConfig
from app.video.worker.pipeline import VideoPipeline

log = get_logger("video.service")

_MAX_RETRIES = 3
_GPU_SPEC = GPUInstanceSpec(gpu_type="RTX3090", min_vram_gb=16, max_price_per_hour=0.5, disk_gb=50)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VideoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Page Config
    # ------------------------------------------------------------------

    def get_page_config(self, page_id: str) -> VideoPageConfig | None:
        return self.db.query(VideoPageConfig).filter_by(page_id=page_id).first()

    def upsert_page_config(self, page_id: str, data: dict) -> VideoPageConfig:
        cfg = self.get_page_config(page_id)
        if cfg:
            for k, v in data.items():
                setattr(cfg, k, v)
        else:
            cfg = VideoPageConfig(page_id=page_id, **data)
            self.db.add(cfg)
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    # ------------------------------------------------------------------
    # Job CRUD
    # ------------------------------------------------------------------

    def create_job(self, data: dict) -> VideoJob:
        page_id = data["page_id"]
        cfg = self.get_page_config(page_id)
        job_data = {
            "avatar_provider": cfg.avatar_provider if cfg else "liveportrait",
            "tts_provider": cfg.tts_provider if cfg else "edge_tts",
            "gpu_provider": cfg.gpu_provider if cfg else "vast",
            "character_image_url": cfg.character_image_url if cfg else None,
            "voice_id": cfg.voice_id if cfg else None,
            "language": cfg.language if cfg else "vi",
            "music_url": cfg.music_url if cfg else None,
            "intro_url": cfg.intro_url if cfg else None,
            "outro_url": cfg.outro_url if cfg else None,
            "subtitle_enabled": cfg.subtitle_enabled if cfg else True,
            "publish_after_generate": cfg.publish_after_generate if cfg else False,
        }
        job_data.update({k: v for k, v in data.items() if v is not None})
        job = VideoJob(**job_data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        log.info(f"Video job {job.id} created for page {page_id}")
        return job

    def get_job(self, job_id: str) -> VideoJob | None:
        return self.db.query(VideoJob).filter_by(id=job_id).first()

    def list_jobs(self, page_id: str, limit: int = 50) -> list[VideoJob]:
        return (
            self.db.query(VideoJob)
            .filter_by(page_id=page_id)
            .order_by(VideoJob.created_at.desc())
            .limit(limit)
            .all()
        )

    def cancel_job(self, job_id: str) -> VideoJob | None:
        job = self.get_job(job_id)
        if job and job.status in {"pending", "waiting_gpu"}:
            job.status = "cancelled"
            self.db.commit()
        return job

    # ------------------------------------------------------------------
    # Job Processing (called by queue/scheduler)
    # ------------------------------------------------------------------

    async def process_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if not job or job.status not in {"pending", "waiting_gpu"}:
            return

        vast_key = getattr(settings, "vast_api_key", "")
        runpod_key = getattr(settings, "runpod_api_key", "")
        manager = GPUResourceManager(self.db, vast_key=vast_key, runpod_key=runpod_key)

        try:
            self._set_status(job, "waiting_gpu")
            instance = await manager.acquire(_GPU_SPEC)
            self._set_status(job, "starting_gpu")
            job.gpu_instance_id = instance.id
            job.gpu_provider = instance.provider
            self.db.commit()

            provider = manager.get_provider(instance.provider)
            if not provider:
                raise RuntimeError("No GPU provider available")

            self._set_status(job, "processing")
            pipeline = VideoPipeline(provider, instance.external_id or "")
            result = await pipeline.run(
                job_id=job.id,
                script=job.script,
                character_image_url=job.character_image_url or "",
                voice_id=job.voice_id or "en-US-JennyNeural",
                language=job.language,
                tts_provider=job.tts_provider,
                avatar_provider=job.avatar_provider,
                music_url=job.music_url,
                intro_url=job.intro_url,
                outro_url=job.outro_url,
                subtitle_enabled=job.subtitle_enabled,
            )

            self._set_status(job, "downloading")
            local_dir = str(Path(settings.upload_dir) / "videos" / job.id)
            remote_files = [f for f in [result["output_path"], result.get("thumbnail_path"), result.get("audio_path"), result.get("subtitle_path")] if f]
            local_files = await provider.download_files(instance.external_id or "", remote_files, local_dir)

            job.output_url = self._to_url(local_files, ".mp4")
            job.thumbnail_url = self._to_url(local_files, ".jpg")
            job.audio_url = self._to_url(local_files, ".wav")
            job.subtitle_url = self._to_url(local_files, ".srt")
            job.duration_seconds = result.get("duration_seconds", 0)
            self._set_status(job, "completed")
            self.db.commit()

            await manager.release(instance.id)

            if job.publish_after_generate and job.output_url:
                await self._request_publish(job)

        except Exception as exc:
            log.error(f"Video job {job_id} failed: {exc}")
            job.error_message = str(exc)[:500]
            job.retry_count += 1
            if job.retry_count < _MAX_RETRIES:
                self._set_status(job, "waiting_gpu")
            else:
                self._set_status(job, "failed")
            self.db.commit()

    def _set_status(self, job: VideoJob, status: str) -> None:
        job.status = status
        log.info(f"Job {job.id} → {status}")

    @staticmethod
    def _to_url(files: list[str], ext: str) -> str | None:
        for f in files:
            if f.endswith(ext):
                return f"/uploads/videos/{Path(f).parent.name}/{Path(f).name}"
        return None

    async def _request_publish(self, job: VideoJob) -> None:
        log.info(f"Job {job.id} auto-publish requested (page={job.page_id}, url={job.output_url})")
        job.published = True
        self.db.flush()

    # ------------------------------------------------------------------
    # GPU Instances
    # ------------------------------------------------------------------

    def list_gpu_instances(self) -> list[GPUInstance]:
        return self.db.query(GPUInstance).filter(GPUInstance.status.in_(["running", "idle", "starting"])).all()

    async def cleanup_idle_gpus(self) -> int:
        vast_key = getattr(settings, "vast_api_key", "")
        runpod_key = getattr(settings, "runpod_api_key", "")
        manager = GPUResourceManager(self.db, vast_key=vast_key, runpod_key=runpod_key)
        count = await manager.cleanup_idle()
        self.db.commit()
        return count
