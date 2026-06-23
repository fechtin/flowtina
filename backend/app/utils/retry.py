"""Async retry helper with exponential backoff (1s, 2s, 5s)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

_BACKOFF = (1, 2, 5)


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    backoff: tuple[int, ...] = _BACKOFF,
    on_error: Callable[[int, Exception], None] | None = None,
) -> T:
    """Run ``func`` up to ``attempts`` times with exponential backoff.

    Re-raises the last exception if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await func()
        except Exception as exc:  # noqa: BLE001 - retried then re-raised
            last_exc = exc
            if on_error:
                on_error(attempt, exc)
            if attempt < attempts - 1:
                delay = backoff[min(attempt, len(backoff) - 1)]
                await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc
