"""APScheduler configuration and job registration."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.jobs import (
    job_blacklist_check,
    job_dns_validation,
    job_health_check,
    job_metrics_update,
    job_monthly_rotation,
    job_quarantine_check,
    job_retry_queue,
    job_sync_warmup_quotas,
    job_warmup_daily,
)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the scheduler with all cron jobs."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Health check every 5 minutes
    scheduler.add_job(
        job_health_check,
        "interval",
        minutes=5,
        id="health_check",
        name="Health Check",
        replace_existing=True,
    )

    # Blacklist check every 4 hours
    scheduler.add_job(
        job_blacklist_check,
        "interval",
        hours=4,
        id="blacklist_check",
        name="Blacklist Check",
        replace_existing=True,
    )

    # Warmup daily tick at midnight UTC
    scheduler.add_job(
        job_warmup_daily,
        "cron",
        hour=0,
        minute=0,
        id="warmup_daily",
        name="Warmup Daily Tick",
        replace_existing=True,
    )

    # Monthly rotation on the 1st at 03:00 UTC
    scheduler.add_job(
        job_monthly_rotation,
        "cron",
        day=1,
        hour=3,
        minute=0,
        id="monthly_rotation",
        name="Monthly IP Rotation",
        replace_existing=True,
    )

    # DNS validation daily at 06:00 UTC
    scheduler.add_job(
        job_dns_validation,
        "cron",
        hour=6,
        minute=0,
        id="dns_validation",
        name="DNS Validation",
        replace_existing=True,
    )

    # Quarantine check daily at 04:00 UTC
    scheduler.add_job(
        job_quarantine_check,
        "cron",
        hour=4,
        minute=0,
        id="quarantine_check",
        name="Quarantine Check",
        replace_existing=True,
    )

    # Prometheus metrics update every minute
    scheduler.add_job(
        job_metrics_update,
        "interval",
        minutes=1,
        id="metrics_update",
        name="Metrics Update",
        replace_existing=True,
    )

    # Retry failed scraper-pro forwards every 2 minutes
    scheduler.add_job(
        job_retry_queue,
        "interval",
        minutes=2,
        id="retry_queue",
        name="Retry Queue",
        replace_existing=True,
    )

    # Sync warmup quotas to MailWizz every hour
    scheduler.add_job(
        job_sync_warmup_quotas,
        "interval",
        hours=1,
        id="sync_warmup_quotas",
        name="Sync Warmup Quotas",
        replace_existing=True,
    )

    return scheduler
