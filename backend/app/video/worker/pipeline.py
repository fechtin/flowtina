"""Video Worker Pipeline: orchestrate TTS → Talking Avatar → Subtitle → FFmpeg merge.

This pipeline runs ON the GPU instance via SSH execute commands.
The orchestrator (VideoService) calls these steps over SSH after acquiring a GPU.
"""

from __future__ import annotations

import asyncio
import re
import textwrap
from pathlib import Path

from app.core.logger import get_logger
from app.video.gpu.base import BaseGPUProvider

log = get_logger("video.pipeline")

_WORKER_WORKDIR = "/tmp/flowtina_job"


class VideoPipeline:
    """Runs video generation steps on a remote GPU instance."""

    def __init__(self, provider: BaseGPUProvider, external_id: str) -> None:
        self.provider = provider
        self.instance_id = external_id

    async def run(
        self,
        job_id: str,
        script: str,
        character_image_url: str,
        voice_id: str = "en-US-JennyNeural",
        language: str = "en",
        tts_provider: str = "edge_tts",
        avatar_provider: str = "liveportrait",
        music_url: str | None = None,
        intro_url: str | None = None,
        outro_url: str | None = None,
        subtitle_enabled: bool = True,
    ) -> dict:
        """Run the full pipeline and return output file paths."""
        workdir = f"{_WORKER_WORKDIR}/{job_id}"
        await self._setup_workdir(workdir)
        audio_path = await self._generate_tts(workdir, script, voice_id, language, tts_provider)
        subtitle_path = await self._generate_subtitle(workdir, script, audio_path) if subtitle_enabled else None
        avatar_path = await self._generate_avatar(workdir, character_image_url, audio_path, avatar_provider)
        output_path = await self._merge(workdir, avatar_path, subtitle_path, music_url, intro_url, outro_url)
        thumbnail_path = await self._extract_thumbnail(workdir, output_path)
        duration = await self._get_duration(output_path)
        return {
            "output_path": output_path,
            "audio_path": audio_path,
            "subtitle_path": subtitle_path,
            "thumbnail_path": thumbnail_path,
            "workdir": workdir,
            "duration_seconds": duration,
        }

    async def _exec(self, command: str) -> dict:
        result = await self.provider.execute(self.instance_id, command)
        if result["exit_code"] != 0:
            log.warning(f"Command failed (exit {result['exit_code']}): {command[:80]}\n{result['stderr'][:200]}")
        return result

    async def _setup_workdir(self, workdir: str) -> None:
        await self._exec(f"mkdir -p {workdir} && pip install -q edge-tts 2>/dev/null || true")

    async def _generate_tts(self, workdir: str, script: str, voice_id: str, language: str, provider: str) -> str:
        audio_path = f"{workdir}/audio.wav"
        if provider == "edge_tts":
            safe_script = script.replace('"', '\\"').replace("'", "\\'")
            cmd = (
                f"python3 -c \""
                f"import asyncio, edge_tts; "
                f"asyncio.run(edge_tts.Communicate('{safe_script[:2000]}', '{voice_id}').save('{workdir}/audio.mp3'))\""
                f" && ffmpeg -y -i {workdir}/audio.mp3 -ar 16000 {audio_path} -loglevel quiet"
            )
        else:
            cmd = f"echo 'TTS not configured' && touch {audio_path}"
        await self._exec(cmd)
        return audio_path

    async def _generate_subtitle(self, workdir: str, script: str, audio_path: str) -> str:
        srt_path = f"{workdir}/subtitle.srt"
        words = script.split()
        chars_per_second = 15
        current_time = 0.0
        srt_lines: list[str] = []
        chunk_size = 8
        for i, chunk in enumerate([words[j:j+chunk_size] for j in range(0, len(words), chunk_size)]):
            text = " ".join(chunk)
            duration = max(len(text) / chars_per_second, 1.0)
            start = _seconds_to_srt(current_time)
            end = _seconds_to_srt(current_time + duration)
            srt_lines.append(f"{i + 1}\n{start} --> {end}\n{text}\n")
            current_time += duration

        srt_content = "\n".join(srt_lines)
        escaped = srt_content.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
        await self._exec(f"printf '{escaped}' > {srt_path}")
        return srt_path

    async def _generate_avatar(self, workdir: str, image_url: str, audio_path: str, provider: str) -> str:
        avatar_path = f"{workdir}/avatar.mp4"
        image_path = f"{workdir}/character.jpg"
        await self._exec(f"wget -q '{image_url}' -O {image_path} || curl -sL '{image_url}' -o {image_path}")
        if provider == "liveportrait":
            cmd = textwrap.dedent(f"""
                if python3 -c "import liveportrait" 2>/dev/null; then
                  python3 -m liveportrait.infer --driving_info {audio_path} --source_image {image_path} --output_dir {workdir} --output_name avatar 2>/dev/null
                else
                  ffmpeg -y -loop 1 -i {image_path} -i {audio_path} -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest {avatar_path} -loglevel quiet
                fi
            """).strip()
        else:
            cmd = f"ffmpeg -y -loop 1 -i {image_path} -i {audio_path} -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest {avatar_path} -loglevel quiet"
        await self._exec(cmd)
        return avatar_path

    async def _merge(
        self,
        workdir: str,
        avatar_path: str,
        subtitle_path: str | None,
        music_url: str | None,
        intro_url: str | None,
        outro_url: str | None,
    ) -> str:
        output_path = f"{workdir}/output.mp4"
        inputs = []
        filter_parts = []

        if intro_url:
            intro_path = f"{workdir}/intro.mp4"
            await self._exec(f"wget -q '{intro_url}' -O {intro_path} || true")
            inputs.extend(["-i", intro_path])

        inputs.extend(["-i", avatar_path])

        if outro_url:
            outro_path = f"{workdir}/outro.mp4"
            await self._exec(f"wget -q '{outro_url}' -O {outro_path} || true")
            inputs.extend(["-i", outro_path])

        input_str = " ".join(f"-i {p}" for p in [avatar_path])

        if subtitle_path:
            sub_filter = f",subtitles={subtitle_path}:force_style='FontSize=24,PrimaryColour=&Hffffff'"
        else:
            sub_filter = ""

        cmd = (
            f"ffmpeg -y {input_str} "
            f"-vf 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2{sub_filter}' "
            f"-c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k "
            f"{output_path} -loglevel quiet"
        )
        await self._exec(cmd)
        return output_path

    async def _extract_thumbnail(self, workdir: str, video_path: str) -> str:
        thumb_path = f"{workdir}/thumbnail.jpg"
        await self._exec(f"ffmpeg -y -i {video_path} -ss 00:00:01.000 -vframes 1 {thumb_path} -loglevel quiet")
        return thumb_path

    async def _get_duration(self, video_path: str) -> int:
        result = await self._exec(
            f"ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}"
        )
        try:
            return int(float(result["stdout"].strip()))
        except Exception:
            return 0


def _seconds_to_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
