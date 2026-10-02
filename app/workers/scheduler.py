from __future__ import annotations

import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: Optional[object] = None


def start_scheduler() -> None:
    """Start APScheduler for periodic jobs when WORKER_ENABLED=true."""
    global _scheduler
    settings = get_settings()
    if not settings.worker_enabled:
        return
    if _scheduler is not None:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed; skipping scheduled jobs")
        return

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    def daily_attendance_reminder() -> None:
        logger.info("Scheduled job: daily attendance reminder (stub — wire tenant loop in production)")

    scheduler.add_job(daily_attendance_reminder, CronTrigger(hour=10, minute=0))
    scheduler.start()
    _scheduler = scheduler
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Background scheduler stopped")
