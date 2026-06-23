"""Facebook publishing via the Meta Graph API (no browser automation)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import FacebookException, NotFoundException
from app.core.logger import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.models.integration import FacebookPage
from app.models.post import Post
from app.repositories.repositories import (
    FacebookPageRepository,
    FacebookPostRepository,
    PostRepository,
)
from app.schemas.content import FacebookPageCreate
from app.utils.retry import retry_async

log = get_logger("facebook")

GRAPH_API = "https://graph.facebook.com/v21.0"


class FacebookService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pages = FacebookPageRepository(db)
        self.fb_posts = FacebookPostRepository(db)
        self.posts = PostRepository(db)

    def list_pages(self, project_id: str) -> list[FacebookPage]:
        return self.pages.list(project_id=project_id)

    def connect_page(self, project_id: str, payload: FacebookPageCreate) -> FacebookPage:
        page = self.pages.create(
            project_id=project_id,
            page_name=payload.page_name,
            page_id=payload.page_id,
            access_token_encrypted=encrypt_secret(payload.access_token),
        )
        self.db.commit()
        self.db.refresh(page)
        return page

    def delete_page(self, page_id: str) -> None:
        page = self.pages.get(page_id)
        if not page:
            raise NotFoundException("Page not found")
        self.pages.soft_delete(page)
        self.db.commit()

    async def publish(self, post_id: str, page_id: str) -> dict:
        """Publish a post to a connected page with retry + history tracking."""
        post = self.posts.get(post_id)
        if not post:
            raise NotFoundException("Post not found")
        page = self.pages.get(page_id)
        if not page:
            raise NotFoundException("Facebook page not found")

        message = self._compose_message(post)
        token = decrypt_secret(page.access_token_encrypted)
        url = f"{GRAPH_API}/{page.page_id}/feed"

        history = self.fb_posts.create(
            post_id=post.id, page_id=page.id, status="publishing"
        )
        start = time.perf_counter()
        try:
            data = await retry_async(
                lambda: self._call_graph(url, {"message": message, "access_token": token}),
                attempts=3,
                on_error=lambda attempt, exc: log.warning(f"FB publish attempt {attempt + 1}: {exc}"),
            )
            duration = int((time.perf_counter() - start) * 1000)
            history.status = "published"
            history.facebook_post_id = data.get("id")
            history.duration_ms = duration
            history.response_json = json.dumps(data)[:2000]
            history.published_at = datetime.now(timezone.utc)
            post.status = "published"
            post.published_at = datetime.now(timezone.utc)
            self.db.commit()
            log.info(f"Published post {post.id} to page {page.page_id} as {data.get('id')}")
            return {"facebook_post_id": data.get("id"), "duration_ms": duration}
        except Exception as exc:  # noqa: BLE001 - record failure, notify upstream
            history.status = "failed"
            history.error_message = str(exc)[:1000]
            post.status = "failed"
            post.error_message = str(exc)[:1000]
            self.db.commit()
            raise FacebookException(f"Publish failed: {exc}") from exc

    @staticmethod
    def _compose_message(post: Post) -> str:
        parts = [post.content.strip()]
        if post.hashtags:
            parts.append(post.hashtags.strip())
        return "\n\n".join(p for p in parts if p)

    @staticmethod
    async def _call_graph(url: str, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, data=data)
        if resp.status_code >= 400:
            raise FacebookException(f"Graph API HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()
