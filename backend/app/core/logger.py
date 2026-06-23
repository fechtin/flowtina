"""Loguru-based logging with per-module log files and 30-day rotation.

Provides ``setup_logging()`` (call once at startup) and ``get_logger(module)`` to
obtain a logger bound to a named sink (system, api, scheduler, facebook,
telegram, ai).
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings

_MODULES = ("system", "api", "scheduler", "facebook", "telegram", "ai")
_configured = False


def setup_logging() -> None:
    """Configure loguru sinks. Idempotent."""
    global _configured
    if _configured:
        return

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{extra[module]}</cyan> | {message}",
        enqueue=True,
    )

    for module in _MODULES:
        logger.add(
            log_dir / f"{module}.log",
            level=settings.log_level,
            rotation="00:00",
            retention=f"{settings.log_retention_days} days",
            compression="zip",
            enqueue=True,
            filter=lambda record, m=module: record["extra"].get("module") == m,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        )

    logger.configure(extra={"module": "system"})
    _configured = True


def get_logger(module: str = "system"):
    """Return a logger bound to a module-specific sink."""
    if module not in _MODULES:
        module = "system"
    return logger.bind(module=module)
