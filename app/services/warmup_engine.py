"""IP warmup engine — 6-week progressive quota increase via MailWizz."""

from datetime import datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import AlertCategory, AlertSeverity, IPStatus, WarmupPhase
from app.models import IP, WarmupDailyStat, WarmupPlan
from app.services.telegram_alerter import alerter

logger = structlog.get_logger(__name__)

PHASE_QUOTAS = {
    WarmupPhase.WEEK_1: settings.WARMUP_WEEK1_QUOTA,
    WarmupPhase.WEEK_2: settings.WARMUP_WEEK2_QUOTA,
    WarmupPhase.WEEK_3: settings.WARMUP_WEEK3_QUOTA,
    WarmupPhase.WEEK_4: settings.WARMUP_WEEK4_QUOTA,
    WarmupPhase.WEEK_5: settings.WARMUP_WEEK5_QUOTA,
    WarmupPhase.WEEK_6: settings.WARMUP_WEEK6_QUOTA,
}

PHASE_ORDER = [
    WarmupPhase.WEEK_1,
    WarmupPhase.WEEK_2,
    WarmupPhase.WEEK_3,
    WarmupPhase.WEEK_4,
    WarmupPhase.WEEK_5,
    WarmupPhase.WEEK_6,
    WarmupPhase.COMPLETED,
]


class WarmupEngine:
    """Manage the 6-week warmup progression for IPs."""

    def __init__(self, db: Session):
        self.db = db

    def create_plan(self, ip: IP) -> WarmupPlan:
        """Create a warmup plan for an IP entering WARMING state."""
        plan = WarmupPlan(
            ip_id=ip.id,
            phase=WarmupPhase.WEEK_1.value,
            started_at=datetime.utcnow(),
            current_daily_quota=PHASE_QUOTAS[WarmupPhase.WEEK_1],
            target_daily_quota=settings.WARMUP_WEEK6_QUOTA,
        )
        self.db.add(plan)
        self.db.commit()
        logger.info("warmup_plan_created", ip=ip.address, quota=plan.current_daily_quota)
        return plan

    def record_daily_stats(
        self,
        plan: WarmupPlan,
        sent: int,
        delivered: int,
        bounced: int,
        complaints: int,
        opens: int = 0,
        clicks: int = 0,
    ) -> WarmupDailyStat:
        """Record daily sending statistics for a warmup plan."""
        stat = WarmupDailyStat(
            plan_id=plan.id,
            date=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            sent=sent,
            delivered=delivered,
            bounced=bounced,
            complaints=complaints,
            opens=opens,
            clicks=clicks,
        )
        self.db.add(stat)
        self.db.commit()
        return stat

    def _compute_7d_rates(self, plan: WarmupPlan) -> tuple[float, float]:
        """Compute 7-day bounce rate and spam (complaint) rate."""
        since = datetime.utcnow() - timedelta(days=7)
        stats = (
            self.db.query(WarmupDailyStat)
            .filter(WarmupDailyStat.plan_id == plan.id, WarmupDailyStat.date >= since)
            .all()
        )
        total_sent = sum(s.sent for s in stats)
        total_bounced = sum(s.bounced for s in stats)
        total_complaints = sum(s.complaints for s in stats)

        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0.0
        spam_rate = (total_complaints / total_sent * 100) if total_sent > 0 else 0.0
        return bounce_rate, spam_rate

    async def check_safety(self, plan: WarmupPlan) -> bool:
        """Check safety thresholds. Pause plan if exceeded. Returns True if safe."""
        bounce_rate, spam_rate = self._compute_7d_rates(plan)
        plan.bounce_rate_7d = bounce_rate
        plan.spam_rate_7d = spam_rate

        ip = self.db.query(IP).filter(IP.id == plan.ip_id).first()
        ip_addr = ip.address if ip else "unknown"

        if bounce_rate > settings.WARMUP_MAX_BOUNCE_RATE:
            plan.paused = True
            plan.pause_until = datetime.utcnow() + timedelta(days=2)
            self.db.commit()
            await alerter.send(
                f"Warmup paused for *{ip_addr}*: bounce rate {bounce_rate:.1f}% > {settings.WARMUP_MAX_BOUNCE_RATE}%",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.WARMUP,
                db=self.db,
            )
            return False

        if spam_rate > settings.WARMUP_MAX_SPAM_RATE:
            plan.paused = True
            plan.pause_until = datetime.utcnow() + timedelta(days=3)
            self.db.commit()
            await alerter.send(
                f"Warmup paused for *{ip_addr}*: spam rate {spam_rate:.2f}% > {settings.WARMUP_MAX_SPAM_RATE}%",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.WARMUP,
                db=self.db,
            )
            return False

        self.db.commit()
        return True

    def _next_phase(self, current: WarmupPhase) -> WarmupPhase:
        """Get the next phase in the warmup progression."""
        idx = PHASE_ORDER.index(current)
        if idx + 1 < len(PHASE_ORDER):
            return PHASE_ORDER[idx + 1]
        return WarmupPhase.COMPLETED

    async def advance_phase(self, plan: WarmupPlan) -> bool:
        """Try to advance to the next warmup phase. Returns True if advanced."""
        current = WarmupPhase(plan.phase)
        if current == WarmupPhase.COMPLETED:
            return False

        # Check if 7 days have passed in current phase
        stats_count = (
            self.db.query(WarmupDailyStat)
            .filter(
                WarmupDailyStat.plan_id == plan.id,
                WarmupDailyStat.date >= datetime.utcnow() - timedelta(days=7),
            )
            .count()
        )
        if stats_count < 7:
            return False

        safe = await self.check_safety(plan)
        if not safe:
            return False

        next_phase = self._next_phase(current)
        plan.phase = next_phase.value

        if next_phase == WarmupPhase.COMPLETED:
            plan.current_daily_quota = plan.target_daily_quota
            ip = self.db.query(IP).filter(IP.id == plan.ip_id).first()
            if ip:
                ip.status = IPStatus.ACTIVE.value
                ip.status_changed_at = datetime.utcnow()
                await alerter.send(
                    f"Warmup completed for *{ip.address}* — now ACTIVE at {plan.target_daily_quota}/day",
                    severity=AlertSeverity.INFO,
                    category=AlertCategory.WARMUP,
                    db=self.db,
                )
        else:
            plan.current_daily_quota = PHASE_QUOTAS.get(next_phase, plan.current_daily_quota)

        self.db.commit()
        logger.info("warmup_phase_advanced", plan_id=plan.id, phase=next_phase.value)
        return True

    async def daily_tick(self) -> None:
        """Run daily warmup logic for all active plans."""
        plans = (
            self.db.query(WarmupPlan)
            .filter(WarmupPlan.phase != WarmupPhase.COMPLETED.value)
            .all()
        )
        for plan in plans:
            # Unpause if pause_until has passed
            if plan.paused and plan.pause_until and plan.pause_until <= datetime.utcnow():
                plan.paused = False
                plan.pause_until = None
                self.db.commit()

            if plan.paused:
                continue

            await self.advance_phase(plan)
