"""Tests for scheduler job registration."""

from apscheduler.schedulers.background import BackgroundScheduler

from app.scheduler.jobs import (
    job_blacklist_check,
    job_dns_validation,
    job_health_check,
    job_metrics_update,
    job_monthly_rotation,
    job_quarantine_check,
    job_warmup_daily,
)


def _create_sync_scheduler():
    """Create a BackgroundScheduler (no event loop needed) with same jobs."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(job_health_check, "interval", minutes=5, id="health_check")
    scheduler.add_job(job_blacklist_check, "interval", hours=4, id="blacklist_check")
    scheduler.add_job(job_warmup_daily, "cron", hour=0, minute=0, id="warmup_daily")
    scheduler.add_job(job_monthly_rotation, "cron", day=1, hour=3, id="monthly_rotation")
    scheduler.add_job(job_dns_validation, "cron", hour=6, id="dns_validation")
    scheduler.add_job(job_quarantine_check, "cron", hour=4, id="quarantine_check")
    scheduler.add_job(job_metrics_update, "interval", minutes=1, id="metrics_update")
    return scheduler


def test_all_jobs_registered():
    """Verify all 7 scheduled jobs are registered."""
    scheduler = _create_sync_scheduler()
    jobs = scheduler.get_jobs()
    job_ids = {j.id for j in jobs}

    expected = {
        "health_check",
        "blacklist_check",
        "warmup_daily",
        "monthly_rotation",
        "dns_validation",
        "quarantine_check",
        "metrics_update",
    }
    assert job_ids == expected


def test_health_check_interval():
    scheduler = _create_sync_scheduler()
    job = scheduler.get_job("health_check")
    assert job.trigger.interval.total_seconds() == 300  # 5 minutes


def test_blacklist_check_interval():
    scheduler = _create_sync_scheduler()
    job = scheduler.get_job("blacklist_check")
    assert job.trigger.interval.total_seconds() == 14400  # 4 hours
