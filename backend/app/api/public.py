"""Unauthenticated, narrowly-scoped public endpoints.

Instagram publishing requires a publicly reachable image URL — Meta's servers
fetch the image while creating the media container and cannot send an auth
header. This exposes a post's uploaded binary by its UUID id (unguessable) for
the brief window between upload and publish; the file is deleted once publishing
succeeds, closing the window.
"""

from __future__ import annotations

from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.growth.models import ContentDraft
from app.repositories.repositories import PostRepository
from app.utils.media import upload_abs_path

router = APIRouter(tags=["public"])


@router.get("/public/posts/{post_id}/image")
def public_post_image(post_id: str, db: Session = Depends(get_db)):
    """Serve a post's uploaded image so Meta can fetch it for Instagram."""
    post = PostRepository(db).get(post_id)
    if not post or not post.image_path:
        raise NotFoundException("Image not available")
    abs_path = upload_abs_path(post.image_path)
    if not abs_path.exists():
        raise NotFoundException("Image is no longer available")
    return FileResponse(abs_path)


@router.get("/public/growth/drafts/{draft_id}/image")
def public_draft_image(draft_id: str, db: Session = Depends(get_db)):
    """Serve a Growth draft's generated image for the dashboard and Meta."""
    draft = (
        db.query(ContentDraft)
        .filter(ContentDraft.id == draft_id, ContentDraft.deleted_at.is_(None))
        .first()
    )
    if not draft or not draft.media_url:
        raise NotFoundException("Image not available")
    abs_path = upload_abs_path(draft.media_url)
    if not abs_path.exists():
        raise NotFoundException("Image is no longer available")
    return FileResponse(abs_path)
