"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

# Create Celery app
celery_app = Celery(
    "email_engine",
    broker="redis://localhost:6379/0",  # Redis as broker
    backend="redis://localhost:6379/0",  # Redis as result backend
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Task routing (optional - for multiple queues)
celery_app.conf.task_routes = {
    "src.infrastructure.background.tasks.validate_contact_task": {"queue": "validation"},
    "src.infrastructure.background.tasks.inject_contact_to_mailwizz_task": {"queue": "mailwizz"},
    "src.infrastructure.background.tasks.send_campaign_task": {"queue": "campaigns"},
    "src.infrastructure.background.tasks.advance_warmup_task": {"queue": "warmup"},
    "src.infrastructure.background.tasks.consolidate_warmup_stats_task": {"queue": "warmup"},
}

# Beat schedule for periodic tasks (cron-like)
# All times are in UTC
celery_app.conf.beat_schedule = {
    # Consolidate warmup stats from Redis to PostgreSQL
    # Runs daily at 00:30 UTC to process previous day's data
    "consolidate-warmup-stats-daily": {
        "task": "src.infrastructure.background.tasks.consolidate_warmup_stats_task",
        "schedule": crontab(hour=0, minute=30),  # 00:30 UTC every day
    },
    # Advance warmup phases (check if IPs ready for next phase)
    # Runs daily at 01:00 UTC after stats consolidation
    "advance-warmup-daily": {
        "task": "src.infrastructure.background.tasks.advance_warmup_task",
        "schedule": crontab(hour=1, minute=0),  # 01:00 UTC every day
    },
}
