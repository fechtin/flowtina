"""Browser-emulating HTTP fetcher for external content sources.

Many sites sit behind a WAF / anti-bot layer that rejects non-browser clients
with HTTP 403 (or 429/503) and only serves content once a session cookie from an
initial "challenge" request is presented. This helper emulates a normal browser:
realistic headers, a per-request cookie jar, redirect following, and an automatic
warm-up + retry against the site root when a request is challenged.

Every collector that fetches external pages/feeds should go through this module
so the whole system presents one consistent, browser-like identity.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("system")

# Status codes typically returned by anti-bot layers before a cookie is set.
_CHALLENGE_STATUSES = frozenset({403, 429, 503})


def browser_headers() -> dict[str, str]:
    """Return realistic desktop-browser request headers.

    The User-Agent is configurable via ``settings.http_user_agent`` so the
    fingerprint can be rotated without code changes.
    """
    return {
        "User-Agent": settings.http_user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "application/rss+xml,application/atom+xml;q=0.8,*/*;q=0.7"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


async def fetch_bytes(url: str, *, timeout: int | None = None) -> bytes:
    """Fetch ``url`` the way a browser would and return the response body.

    On an anti-bot challenge (403/429/503) the helper warms up by requesting the
    site root on the same session — capturing any challenge cookie — then retries
    the original URL. Raises ``httpx.HTTPStatusError`` if it still fails.
    """
    parts = urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}/"
    timeout = timeout if timeout is not None else settings.http_fetch_timeout_seconds

    async with httpx.AsyncClient(
        headers=browser_headers(),
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        if resp.status_code in _CHALLENGE_STATUSES and url != root:
            log.debug(f"HTTP {resp.status_code} challenge on {url}; warming up via {root}")
            # The challenge response itself sets the session cookie (even on 403);
            # httpx stores it on the client, so the retry carries it through.
            await client.get(root)
            resp = await client.get(url, headers={"Referer": root})
        resp.raise_for_status()
        return resp.content
