"""Standalone scheduler process entrypoint.

Run as its own systemd service so the web workers stay stateless:
    python -m app.scheduler.runner
"""

from __future__ import annotations

import signal
import time

from app.core.config import settings
from app.core.database import init_db
from app.core.logger import get_logger, setup_logging
from app.scheduler.manager import scheduler_manager

setup_logging()
log = get_logger("scheduler")
_running = True


def _handle_signal(_signum, _frame) -> None:  # noqa: ANN001
    global _running
    _running = False


def main() -> None:
    if settings.is_sqlite:
        init_db()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    scheduler_manager.start()
    log.info("Scheduler runner started; waiting for jobs")
    try:
        while _running:
            time.sleep(1)
    finally:
        scheduler_manager.shutdown()
        log.info("Scheduler runner stopped")


if __name__ == "__main__":
    main()
