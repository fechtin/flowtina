"""Request-logging and in-memory rate-limiting middleware (no Redis)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request id and log method, path, status and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        log.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration_ms}ms)"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window-ish sliding rate limiter keyed by client IP.

    Lightweight and memory-bounded; suitable for a single-process deployment.
    """

    def __init__(self, app) -> None:  # noqa: ANN001
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/api/v1/health", "/health", "/metrics"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "anonymous"
        authed = request.headers.get("authorization") is not None
        limit = settings.rate_limit_authenticated if authed else settings.rate_limit_anonymous

        now = time.time()
        window = self._hits[client_ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {"code": "TOO_MANY_REQUESTS", "message": "Rate limit exceeded"},
                },
            )
        window.append(now)
        return await call_next(request)
