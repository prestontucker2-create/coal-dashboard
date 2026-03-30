from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        }
    )
    return scheduler


def register_domain_job(
    scheduler: AsyncIOScheduler,
    job_id: str,
    callback,
    interval_seconds: int,
    **kwargs,
):
    scheduler.add_job(
        callback,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=job_id,
        replace_existing=True,
        kwargs=kwargs,
    )
    logger.info(f"Registered job: {job_id} (every {interval_seconds}s)")
