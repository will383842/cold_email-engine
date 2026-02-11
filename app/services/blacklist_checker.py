"""DNS-based blacklist checker for 9 major RBLs."""

import asyncio
from datetime import datetime

import dns.resolver
import structlog
from sqlalchemy.orm import Session

from app.enums import AlertCategory, AlertSeverity, IPStatus
from app.models import IP, BlacklistEvent
from app.services.telegram_alerter import alerter

logger = structlog.get_logger(__name__)

# 9 major DNS blacklists
BLACKLISTS = [
    "zen.spamhaus.org",
    "bl.spamcop.net",
    "b.barracudacentral.org",
    "dnsbl.sorbs.net",
    "spam.dnsbl.sorbs.net",
    "ips.backscatterer.org",
    "psbl.surriel.com",
    "dyna.spamrats.com",
    "all.s5h.net",
]


def _reverse_ip(ip: str) -> str:
    """Reverse IP octets for DNSBL query (e.g. 1.2.3.4 → 4.3.2.1)."""
    return ".".join(reversed(ip.split(".")))


class BlacklistChecker:
    """Check IPs against DNS blacklists and handle listings."""

    def __init__(self, db: Session):
        self.db = db
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5
        self.resolver.lifetime = 5

    def check_single(self, ip_address: str, blacklist: str) -> bool:
        """Check if an IP is listed on a single blacklist."""
        query = f"{_reverse_ip(ip_address)}.{blacklist}"
        try:
            self.resolver.resolve(query, "A")
            return True  # listed
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return False
        except dns.exception.Timeout:
            logger.warning("blacklist_check_timeout", ip=ip_address, bl=blacklist)
            return False

    def check_ip(self, ip_address: str) -> list[str]:
        """Check an IP against all 9 blacklists. Returns list of listings."""
        listed_on = []
        for bl in BLACKLISTS:
            if self.check_single(ip_address, bl):
                listed_on.append(bl)
                logger.warning("ip_blacklisted", ip=ip_address, blacklist=bl)
        return listed_on

    async def check_all_ips(self) -> dict[str, list[str]]:
        """Check all active/warming IPs against blacklists."""
        ips = (
            self.db.query(IP)
            .filter(IP.status.in_([IPStatus.ACTIVE.value, IPStatus.WARMING.value]))
            .all()
        )

        results: dict[str, list[str]] = {}
        for ip in ips:
            listed_on = self.check_ip(ip.address)
            if listed_on:
                results[ip.address] = listed_on
                self._record_listing(ip, listed_on)

        # Check if previously blacklisted IPs have been delisted
        await self._check_delistings()

        return results

    def _record_listing(self, ip: IP, blacklist_names: list[str]) -> None:
        """Record new blacklist events in DB."""
        for bl_name in blacklist_names:
            existing = (
                self.db.query(BlacklistEvent)
                .filter(
                    BlacklistEvent.ip_id == ip.id,
                    BlacklistEvent.blacklist_name == bl_name,
                    BlacklistEvent.delisted_at.is_(None),
                )
                .first()
            )
            if not existing:
                self.db.add(
                    BlacklistEvent(
                        ip_id=ip.id,
                        blacklist_name=bl_name,
                        listed_at=datetime.utcnow(),
                    )
                )
        self.db.commit()

    async def _check_delistings(self) -> None:
        """Check if blacklisted IPs have been delisted."""
        events = (
            self.db.query(BlacklistEvent)
            .filter(BlacklistEvent.delisted_at.is_(None))
            .all()
        )
        for event in events:
            ip = self.db.query(IP).filter(IP.id == event.ip_id).first()
            if not ip:
                continue
            if not self.check_single(ip.address, event.blacklist_name):
                event.delisted_at = datetime.utcnow()
                event.auto_recovered = True
                logger.info(
                    "ip_delisted",
                    ip=ip.address,
                    blacklist=event.blacklist_name,
                )
                await alerter.send(
                    f"IP *{ip.address}* delisted from {event.blacklist_name}",
                    severity=AlertSeverity.INFO,
                    category=AlertCategory.BLACKLIST,
                    db=self.db,
                )
        self.db.commit()
