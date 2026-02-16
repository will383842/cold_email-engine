"""Forward bounce/delivery data to scraper-pro with HMAC-SHA256 signing."""

import hashlib
import hmac
import json
import time

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


def _sign_payload(secret: str, timestamp: str, body: str) -> str:
    """Generate HMAC-SHA256 signature (same scheme as scraper-pro)."""
    message = f"{timestamp}.{body}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _build_headers(secret: str, body: str) -> dict:
    """Build authenticated headers for scraper-pro API."""
    timestamp = str(int(time.time()))
    signature = _sign_payload(secret, timestamp, body)
    return {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    }


class ScraperProClient:
    """Send bounce and delivery feedback to scraper-pro API."""

    def __init__(self):
        self.bounce_url = settings.SCRAPER_PRO_BOUNCE_URL
        self.delivery_url = settings.SCRAPER_PRO_DELIVERY_URL
        self.secret = settings.SCRAPER_PRO_HMAC_SECRET

    @property
    def bounce_enabled(self) -> bool:
        return bool(self.bounce_url and self.secret)

    @property
    def delivery_enabled(self) -> bool:
        return bool(self.delivery_url and self.secret)

    async def _post(self, url: str, payload: dict, log_action: str) -> bool:
        """Send HMAC-signed POST to scraper-pro. Enqueues for retry on failure."""
        body = json.dumps(payload, sort_keys=True)
        headers = _build_headers(self.secret, body)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, content=body, headers=headers)
                if resp.status_code == 200:
                    logger.info(f"{log_action}_ok", **payload)
                    return True
                logger.warning(
                    f"{log_action}_failed",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
        except Exception as exc:
            logger.error(f"{log_action}_error", error=str(exc))

        # Enqueue for retry
        from app.services.retry_queue import enqueue
        enqueue(url, payload, log_action)
        return False

    async def forward_bounce(
        self,
        email: str,
        bounce_type: str,
        reason: str = "",
        ip_address: str = "",
    ) -> bool:
        """Forward a bounce event to scraper-pro bounce-feedback endpoint."""
        if not self.bounce_enabled:
            logger.debug("scraper_pro_bounce_not_configured")
            return False
        payload = {"email": email, "bounce_type": bounce_type}
        return await self._post(self.bounce_url, payload, "bounce_forwarded")

    async def forward_delivery_feedback(
        self,
        domain: str,
        count: int = 1,
    ) -> bool:
        """Forward delivery stats to scraper-pro for accurate bounce rate calculation."""
        if not self.delivery_enabled:
            logger.debug("scraper_pro_delivery_not_configured")
            return False
        payload = {"domain": domain, "count": count}
        return await self._post(self.delivery_url, payload, "delivery_forwarded")


scraper_pro_client = ScraperProClient()
