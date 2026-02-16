"""Scheduled job functions for APScheduler."""

import structlog

from app.database import SessionLocal
from app.services.blacklist_checker import BlacklistChecker
from app.services.dns_validator import DNSValidator
from app.services.health_monitor import HealthMonitor
from app.services.ip_manager import IPManager
from app.services.warmup_engine import WarmupEngine

logger = structlog.get_logger(__name__)


async def job_health_check() -> None:
    """Run system health check (every 5 min)."""
    db = SessionLocal()
    try:
        monitor = HealthMonitor(db)
        await monitor.run_health_check()
    except Exception as exc:
        logger.error("job_health_check_failed", error=str(exc))
    finally:
        db.close()


async def job_blacklist_check() -> None:
    """Check all active IPs against 9 DNS blacklists (every 4h)."""
    db = SessionLocal()
    try:
        checker = BlacklistChecker(db)
        results = await checker.check_all_ips()
        if results:
            # Trigger IP manager for newly listed IPs
            mgr = IPManager(db)
            for ip_addr, bl_names in results.items():
                from app.models import IP

                ip = db.query(IP).filter(IP.address == ip_addr).first()
                if ip:
                    await mgr.handle_blacklist(ip, bl_names)
        logger.info("job_blacklist_check_complete", listings=len(results))
    except Exception as exc:
        logger.error("job_blacklist_check_failed", error=str(exc))
    finally:
        db.close()


async def job_warmup_daily() -> None:
    """Run daily warmup tick — advance phases, check safety (midnight UTC)."""
    db = SessionLocal()
    try:
        engine = WarmupEngine(db)
        await engine.daily_tick()
        logger.info("job_warmup_daily_complete")
    except Exception as exc:
        logger.error("job_warmup_daily_failed", error=str(exc))
    finally:
        db.close()


async def job_monthly_rotation() -> None:
    """Execute monthly IP rotation (1st of month 03:00 UTC)."""
    db = SessionLocal()
    try:
        mgr = IPManager(db)
        result = mgr.monthly_rotation()
        logger.info("job_monthly_rotation_complete", **result)
    except Exception as exc:
        logger.error("job_monthly_rotation_failed", error=str(exc))
    finally:
        db.close()


async def job_dns_validation() -> None:
    """Validate DNS for all domains (daily 06:00 UTC)."""
    db = SessionLocal()
    try:
        validator = DNSValidator(db)
        results = validator.validate_all()
        logger.info("job_dns_validation_complete", domains=len(results))
    except Exception as exc:
        logger.error("job_dns_validation_failed", error=str(exc))
    finally:
        db.close()


async def job_quarantine_check() -> None:
    """Release IPs from quarantine when rest period is over (daily 04:00 UTC)."""
    db = SessionLocal()
    try:
        mgr = IPManager(db)
        released = mgr.check_quarantine_release()
        logger.info("job_quarantine_check_complete", released=len(released))
    except Exception as exc:
        logger.error("job_quarantine_check_failed", error=str(exc))
    finally:
        db.close()


async def job_metrics_update() -> None:
    """Update Prometheus gauges from DB (every 1 min)."""
    db = SessionLocal()
    try:
        from app.api.routes.metrics import update_metrics_from_db

        update_metrics_from_db(db)
    except Exception as exc:
        logger.error("job_metrics_update_failed", error=str(exc))
    finally:
        db.close()


async def job_retry_queue() -> None:
    """Retry failed scraper-pro API calls (every 2 min)."""
    try:
        from app.services.retry_queue import process_queue

        await process_queue()
    except Exception as exc:
        logger.error("job_retry_queue_failed", error=str(exc))


async def job_sync_warmup_quotas() -> None:
    """Sync warmup quotas to MailWizz via API (every hour)."""
    db = SessionLocal()
    try:
        from app.enums import WarmupPhase
        from app.models import IP, WarmupPlan
        from app.services.mailwizz_api_client import MailWizzAPIClient
        from app.services.mailwizz_db import mailwizz_db

        client = MailWizzAPIClient()

        # Get all active warmup plans
        plans = (
            db.query(WarmupPlan)
            .filter(WarmupPlan.phase != WarmupPhase.COMPLETED.value)
            .all()
        )

        synced = 0
        for plan in plans:
            ip = db.query(IP).filter(IP.id == plan.ip_id).first()
            if not ip or not ip.mailwizz_server_id:
                continue

            # Try API first, fallback to MySQL
            if client._is_configured():
                success = await client.update_delivery_server_quota(
                    server_id=ip.mailwizz_server_id,
                    daily_quota=plan.current_daily_quota,
                )
                if success:
                    synced += 1
            else:
                # Fallback to MySQL
                success = await mailwizz_db.update_quota(
                    server_id=ip.mailwizz_server_id,
                    hourly_quota=None,
                    daily_quota=plan.current_daily_quota,
                )
                if success:
                    synced += 1

        logger.info("job_sync_warmup_quotas_complete", synced=synced, total=len(plans))
    except Exception as exc:
        logger.error("job_sync_warmup_quotas_failed", error=str(exc))
    finally:
        db.close()
