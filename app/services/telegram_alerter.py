"""Telegram Bot API alerting service."""

from datetime import datetime

import httpx
import structlog

from app.config import settings
from app.enums import AlertCategory, AlertSeverity
from app.models import AlertLog

logger = structlog.get_logger(__name__)

SEVERITY_EMOJI = {
    AlertSeverity.INFO: "ℹ️",
    AlertSeverity.WARNING: "⚠️",
    AlertSeverity.CRITICAL: "🚨",
}


class TelegramAlerter:
    """Send alerts via Telegram Bot API and log them."""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        category: AlertCategory = AlertCategory.HEALTH,
        db=None,
    ) -> bool:
        """Send a Telegram message and log to DB."""
        emoji = SEVERITY_EMOJI.get(severity, "")
        text = f"{emoji} *Email Engine — {severity.value.upper()}*\n\n{message}"

        sent = False
        if self.enabled:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{self.api_url}/sendMessage",
                        json={
                            "chat_id": self.chat_id,
                            "text": text,
                            "parse_mode": "Markdown",
                        },
                    )
                    sent = resp.status_code == 200
                    if not sent:
                        logger.warning("telegram_send_failed", status=resp.status_code)
            except Exception as exc:
                logger.error("telegram_send_error", error=str(exc))
        else:
            logger.debug("telegram_disabled")

        if db:
            db.add(
                AlertLog(
                    timestamp=datetime.utcnow(),
                    severity=severity.value,
                    category=category.value,
                    message=message,
                    telegram_sent=sent,
                )
            )
            db.commit()

        return sent


alerter = TelegramAlerter()
