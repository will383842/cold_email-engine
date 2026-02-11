"""System health monitoring: PowerMTA, disk, RAM, queue."""

import shutil
from datetime import datetime

import psutil
import structlog
from sqlalchemy.orm import Session

from app.enums import AlertCategory, AlertSeverity
from app.models import HealthCheck
from app.services.powermta_config import PowerMTAConfig
from app.services.telegram_alerter import alerter

logger = structlog.get_logger(__name__)

DISK_WARNING_PCT = 85.0
RAM_WARNING_PCT = 90.0
QUEUE_WARNING_SIZE = 50000


class HealthMonitor:
    """Monitor system health and PowerMTA status."""

    def __init__(self, db: Session):
        self.db = db
        self.pmta = PowerMTAConfig()

    def check_pmta(self) -> bool:
        """Check if PowerMTA is running."""
        return self.pmta.is_running()

    def check_disk(self) -> float:
        """Return disk usage percentage."""
        try:
            usage = shutil.disk_usage("/")
            return (usage.used / usage.total) * 100
        except Exception:
            return 0.0

    def check_ram(self) -> float:
        """Return RAM usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    def check_queue(self) -> int:
        """Return PowerMTA queue size."""
        return self.pmta.get_queue_size()

    async def run_health_check(self) -> HealthCheck:
        """Run full health check and save to DB."""
        pmta_running = self.check_pmta()
        disk_pct = self.check_disk()
        ram_pct = self.check_ram()
        queue_size = self.check_queue()

        check = HealthCheck(
            timestamp=datetime.utcnow(),
            pmta_running=pmta_running,
            pmta_queue_size=queue_size,
            disk_usage_pct=round(disk_pct, 1),
            ram_usage_pct=round(ram_pct, 1),
        )
        self.db.add(check)
        self.db.commit()

        # Alert on issues
        if not pmta_running:
            await alerter.send(
                "PowerMTA is *NOT RUNNING*!",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.HEALTH,
                db=self.db,
            )

        if disk_pct > DISK_WARNING_PCT:
            await alerter.send(
                f"Disk usage at *{disk_pct:.1f}%*",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.HEALTH,
                db=self.db,
            )

        if ram_pct > RAM_WARNING_PCT:
            await alerter.send(
                f"RAM usage at *{ram_pct:.1f}%*",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.HEALTH,
                db=self.db,
            )

        if queue_size > QUEUE_WARNING_SIZE:
            await alerter.send(
                f"PowerMTA queue size: *{queue_size}* (threshold: {QUEUE_WARNING_SIZE})",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.HEALTH,
                db=self.db,
            )

        logger.info(
            "health_check_complete",
            pmta=pmta_running,
            disk=disk_pct,
            ram=ram_pct,
            queue=queue_size,
        )
        return check

    def get_latest(self) -> HealthCheck | None:
        """Return the most recent health check."""
        return (
            self.db.query(HealthCheck).order_by(HealthCheck.timestamp.desc()).first()
        )

    def get_status_summary(self) -> dict:
        """Return a summary dict for the /health endpoint."""
        latest = self.get_latest()
        if not latest:
            return {"status": "unknown", "message": "No health checks recorded yet"}

        issues = []
        if not latest.pmta_running:
            issues.append("PowerMTA down")
        if latest.disk_usage_pct > DISK_WARNING_PCT:
            issues.append(f"Disk {latest.disk_usage_pct}%")
        if latest.ram_usage_pct > RAM_WARNING_PCT:
            issues.append(f"RAM {latest.ram_usage_pct}%")

        return {
            "status": "degraded" if issues else "healthy",
            "issues": issues,
            "pmta_running": latest.pmta_running,
            "pmta_queue_size": latest.pmta_queue_size,
            "disk_usage_pct": latest.disk_usage_pct,
            "ram_usage_pct": latest.ram_usage_pct,
            "last_check": latest.timestamp.isoformat(),
        }
