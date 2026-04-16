"""Scheduler setup for future background polling jobs."""

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import Settings


def create_scheduler(settings: Settings) -> BackgroundScheduler:
    """Create the background scheduler without registering business jobs yet."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.configure(
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
        }
    )
    return scheduler
