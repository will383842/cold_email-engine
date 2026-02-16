"""Quota Checker - Enforce warmup daily quotas."""

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import IP, WarmupPlan
from src.infrastructure.cache import get_cache


class QuotaChecker:
    """
    Check and enforce daily sending quotas for IPs in warmup.

    This is CRITICAL for warmup success - prevents burning IPs by sending too much.
    """

    def __init__(self, db: Session):
        self.db = db
        self.cache = get_cache()

    def check_quota(
        self,
        ip_id: int,
        emails_to_send: int
    ) -> Tuple[bool, str, dict]:
        """
        Check if IP can send X emails without exceeding daily quota.

        Args:
            ip_id: IP ID
            emails_to_send: Number of emails to send

        Returns:
            Tuple of (allowed, message, quota_info)
            - allowed: True if sending is allowed
            - message: Human-readable message
            - quota_info: Dict with quota details

        Example:
            allowed, msg, info = checker.check_quota(ip_id=1, emails_to_send=100)
            if not allowed:
                print(f"Cannot send: {msg}")
            else:
                print(f"OK to send. Remaining: {info['remaining']}")
        """
        # Get IP and warmup plan
        ip = self.db.query(IP).filter_by(id=ip_id).first()

        if not ip:
            return False, f"IP {ip_id} not found", {}

        # If IP is ACTIVE (warmup completed), no quota limits
        if ip.status == "active":
            return True, "IP is active - no quota limits", {
                "ip_address": ip.address,
                "status": "active",
                "daily_quota": "unlimited",
                "sent_today": 0,
                "remaining": "unlimited"
            }

        # If IP is not in warmup, allow
        if ip.status != "warming":
            return True, f"IP status is {ip.status} - no quota limits", {
                "ip_address": ip.address,
                "status": ip.status,
            }

        # Check warmup plan exists
        if not ip.warmup_plan:
            return False, f"IP {ip.address} is in warmup but has no warmup plan", {}

        plan = ip.warmup_plan

        # Check if plan is paused
        if plan.paused:
            pause_msg = ""
            if plan.pause_until:
                pause_msg = f" until {plan.pause_until.strftime('%Y-%m-%d %H:%M UTC')}"
            return False, f"Warmup paused{pause_msg} - check bounce/spam rates", {
                "ip_address": ip.address,
                "status": "paused",
                "paused": True,
                "pause_until": plan.pause_until.isoformat() if plan.pause_until else None,
                "bounce_rate_7d": plan.bounce_rate_7d,
                "spam_rate_7d": plan.spam_rate_7d,
            }

        # Get daily quota
        daily_quota = plan.current_daily_quota

        # Count emails sent today from Redis
        today = datetime.utcnow().date().isoformat()
        key = f"warmup:ip:{ip_id}:date:{today}:sent"
        sent_today = int(self.cache.get(key) or 0)

        # Calculate remaining
        remaining = daily_quota - sent_today

        # Check if adding new emails would exceed quota
        if sent_today + emails_to_send > daily_quota:
            return False, (
                f"Quota exceeded: trying to send {emails_to_send} but only "
                f"{remaining} remaining today (limit: {daily_quota}/day)"
            ), {
                "ip_address": ip.address,
                "status": "warming",
                "phase": plan.phase,
                "daily_quota": daily_quota,
                "sent_today": sent_today,
                "remaining": remaining,
                "requested": emails_to_send,
                "would_exceed": True,
            }

        # All good - can send
        return True, (
            f"OK to send {emails_to_send} emails. "
            f"Will have {remaining - emails_to_send} remaining today."
        ), {
            "ip_address": ip.address,
            "status": "warming",
            "phase": plan.phase,
            "daily_quota": daily_quota,
            "sent_today": sent_today,
            "remaining": remaining,
            "requested": emails_to_send,
            "after_send": remaining - emails_to_send,
        }

    def get_quota_info(self, ip_id: int) -> Optional[dict]:
        """
        Get current quota information for an IP.

        Args:
            ip_id: IP ID

        Returns:
            Dict with quota info or None if IP not found
        """
        allowed, message, info = self.check_quota(ip_id, 0)
        return info if info else None

    def get_available_ips_for_sending(
        self,
        tenant_id: int,
        emails_to_send: int
    ) -> list[dict]:
        """
        Get all IPs for a tenant that can send X emails.

        Args:
            tenant_id: Tenant ID
            emails_to_send: Number of emails to send

        Returns:
            List of IP dicts with quota info, sorted by most remaining quota first

        Example:
            ips = checker.get_available_ips_for_sending(tenant_id=1, emails_to_send=100)
            for ip in ips:
                print(f"{ip['address']}: {ip['remaining']} remaining")
        """
        # Get all IPs for tenant
        ips = self.db.query(IP).filter_by(tenant_id=tenant_id).all()

        available = []

        for ip in ips:
            allowed, message, info = self.check_quota(ip.id, emails_to_send)

            if allowed:
                available.append({
                    "ip_id": ip.id,
                    "address": ip.address,
                    "status": ip.status,
                    "allowed": True,
                    "message": message,
                    **info
                })

        # Sort by remaining quota (most remaining first)
        # Active IPs (unlimited) come first
        def sort_key(ip_dict):
            if ip_dict.get("status") == "active":
                return (0, float('inf'))  # Active first, unlimited
            remaining = ip_dict.get("remaining", 0)
            if isinstance(remaining, str):  # "unlimited"
                return (0, float('inf'))
            return (1, -remaining)  # Warming second, most remaining first

        available.sort(key=sort_key)

        return available

    def reserve_quota(self, ip_id: int, email_count: int) -> bool:
        """
        Reserve quota for sending (increment counter).

        This should be called BEFORE sending to reserve the quota.
        If sending fails, quota is already counted (safe side).

        Args:
            ip_id: IP ID
            email_count: Number of emails being sent

        Returns:
            True if reserved successfully
        """
        # Check quota first
        allowed, message, info = self.check_quota(ip_id, email_count)

        if not allowed:
            return False

        # Increment Redis counter
        today = datetime.utcnow().date().isoformat()
        key = f"warmup:ip:{ip_id}:date:{today}:sent"
        self.cache.increment(key, email_count)

        return True
