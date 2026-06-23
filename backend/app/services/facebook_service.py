"""Facebook publishing via the Meta Graph API (no browser automation)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import FacebookException, NotFoundException, ValidationException
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

    async def import_pages(self, project_id: str, token: str | None = None) -> list[FacebookPage]:
        """Discover and connect the operator's Pages from a single token.

        Uses the supplied token, or falls back to the configured system token.
        Calls Graph ``/me/accounts`` to fetch each Page's id, name and per-page
        access token automatically — no manual page-id/token entry needed. Pages
        already connected are updated (token refreshed) rather than duplicated.
        """
        token = (token or settings.facebook_system_token or "").strip()
        if not token:
            raise ValidationException("No Facebook token provided or configured")

        token = await self._maybe_exchange_long_lived(token)
        accounts = await self._fetch_accounts(token)
        if not accounts:
            raise FacebookException("No Pages found for this token (check its permissions)")

        existing = {p.page_id: p for p in self.pages.list(project_id=project_id)}
        result: list[FacebookPage] = []
        seen: set[str] = set()
        for acc in accounts:
            page_id = str(acc.get("id", ""))
            page_token = acc.get("access_token", "")
            if not page_id or not page_token:
                continue
            seen.add(page_id)
            name = acc.get("name") or page_id
            if page_id in existing:
                page = existing[page_id]
                page.page_name = name
                page.access_token_encrypted = encrypt_secret(page_token)
                page.status = "healthy"
            else:
                page = self.pages.create(
                    project_id=project_id,
                    page_name=name,
                    page_id=page_id,
                    access_token_encrypted=encrypt_secret(page_token),
                )
            result.append(page)

        # Prune pages no longer returned by the token (unassigned/removed on Facebook).
        removed = 0
        for page_id, page in existing.items():
            if page_id not in seen:
                self.pages.soft_delete(page)
                removed += 1

        self.db.commit()
        log.info(
            f"Imported {len(result)} Facebook page(s) for project {project_id}"
            + (f", pruned {removed} stale page(s)" if removed else "")
        )
        return result

    async def _maybe_exchange_long_lived(self, token: str) -> str:
        """Exchange a short-lived user token for a long-lived one when possible."""
        if not (settings.facebook_app_id and settings.facebook_app_secret):
            return token
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.facebook_app_id,
            "client_secret": settings.facebook_app_secret,
            "fb_exchange_token": token,
        }
        try:
            data = await self._get(f"{GRAPH_API}/oauth/access_token", params)
            return data.get("access_token", token)
        except FacebookException as exc:
            log.warning(f"Long-lived token exchange skipped: {exc}")
            return token

    async def _fetch_accounts(self, token: str) -> list[dict]:
        """Page through /me/accounts collecting all pages."""
        url: str | None = f"{GRAPH_API}/me/accounts"
        params: dict | None = {"fields": "id,name,access_token", "limit": 100, "access_token": token}
        accounts: list[dict] = []
        for _ in range(10):  # safety bound on pagination
            if not url:
                break
            data = await self._get(url, params)
            accounts.extend(data.get("data", []))
            url = (data.get("paging") or {}).get("next")
            params = None  # the `next` URL already carries query params
        return accounts

    @staticmethod
    async def _get(url: str, params: dict | None) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
        if resp.status_code >= 400:
            raise FacebookException(f"Graph API HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

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
