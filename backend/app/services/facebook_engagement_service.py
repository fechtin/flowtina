"""Auto-engagement with comments on a page's own posts (Graph API only).

Polls the page's recent posts for new comments and, per the page's settings,
likes them and/or posts an AI-generated reply. State is tracked in
``facebook_comments`` so every comment is acted on at most once.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import FacebookException, NotFoundException
from app.core.logger import get_logger
from app.core.security import decrypt_secret
from app.models.integration import FacebookPage
from app.prompts.defaults import DEFAULT_REPLY_PROMPT
from app.prompts.engine import prompt_engine
from app.repositories.repositories import (
    FacebookCommentRepository,
    FacebookPageRepository,
)
from app.services.ai_service import AIService
from app.services.facebook_service import GRAPH_API
from app.utils.text import strip_markdown

log = get_logger("facebook")


class FacebookEngagementService:
    """Like and AI-reply to comments on the page's own Facebook posts."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.pages = FacebookPageRepository(db)
        self.comments = FacebookCommentRepository(db)
        self.ai = AIService(db)

    # --- settings & reads ---

    def update_settings(
        self,
        page_id: str,
        *,
        auto_like_comments: bool | None = None,
        auto_reply_comments: bool | None = None,
        reply_persona: str | None = None,
    ) -> FacebookPage:
        page = self.pages.get(page_id)
        if not page:
            raise NotFoundException("Facebook page not found")
        if auto_like_comments is not None:
            page.auto_like_comments = auto_like_comments
        if auto_reply_comments is not None:
            page.auto_reply_comments = auto_reply_comments
        if reply_persona is not None:
            page.reply_persona = reply_persona.strip() or None
        self.db.commit()
        self.db.refresh(page)
        return page

    def list_comments(self, page_id: str, limit: int = 50) -> list:
        return self.comments.list_for_page(page_id, limit=limit)

    # --- orchestration ---

    async def engage_all(self) -> int:
        """Process every page that has like or reply auto-engagement enabled."""
        pages = [
            p
            for p in self.pages.list(limit=None)
            if p.enabled and (p.auto_like_comments or p.auto_reply_comments)
        ]
        total = 0
        for page in pages:
            try:
                total += int((await self.engage_page(page))["processed"])
            except Exception as exc:  # noqa: BLE001 - one bad page must not stop others
                log.error(f"Engagement failed for page {page.page_id}: {exc}")
        return total

    async def engage_page(self, page: FacebookPage) -> dict[str, object]:
        """Scan the page's recent posts and act on any unseen comments.

        Returns ``{processed, scanned, skipped, error}``: comments newly acted
        on, posts scanned, posts skipped because their comments could not be
        read, and a page-level error message (e.g. the token cannot list the
        page's posts) or ``None``.
        """
        token = decrypt_secret(page.access_token_encrypted)
        try:
            posts = await self._fetch_recent_posts(page.page_id, token)
        except FacebookException as exc:
            log.warning(f"Could not list posts for page {page.page_id}: {exc}")
            return {"processed": 0, "scanned": 0, "skipped": 0, "error": str(exc)}

        processed = 0
        skipped = 0
        for post in posts:
            post_id = str(post.get("id", ""))
            if not post_id:
                continue
            # A single inaccessible post (deleted, restricted) must not abort
            # the whole page run.
            try:
                comments = await self._fetch_comments(post_id, token)
            except FacebookException as exc:
                skipped += 1
                log.warning(f"Skipping post {post_id} on page {page.page_id}: {exc}")
                continue
            post_message = str(post.get("message") or "")
            for comment in comments:
                if await self._process_comment(page, post_id, post_message, comment, token):
                    processed += 1
        if processed:
            log.info(f"Engaged with {processed} new comment(s) on page {page.page_id}")
        return {
            "processed": processed,
            "scanned": len(posts),
            "skipped": skipped,
            "error": None,
        }

    async def _process_comment(
        self,
        page: FacebookPage,
        post_id: str,
        post_message: str,
        comment: dict,
        token: str,
    ) -> bool:
        comment_id = str(comment.get("id", ""))
        if not comment_id or self.comments.exists(comment_id):
            return False
        author = comment.get("from") or {}
        # Never engage with the page's own comments/replies.
        if str(author.get("id", "")) == page.page_id:
            return False

        message = (comment.get("message") or "").strip()
        record = self.comments.create(
            page_id=page.id,
            facebook_post_id=post_id,
            comment_id=comment_id,
            commenter_name=author.get("name"),
            message=message or None,
            processed_at=datetime.now(timezone.utc),
        )
        errors: list[str] = []

        if page.auto_like_comments:
            try:
                await self._like_comment(comment_id, token)
                record.liked = True
            except Exception as exc:  # noqa: BLE001 - record and continue to reply
                errors.append(f"like: {exc}")

        if page.auto_reply_comments and message:
            try:
                reply = await self._build_reply(page, post_message, message)
                if reply:
                    await self._reply_comment(comment_id, reply, token)
                    record.replied = True
                    record.reply_text = reply
            except Exception as exc:  # noqa: BLE001 - record failure, keep going
                errors.append(f"reply: {exc}")

        if errors:
            record.status = "error"
            record.error_message = "; ".join(errors)[:1000]
        self.db.commit()
        return True

    # --- AI reply ---

    async def _build_reply(self, page: FacebookPage, post_message: str, comment: str) -> str:
        persona = (
            f"Voice and guidance: {page.reply_persona}" if page.reply_persona else ""
        )
        prompt = prompt_engine.render(
            DEFAULT_REPLY_PROMPT,
            {
                "persona": persona,
                "post_content": post_message[:1500],
                "comment": comment[:1000],
            },
        )
        result = await self.ai.generate(page.project_id, prompt)
        return strip_markdown(result.text).strip()[:8000]

    # --- Graph API ---

    async def _fetch_recent_posts(self, page_id: str, token: str) -> list[dict]:
        """List the page's own recent posts (newest first)."""
        params: dict[str, str | int] = {
            "fields": "id,message",
            "limit": settings.facebook_engage_max_posts,
            "access_token": token,
        }
        data = await self._get(f"{GRAPH_API}/{page_id}/posts", params)
        return list(data.get("data", []))

    async def _fetch_comments(self, post_id: str, token: str) -> list[dict]:
        params: dict[str, str | int] = {
            "fields": "id,message,from{id,name},created_time",
            "order": "reverse_chronological",
            "limit": settings.facebook_engage_max_comments,
            "access_token": token,
        }
        data = await self._get(f"{GRAPH_API}/{post_id}/comments", params)
        return list(data.get("data", []))

    async def _like_comment(self, comment_id: str, token: str) -> None:
        await self._post(f"{GRAPH_API}/{comment_id}/likes", {"access_token": token})

    async def _reply_comment(self, comment_id: str, message: str, token: str) -> None:
        await self._post(
            f"{GRAPH_API}/{comment_id}/comments",
            {"message": message, "access_token": token},
        )

    @staticmethod
    async def _get(url: str, params: dict[str, str | int]) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
        if resp.status_code >= 400:
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    @staticmethod
    async def _post(url: str, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
        if resp.status_code >= 400:
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()
