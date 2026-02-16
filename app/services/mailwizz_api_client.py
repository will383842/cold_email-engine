"""MailWizz API REST client (replaces MySQL direct access)."""

import hashlib
import hmac
from typing import Any, Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class MailWizzAPIClient:
    """
    MailWizz API REST client.

    Uses MailWizz API v1 instead of direct MySQL access.
    Falls back to MySQL if API not configured (backward compatibility).
    """

    def __init__(self):
        self.base_url = settings.MAILWIZZ_API_URL.rstrip("/") if settings.MAILWIZZ_API_URL else None
        self.public_key = settings.MAILWIZZ_API_PUBLIC_KEY
        self.private_key = settings.MAILWIZZ_API_PRIVATE_KEY
        self.timeout = 10.0

    def _is_configured(self) -> bool:
        """Check if API is properly configured."""
        return bool(self.base_url and self.public_key and self.private_key)

    def _build_headers(self) -> dict[str, str]:
        """Build authentication headers for MailWizz API."""
        # MailWizz uses HMAC-SHA1 signature
        # Format: X-MW-PUBLIC-KEY + X-MW-SIGNATURE (HMAC of timestamp + public_key)
        import time

        timestamp = str(int(time.time()))
        message = f"{timestamp}{self.public_key}"
        signature = hmac.new(
            self.private_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()

        return {
            "X-MW-PUBLIC-KEY": self.public_key,
            "X-MW-TIMESTAMP": timestamp,
            "X-MW-SIGNATURE": signature,
            "Content-Type": "application/json",
        }

    async def get_delivery_server(self, server_id: int) -> Optional[dict[str, Any]]:
        """
        Get delivery server by ID.

        Args:
            server_id: MailWizz delivery server ID

        Returns:
            Server dict with keys: server_id, name, hourly_quota, daily_quota, monthly_quota
            None if not found or API not configured
        """
        if not self._is_configured():
            logger.warning("mailwizz_api_not_configured", fallback="mysql")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/delivery-servers/{server_id}",
                    headers=self._build_headers(),
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        record = data.get("data", {}).get("record", {})
                        return {
                            "server_id": server_id,
                            "name": record.get("name"),
                            "hourly_quota": int(record.get("hourly_quota", 0)),
                            "daily_quota": int(record.get("daily_quota", 0)),
                            "monthly_quota": int(record.get("monthly_quota", 0)),
                        }
                logger.warning(
                    "mailwizz_api_get_server_failed",
                    server_id=server_id,
                    status=response.status_code,
                )
                return None
        except Exception as exc:
            logger.error("mailwizz_api_get_server_error", server_id=server_id, error=str(exc))
            return None

    async def update_delivery_server_quota(
        self,
        server_id: int,
        hourly_quota: Optional[int] = None,
        daily_quota: Optional[int] = None,
        monthly_quota: Optional[int] = None,
    ) -> bool:
        """
        Update delivery server quotas.

        Args:
            server_id: MailWizz delivery server ID
            hourly_quota: New hourly quota (optional)
            daily_quota: New daily quota (optional)
            monthly_quota: New monthly quota (optional)

        Returns:
            True if update successful, False otherwise
        """
        if not self._is_configured():
            logger.warning("mailwizz_api_not_configured", fallback="mysql")
            return False

        # Build update payload
        payload: dict[str, Any] = {}
        if hourly_quota is not None:
            payload["hourly_quota"] = hourly_quota
        if daily_quota is not None:
            payload["daily_quota"] = daily_quota
        if monthly_quota is not None:
            payload["monthly_quota"] = monthly_quota

        if not payload:
            logger.warning("mailwizz_api_update_no_payload", server_id=server_id)
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/delivery-servers/{server_id}",
                    headers=self._build_headers(),
                    json=payload,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        logger.info(
                            "mailwizz_api_quota_updated",
                            server_id=server_id,
                            hourly=hourly_quota,
                            daily=daily_quota,
                        )
                        return True
                logger.warning(
                    "mailwizz_api_update_failed",
                    server_id=server_id,
                    status=response.status_code,
                )
                return False
        except Exception as exc:
            logger.error("mailwizz_api_update_error", server_id=server_id, error=str(exc))
            return False
