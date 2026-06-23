"""Post endpoints: CRUD, AI generation, publish and retry."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.common import ok
from app.schemas.content import GenerateRequest, PostCreate, PostOut, PostUpdate
from app.services.content_service import ContentService
from app.services.facebook_service import FacebookService
from app.services.post_service import PostService
from app.utils.media import save_upload

router = APIRouter(tags=["posts"])


@router.get("/projects/{project_id}/posts")
def list_posts(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    status: str | None = None,
    language: str | None = None,
    keyword: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    items = PostService(db).list(
        project.id,
        status=status,
        language=language,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return ok([PostOut.model_validate(p).model_dump() for p in items])


@router.post("/projects/{project_id}/posts")
def create_post(
    payload: PostCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    post = PostService(db).create(project.id, payload)
    return ok(PostOut.model_validate(post).model_dump(), "Post created")


@router.post("/projects/{project_id}/posts/generate")
async def generate_post(
    payload: GenerateRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    posts = await ContentService(db).generate_for_project(
        project.id,
        topic=payload.topic,
        content_type=payload.content_type,
        language=payload.language,
        auto_publish=payload.auto_publish,
        require_approval=payload.require_approval,
        target_page_id=payload.facebook_page_id,
    )
    return ok(
        [PostOut.model_validate(p).model_dump() for p in posts],
        f"Generated {len(posts)} post(s)",
    )


@router.get("/posts/{post_id}")
def get_post(
    post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    post = PostService(db).get(post_id)
    return ok(PostOut.model_validate(post).model_dump())


@router.put("/posts/{post_id}")
def update_post(
    post_id: str,
    payload: PostUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = PostService(db).update(post_id, payload)
    return ok(PostOut.model_validate(post).model_dump(), "Post updated")


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    PostService(db).delete(post_id)
    return ok(message="Post deleted")


@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: str,
    page_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await FacebookService(db).publish(post_id, page_id)
    return ok(result, "Post published")


@router.post("/posts/{post_id}/retry")
async def retry_post(
    post_id: str,
    page_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await FacebookService(db).publish(post_id, page_id)
    return ok(result, "Retry succeeded")


@router.post("/posts/{post_id}/image")
async def upload_post_image(
    post_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attach an uploaded binary image to a post (replaces any prior image)."""
    svc = PostService(db)
    post = svc.get(post_id)
    rel_path = await save_upload(file, post.id)
    post = svc.set_image_path(post.id, rel_path)
    return ok(PostOut.model_validate(post).model_dump(), "Image uploaded")


@router.delete("/posts/{post_id}/image")
def delete_post_image(
    post_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove any attached image (uploaded file or URL) from a post."""
    post = PostService(db).clear_image(post_id)
    return ok(PostOut.model_validate(post).model_dump(), "Image removed")
