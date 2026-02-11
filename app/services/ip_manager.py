"""IP lifecycle state machine: ACTIVE → RETIRING → RESTING → WARMING → ACTIVE."""

import json
from datetime import datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import AlertCategory, AlertSeverity, IPStatus
from app.models import IP
from app.services.telegram_alerter import alerter

logger = structlog.get_logger(__name__)

# Valid state transitions
TRANSITIONS = {
    IPStatus.ACTIVE: [IPStatus.RETIRING, IPStatus.BLACKLISTED],
    IPStatus.RETIRING: [IPStatus.RESTING],
    IPStatus.RESTING: [IPStatus.WARMING, IPStatus.STANDBY],
    IPStatus.WARMING: [IPStatus.ACTIVE, IPStatus.BLACKLISTED],
    IPStatus.BLACKLISTED: [IPStatus.RESTING, IPStatus.STANDBY],
    IPStatus.STANDBY: [IPStatus.WARMING, IPStatus.ACTIVE],
}


class IPManager:
    """Manage the IP lifecycle and rotation."""

    def __init__(self, db: Session):
        self.db = db

    def transition(self, ip: IP, new_status: IPStatus, reason: str = "") -> bool:
        """Attempt a state transition. Returns True on success."""
        current = IPStatus(ip.status)
        allowed = TRANSITIONS.get(current, [])
        if new_status not in allowed:
            logger.warning(
                "invalid_ip_transition",
                ip=ip.address,
                current=current.value,
                target=new_status.value,
            )
            return False

        old_status = ip.status
        ip.status = new_status.value
        ip.status_changed_at = datetime.utcnow()

        if new_status == IPStatus.RESTING:
            ip.quarantine_until = datetime.utcnow() + timedelta(days=settings.IP_REST_DAYS)

        self.db.commit()
        logger.info(
            "ip_transition",
            ip=ip.address,
            from_status=old_status,
            to_status=new_status.value,
            reason=reason,
        )
        return True

    def get_active_ips(self, purpose: str | None = None) -> list[IP]:
        """Return all active IPs, optionally filtered by purpose."""
        q = self.db.query(IP).filter(IP.status == IPStatus.ACTIVE.value)
        if purpose:
            q = q.filter(IP.purpose == purpose)
        return q.all()

    def get_standby_ips(self) -> list[IP]:
        """Return all standby IPs ready to be activated."""
        return self.db.query(IP).filter(IP.status == IPStatus.STANDBY.value).all()

    def activate_standby(self, ip: IP) -> bool:
        """Activate a standby IP (skip warmup — already warm)."""
        return self.transition(ip, IPStatus.ACTIVE, reason="standby_activation")

    async def handle_blacklist(self, ip: IP, blacklist_names: list[str]) -> None:
        """Handle IP blacklisting: transition + activate standby."""
        ip.blacklisted_on = json.dumps(blacklist_names)
        self.transition(ip, IPStatus.BLACKLISTED, reason=f"listed on {', '.join(blacklist_names)}")

        # Try to activate a standby IP
        standby = self.get_standby_ips()
        activated = None
        if standby:
            candidate = standby[0]
            if self.activate_standby(candidate):
                activated = candidate.address

        msg = (
            f"IP *{ip.address}* blacklisted on: {', '.join(blacklist_names)}\n"
            f"Standby activated: {activated or 'NONE — manual action required'}"
        )
        await alerter.send(
            msg,
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.BLACKLIST,
            db=self.db,
        )

    def check_quarantine_release(self) -> list[IP]:
        """Release IPs whose quarantine period has ended."""
        now = datetime.utcnow()
        resting_ips = (
            self.db.query(IP)
            .filter(IP.status == IPStatus.RESTING.value, IP.quarantine_until <= now)
            .all()
        )
        released = []
        for ip in resting_ips:
            if self.transition(ip, IPStatus.WARMING, reason="quarantine_ended"):
                released.append(ip)
                logger.info("ip_quarantine_released", ip=ip.address)
        return released

    def monthly_rotation(self) -> dict:
        """Execute monthly rotation: retire oldest active, promote resting."""
        active_ips = (
            self.db.query(IP)
            .filter(IP.status == IPStatus.ACTIVE.value)
            .order_by(IP.status_changed_at.asc())
            .all()
        )

        retired = []
        for ip in active_ips:
            if self.transition(ip, IPStatus.RETIRING, reason="monthly_rotation"):
                retired.append(ip.address)
                # Immediately move to resting (rotation = no grace period)
                self.transition(ip, IPStatus.RESTING, reason="monthly_rotation")

        return {"retired": retired, "count": len(retired)}
