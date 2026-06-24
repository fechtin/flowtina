"""Auto-engagement with comments on a page's own posts (Graph API only).

Polls recent published posts for new comments and, per the page's settings,
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
from app.models.post import Post
from app.prompts.defaults import DEFAULT_REPLY_PROMPT
from app.prompts.engine import prompt_engine
from app.repositories.repositories import (
    FacebookCommentRepository,
    FacebookPageRepository,
    FacebookPostRepository,
)
from app.services.ai_service import AIService
from app.services.facebook_service import GRAPH_API
from app.utils.text import strip_markdown

log = get_logger("facebook")

_LANG_NAMES = {"en": "English", "vi": "Vietnamese"}


class FacebookEngagementService:
    """Like and AI-reply to comments on the operator's own Facebook posts."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.pages = FacebookPageRepository(db)
        self.fb_posts = FacebookPostRepository(db)
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
                total += await self.engage_page(page)
            except Exception as exc:  # noqa: BLE001 - one bad page must not stop others
                log.error(f"Engagement failed for page {page.page_id}: {exc}")
        return total

    async def engage_page(self, page: FacebookPage) -> int:
        """Scan a page's recent posts and act on any unseen comments.

        Returns the number of newly processed comments.
        """
        token = decrypt_secret(page.access_token_encrypted)
        recent = [
            fp
            for fp in self.fb_posts.list(
                page_id=page.id, status="published", order_by="published_at", limit=None
            )
            if fp.facebook_post_id
        ][: settings.facebook_engage_max_posts]

        processed = 0
        for fb_post in recent:
            fb_post_id = fb_post.facebook_post_id
            if not fb_post_id:
                continue
            comments = await self._fetch_comments(fb_post_id, token)
            for comment in comments:
                if await self._process_comment(page, fb_post, comment, token):
                    processed += 1
        if processed:
            log.info(f"Engaged with {processed} new comment(s) on page {page.page_id}")
        return processed

    async def _process_comment(
        self, page: FacebookPage, fb_post, comment: dict, token: str
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
            facebook_post_id=fb_post.facebook_post_id,
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
                reply = await self._build_reply(page, fb_post, message)
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

    async def _build_reply(self, page: FacebookPage, fb_post, message: str) -> str:
        post = self.db.get(Post, fb_post.post_id)
        language = post.language if post else settings.default_language
        persona = (
            f"Voice and guidance: {page.reply_persona}" if page.reply_persona else ""
        )
        prompt = prompt_engine.render(
            DEFAULT_REPLY_PROMPT,
            {
                "language": _LANG_NAMES.get(language, language),
                "persona": persona,
                "post_content": (post.content if post else "")[:1500],
                "comment": message[:1000],
            },
        )
        result = await self.ai.generate(page.project_id, prompt)
        return strip_markdown(result.text).strip()[:8000]

    # --- Graph API ---

    async def _fetch_comments(self, fb_post_id: str, token: str) -> list[dict]:
        params: dict[str, str | int] = {
            "fields": "id,message,from{id,name},created_time",
            "order": "reverse_chronological",
            "limit": settings.facebook_engage_max_comments,
            "access_token": token,
        }
        url = f"{GRAPH_API}/{fb_post_id}/comments"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
        if resp.status_code >= 400:
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return list(resp.json().get("data", []))

    async def _like_comment(self, comment_id: str, token: str) -> None:
        await self._post(f"{GRAPH_API}/{comment_id}/likes", {"access_token": token})

    async def _reply_comment(self, comment_id: str, message: str, token: str) -> None:
        await self._post(
            f"{GRAPH_API}/{comment_id}/comments",
            {"message": message, "access_token": token},
        )

    @staticmethod
    async def _post(url: str, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
        if resp.status_code >= 400:
            raise FacebookException(
                f"Graph API HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()
