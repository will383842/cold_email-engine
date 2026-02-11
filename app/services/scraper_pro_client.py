"""Forward bounce data to scraper-pro with HMAC-SHA256 signing."""

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


class ScraperProClient:
    """Send bounce feedback to scraper-pro API."""

    def __init__(self):
        self.url = settings.SCRAPER_PRO_BOUNCE_URL
        self.secret = settings.SCRAPER_PRO_HMAC_SECRET

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.secret)

    async def forward_bounce(
        self,
        email: str,
        bounce_type: str,
        reason: str = "",
        ip_address: str = "",
    ) -> bool:
        """Forward a bounce event to scraper-pro bounce-feedback endpoint."""
        if not self.enabled:
            logger.debug("scraper_pro_not_configured")
            return False

        payload = {
            "event_type": "bounce",
            "platform": "email-engine",
            "timestamp": int(time.time()),
            "email": email,
            "bounce_type": bounce_type,
            "reason": reason,
            "source_ip": ip_address,
        }

        body = json.dumps(payload, sort_keys=True)
        timestamp = str(int(time.time()))
        signature = _sign_payload(self.secret, timestamp, body)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Timestamp": timestamp,
                        "X-Signature": signature,
                    },
                )
                if resp.status_code == 200:
                    logger.info("bounce_forwarded", email=email, type=bounce_type)
                    return True
                logger.warning(
                    "bounce_forward_failed",
                    email=email,
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return False
        except Exception as exc:
            logger.error("bounce_forward_error", email=email, error=str(exc))
            return False


scraper_pro_client = ScraperProClient()
