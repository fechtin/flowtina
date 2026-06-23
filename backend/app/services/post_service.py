"""Post CRUD, versioning and publish-state transitions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.post import Post
from app.repositories.repositories import PostRepository, PostVersionRepository
from app.schemas.content import PostCreate, PostUpdate
from app.utils.media import remove_upload


class PostService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.posts = PostRepository(db)
        self.versions = PostVersionRepository(db)

    def list(
        self,
        project_id: str,
        *,
        status: str | None = None,
        language: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Post]:
        return self.posts.list_filtered(
            project_id,
            status=status,
            language=language,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )

    def get(self, post_id: str) -> Post:
        post = self.posts.get(post_id)
        if not post:
            raise NotFoundException("Post not found")
        return post

    def create(self, project_id: str, payload: PostCreate) -> Post:
        post = self.posts.create(
            project_id=project_id, created_by_ai=False, **payload.model_dump()
        )
        self.db.commit()
        self.db.refresh(post)
        return post

    def update(self, post_id: str, payload: PostUpdate) -> Post:
        post = self.get(post_id)
        data = payload.model_dump(exclude_none=True)
        if "content" in data and data["content"] != post.content:
            self.versions.create(
                post_id=post.id, version=post.version, content=post.content
            )
            post.version += 1
        self.posts.update(post, **data)
        self.db.commit()
        self.db.refresh(post)
        return post

    def delete(self, post_id: str) -> None:
        post = self.get(post_id)
        if post.image_path:
            remove_upload(post.image_path)
        self.posts.soft_delete(post)
        self.db.commit()

    def set_image_path(self, post_id: str, rel_path: str) -> Post:
        """Attach an uploaded binary image, replacing any prior attachment.

        An uploaded image and a URL image are mutually exclusive (one image per
        post), so the ``image_url`` is cleared and any previous upload removed.
        """
        post = self.get(post_id)
        if post.image_path and post.image_path != rel_path:
            remove_upload(post.image_path)
        post.image_path = rel_path
        post.image_url = None
        self.db.commit()
        self.db.refresh(post)
        return post

    def clear_image(self, post_id: str) -> Post:
        """Remove any attached image (uploaded file and/or URL) from a post."""
        post = self.get(post_id)
        if post.image_path:
            remove_upload(post.image_path)
        post.image_path = None
        post.image_url = None
        self.db.commit()
        self.db.refresh(post)
        return post

    def mark_published(self, post: Post) -> None:
        post.status = "published"
        post.published_at = datetime.now(timezone.utc)
        post.error_message = None
        self.db.commit()

    def mark_failed(self, post: Post, error: str) -> None:
        post.status = "failed"
        post.error_message = error[:1000]
        self.db.commit()

    def schedule(self, post: Post, publish_at: datetime) -> Post:
        post.status = "scheduled"
        post.publish_at = publish_at
        self.db.commit()
        self.db.refresh(post)
        return post
