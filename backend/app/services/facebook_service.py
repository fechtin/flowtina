"""Facebook publishing via the Meta Graph API (no browser automation)."""

from __future__ import annotations

import json
import mimetypes
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    FacebookException,
    NotFoundException,
    ValidationException,
)
from app.core.logger import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.models.integration import FacebookPage
from app.models.post import Post
from app.models.project import Project
from app.repositories.repositories import (
    FacebookPageRepository,
    FacebookPostRepository,
    PostRepository,
)
from app.schemas.content import FacebookPageCreate
from app.utils.media import remove_upload, upload_abs_path
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

    def connect_page(
        self, project_id: str, payload: FacebookPageCreate
    ) -> FacebookPage:
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

    async def _resolve_token(self, project: Project | None, token: str | None) -> str:
        """Resolve and persist the working Graph token for a project.

        Resolution order: the supplied token, then the project's previously
        stored token, then the server-configured system token. The token is
        exchanged for a long-lived one when possible and persisted (encrypted)
        on the project so later syncs need no re-entry. The caller commits.
        """
        stored = (
            decrypt_secret(project.facebook_system_token_encrypted)
            if project and project.facebook_system_token_encrypted
            else ""
        )
        token = (token or stored or settings.facebook_system_token or "").strip()
        if not token:
            raise ValidationException("No Facebook token provided or configured")
        token = await self._maybe_exchange_long_lived(token)
        if project is not None:
            project.facebook_system_token_encrypted = encrypt_secret(token)
        return token

    async def discover_pages(
        self, project_id: str, token: str | None = None
    ) -> list[dict]:
        """List the Pages a token can manage without connecting them.

        Lets the operator pick which Pages to import when a token grants access
        to more than one. The working token is persisted so the follow-up import
        needs no re-entry, but no Page rows are created here.
        """
        project = self.db.get(Project, project_id)
        token = await self._resolve_token(project, token)
        accounts = await self._fetch_accounts(token)
        if not accounts:
            raise FacebookException(
                "No Pages found for this token (check its permissions)"
            )
        self.db.commit()  # persist the resolved token for the follow-up import

        existing = {p.page_id for p in self.pages.list(project_id=project_id)}
        discovered: list[dict] = []
        for acc in accounts:
            page_id = str(acc.get("id", ""))
            if not page_id or not acc.get("access_token"):
                continue
            discovered.append(
                {
                    "page_id": page_id,
                    "page_name": acc.get("name") or page_id,
                    "already_connected": page_id in existing,
                }
            )
        return discovered

    async def import_pages(
        self,
        project_id: str,
        token: str | None = None,
        page_ids: list[str] | None = None,
    ) -> list[FacebookPage]:
        """Discover and connect the operator's Pages from a single token.

        Calls Graph ``/me/accounts`` to fetch each Page's id, name and per-page
        access token automatically — no manual page-id/token entry needed. Pages
        already connected are updated (token refreshed) rather than duplicated.

        When ``page_ids`` is given, only those Pages are connected and existing
        Pages are left untouched. When omitted, every discovered Page is
        connected and stale ones (no longer returned by the token) are pruned.
        """
        project = self.db.get(Project, project_id)
        token = await self._resolve_token(project, token)
        accounts = await self._fetch_accounts(token)
        if not accounts:
            raise FacebookException(
                "No Pages found for this token (check its permissions)"
            )

        selected = set(page_ids) if page_ids is not None else None
        existing = {p.page_id: p for p in self.pages.list(project_id=project_id)}
        result: list[FacebookPage] = []
        seen: set[str] = set()
        for acc in accounts:
            page_id = str(acc.get("id", ""))
            page_token = acc.get("access_token", "")
            if not page_id or not page_token:
                continue
            if selected is not None and page_id not in selected:
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

        # Full sync only: prune pages no longer returned by the token
        # (unassigned/removed on Facebook). Skipped when importing a selection.
        removed = 0
        if selected is None:
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
        params: dict | None = {
            "fields": "id,name,access_token",
            "limit": 100,
            "access_token": token,
        }
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
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
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
        call = self._build_publish_call(post, page.page_id, message, token)

        history = self.fb_posts.create(
            post_id=post.id, page_id=page.id, status="publishing"
        )
        start = time.perf_counter()
        try:
            data = await retry_async(
                call,
                attempts=3,
                on_error=lambda attempt, exc: log.warning(
                    f"FB publish attempt {attempt + 1}: {exc}"
                ),
            )
            duration = int((time.perf_counter() - start) * 1000)
            # A /photos response carries the photo id plus the feed story id in
            # ``post_id``; prefer the story id so links resolve to the post.
            fb_post_id = data.get("post_id") or data.get("id")
            history.status = "published"
            history.facebook_post_id = fb_post_id
            history.duration_ms = duration
            history.response_json = json.dumps(data)[:2000]
            history.published_at = datetime.now(timezone.utc)
            post.status = "published"
            post.published_at = datetime.now(timezone.utc)
            # The uploaded binary is only needed until publish succeeds.
            if post.image_path:
                remove_upload(post.image_path)
                post.image_path = None
            self.db.commit()
            log.info(f"Published post {post.id} to page {page.page_id} as {fb_post_id}")
            return {"facebook_post_id": fb_post_id, "duration_ms": duration}
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

    def _build_publish_call(
        self, post: Post, page_id: str, message: str, token: str
    ) -> Callable[[], Awaitable[dict]]:
        """Select the Graph endpoint for this post's content.

        An uploaded binary takes precedence over a URL image; with neither, the
        post is a plain text status published to ``/feed``. The returned thunk is
        re-invokable so ``retry_async`` can retry it safely.
        """
        if post.image_path:
            path = upload_abs_path(post.image_path)
            return lambda: self._post_photo_file(page_id, message, path, token)
        if post.image_url:
            data = {"url": post.image_url, "caption": message, "access_token": token}
            return lambda: self._call_graph(f"{GRAPH_API}/{page_id}/photos", data)
        data = {"message": message, "access_token": token}
        return lambda: self._call_graph(f"{GRAPH_API}/{page_id}/feed", data)

    @staticmethod
    async def _call_graph(url: str, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, data=data)
        if resp.status_code >= 400:
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    @staticmethod
    async def _post_photo_file(
        page_id: str, caption: str, path: Path, token: str
    ) -> dict:
        """Upload a local image as multipart/form-data to ``/{page_id}/photos``."""
        if not path.exists():
            raise FacebookException(f"Uploaded image is missing: {path.name}")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        url = f"{GRAPH_API}/{page_id}/photos"
        with path.open("rb") as fh:
            files = {"source": (path.name, fh, content_type)}
            data = {"caption": caption, "access_token": token}
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, data=data, files=files)
        if resp.status_code >= 400:
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()
