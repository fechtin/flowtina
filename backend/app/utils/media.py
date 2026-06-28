"""Temporary storage for uploaded post images.

Uploaded binaries live under ``settings.upload_dir`` only between upload and a
successful Facebook publish, after which they are removed. Paths are stored on
the post relative to the upload dir; absolute paths are never persisted.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationException

_CHUNK = 1024 * 1024  # 1 MiB streaming chunks keep peak memory low.
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _upload_root() -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def upload_abs_path(rel_path: str) -> Path:
    """Resolve a stored relative path to its absolute location."""
    return _upload_root() / rel_path


async def save_upload(file: UploadFile, post_id: str) -> str:
    """Stream an uploaded image to disk and return its relative path.

    Validates the declared content type and enforces ``upload_max_bytes`` while
    streaming so an oversized upload never fully buffers in memory.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_TYPES:
        raise ValidationException(
            f"Unsupported image type '{content_type or 'unknown'}'. "
            "Allowed: JPEG, PNG, GIF, WEBP."
        )
    ext = _EXT.get(content_type, mimetypes.guess_extension(content_type) or ".bin")
    dest_dir = _upload_root() / post_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    rel_path = f"{post_id}/{uuid.uuid4().hex}{ext}"
    dest = _upload_root() / rel_path

    written = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(_CHUNK):
                written += len(chunk)
                if written > settings.upload_max_bytes:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise ValidationException(
                        f"Image exceeds the {settings.upload_max_bytes // (1024 * 1024)} MiB limit."
                    )
                out.write(chunk)
    finally:
        await file.close()

    if written == 0:
        dest.unlink(missing_ok=True)
        raise ValidationException("Uploaded file is empty.")
    return rel_path


def save_bytes(data: bytes, owner_id: str, ext: str = ".jpg") -> str:
    """Persist raw image bytes under ``owner_id`` and return the relative path.

    Used for generated (not uploaded) images such as Growth Engine draft
    artwork. Enforces ``upload_max_bytes`` so a runaway API response can't fill
    the disk.
    """
    if not data:
        raise ValidationException("Generated image is empty.")
    if len(data) > settings.upload_max_bytes:
        raise ValidationException(
            f"Image exceeds the {settings.upload_max_bytes // (1024 * 1024)} MiB limit."
        )
    dest_dir = _upload_root() / owner_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    rel_path = f"{owner_id}/{uuid.uuid4().hex}{ext}"
    (_upload_root() / rel_path).write_bytes(data)
    return rel_path


def remove_upload(rel_path: str) -> None:
    """Delete a stored upload and prune its now-empty post directory."""
    if not rel_path:
        return
    path = _upload_root() / rel_path
    path.unlink(missing_ok=True)
    parent = path.parent
    try:
        if parent != _upload_root() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:  # directory vanished or not empty — nothing to prune
        pass
