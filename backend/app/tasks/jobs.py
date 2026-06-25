"""Background task functions executed by the scheduler.

Each task opens its own DB session (it runs outside the request lifecycle) and is
fully self-contained so it can be scheduled, run manually, or recovered after a
restart.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.repositories.repositories import SchedulerHistoryRepository, SchedulerJobRepository
from app.services.content_service import ContentService
from app.services.dashboard_service import ReportService
from app.services.telegram_service import TelegramService

log = get_logger("scheduler")


def _run_async(coro):
    """Run an async coroutine from the (sync) scheduler thread."""
    return asyncio.run(coro)


def run_generate_content(job_id: str) -> None:
    """Generate content for a job's project and record execution history."""
    db = SessionLocal()
    history_repo = SchedulerHistoryRepository(db)
    jobs = SchedulerJobRepository(db)
    started = datetime.now(timezone.utc)
    history = history_repo.create(job_id=job_id, started_at=started, status="running")
    db.commit()
    try:
        job = jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        posts = _run_async(
            ContentService(db).generate_for_project(
                job.project_id,
                content_type=job.content_type,
                language=job.language,
                auto_publish=job.auto_publish,
                require_approval=job.require_approval,
                target_page_id=job.facebook_page_id,
            )
        )
        job.last_run_at = started
        history.status = "completed"
        history.message = f"Generated {len(posts)} post(s)"
        history.finished_at = datetime.now(timezone.utc)
        history.duration_ms = int((history.finished_at - started).total_seconds() * 1000)
        db.commit()
        log.info(f"Job {job_id} completed: {history.message}")
    except Exception as exc:  # noqa: BLE001 - record and notify
        db.rollback()
        history.status = "failed"
        history.message = str(exc)[:1000]
        history.finished_at = datetime.now(timezone.utc)
        db.commit()
        log.error(f"Job {job_id} failed: {exc}")
    finally:
        db.close()


def send_daily_report(project_id: str) -> None:
    """Generate a daily report and push it to Telegram if configured."""
    db = SessionLocal()
    try:
        content = ReportService(db).generate(project_id, "daily")
        _run_async(TelegramService(db).send(project_id, content, type_="daily_report"))
    except Exception as exc:  # noqa: BLE001 - reports are best-effort
        log.warning(f"Daily report for {project_id} failed: {exc}")
    finally:
        db.close()


def engage_comments() -> None:
    """Poll pages with auto-engagement enabled and like/reply to new comments."""
    from app.services.facebook_engagement_service import FacebookEngagementService

    db = SessionLocal()
    try:
        count = _run_async(FacebookEngagementService(db).engage_all())
        if count:
            log.info(f"Comment engagement processed {count} new comment(s)")
    except Exception as exc:  # noqa: BLE001 - engagement is best-effort
        log.warning(f"Comment engagement run failed: {exc}")
    finally:
        db.close()


def consolidate_memories() -> None:
    """Nightly: decay, archive and re-summarize each follower's long-term memory."""
    from app.repositories.repositories import ConversationRepository
    from app.services.memory.service import MemoryService

    db = SessionLocal()
    try:
        service = MemoryService(db)
        conversations = ConversationRepository(db).list_active()
        done = 0
        for conversation in conversations:
            try:
                _run_async(service.consolidate(conversation))
                db.commit()
                done += 1
            except Exception as exc:  # noqa: BLE001 - one bad user must not stop others
                db.rollback()
                log.warning(f"Memory consolidation failed for {conversation.id}: {exc}")
        if done:
            log.info(f"Memory consolidation processed {done} conversation(s)")
    finally:
        db.close()


def cleanup_logs(retention_days: int = 30) -> None:
    """Delete system logs older than the retention window."""
    from app.repositories.repositories import SystemLogRepository

    db = SessionLocal()
    try:
        removed = SystemLogRepository(db).cleanup_older_than(retention_days)
        db.commit()
        log.info(f"Cleanup removed {removed} old system log rows")
    finally:
        db.close()
