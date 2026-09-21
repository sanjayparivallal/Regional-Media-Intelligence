"""
Harvest Scheduler — APScheduler daily cron job.

Schedules automatic ePaper harvesting at a configurable IST time.
Also supports manual trigger via API (see api/harvesting.py).

Configuration (via .env):
    HARVEST_SCHEDULE     — cron time in HH:MM (default: 06:30)
    HARVEST_TIMEZONE     — timezone name (default: Asia/Kolkata)
    HARVEST_MAX_CONCURRENCY — concurrent downloads (default: 5)
"""

import asyncio
import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_scheduled_harvest():
    """Entry point called by APScheduler."""
    from harvesting.service import HarvestingService
    from harvesting.utils import get_ist_date

    logger.info("Scheduled harvest triggered.")
    service = HarvestingService()
    try:
        result = await service.run_harvest(
            target_date=get_ist_date(),
            triggered_by="scheduler",
        )
        logger.info(
            f"Scheduled harvest complete: "
            f"successful={result.successful} "
            f"failed={result.failed} "
            f"duration={result.duration_seconds:.1f}s"
        )
    except Exception:
        logger.exception("Scheduled harvest raised an unexpected exception.")


def start_scheduler() -> AsyncIOScheduler:
    """
    Create and start the APScheduler cron job.

    Called once from FastAPI's lifespan context manager (main.py).
    Returns the scheduler so it can be shut down cleanly on app exit.
    """
    global _scheduler
    from config import get_settings
    settings = get_settings()

    schedule_time = getattr(settings, "harvest_schedule", "06:30")
    timezone = getattr(settings, "harvest_timezone", "Asia/Kolkata")

    try:
        hour, minute = schedule_time.split(":")
    except ValueError:
        hour, minute = "6", "30"
        logger.warning(f"Invalid HARVEST_SCHEDULE '{schedule_time}', defaulting to 06:30")

    _scheduler = AsyncIOScheduler(timezone=timezone)
    _scheduler.add_job(
        _run_scheduled_harvest,
        CronTrigger(hour=int(hour), minute=int(minute), timezone=timezone),
        id="daily_harvest",
        name="Daily ePaper Harvest",
        replace_existing=True,
        misfire_grace_time=3600,   # Allow up to 1h late start (e.g. after restart)
    )
    _scheduler.start()
    logger.info(
        f"Harvest scheduler started — daily at {schedule_time} {timezone}"
    )
    return _scheduler


def stop_scheduler():
    """Gracefully shut down the scheduler. Called from lifespan shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Harvest scheduler stopped.")
    _scheduler = None


async def trigger_now(target_date: date | None = None) -> None:
    """
    Manually trigger a harvest immediately (used by API endpoint).

    Runs in background — does not block the API response.
    """
    from harvesting.service import HarvestingService
    from harvesting.utils import get_ist_date

    service = HarvestingService()
    result = await service.run_harvest(
        target_date=target_date or get_ist_date(),
        triggered_by="api",
    )
    return result
