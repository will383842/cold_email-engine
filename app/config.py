"""Application configuration from environment variables."""

import sys

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All settings loaded from .env file."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    # --- API ---
    API_KEY: str = "changeme"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "changeme-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./email_engine.db"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- PowerMTA ---
    PMTA_CONFIG_PATH: str = "/etc/pmta/config"
    PMTA_BIN_PATH: str = "/usr/sbin/pmta"

    # --- MailWizz API ---
    MAILWIZZ_API_URL: str = ""
    MAILWIZZ_API_PUBLIC_KEY: str = ""
    MAILWIZZ_API_PRIVATE_KEY: str = ""

    # --- MailWizz MySQL (fallback) ---
    MAILWIZZ_DB_HOST: str = "127.0.0.1"
    MAILWIZZ_DB_PORT: int = 3306
    MAILWIZZ_DB_USER: str = "mailwizz"
    MAILWIZZ_DB_PASSWORD: str = ""
    MAILWIZZ_DB_NAME: str = "mailwizz"

    # --- Telegram Alerts ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # --- Scraper-Pro Integration ---
    SCRAPER_PRO_BOUNCE_URL: str = ""
    SCRAPER_PRO_DELIVERY_URL: str = ""
    SCRAPER_PRO_HMAC_SECRET: str = ""

    # --- Blacklist ---
    BLACKLIST_CHECK_INTERVAL_HOURS: int = 4

    # --- Warmup ---
    WARMUP_WEEK1_QUOTA: int = 50
    WARMUP_WEEK2_QUOTA: int = 200
    WARMUP_WEEK3_QUOTA: int = 500
    WARMUP_WEEK4_QUOTA: int = 1500
    WARMUP_WEEK5_QUOTA: int = 5000
    WARMUP_WEEK6_QUOTA: int = 10000
    WARMUP_MAX_BOUNCE_RATE: float = 5.0
    WARMUP_MAX_SPAM_RATE: float = 0.1

    # --- IP Rotation ---
    IP_QUARANTINE_DAYS: int = 30
    IP_REST_DAYS: int = 7

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """Warn on insecure defaults — block only API_KEY=changeme."""
        if self.API_KEY in ("changeme", "changeme-generate-a-strong-key"):
            print(
                "FATAL: API_KEY is set to the default placeholder. "
                "Set a strong API_KEY in your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)
        if self.JWT_SECRET_KEY in ("changeme-jwt-secret", "changeme"):
            print(
                "FATAL: JWT_SECRET_KEY is set to the default placeholder. "
                "Set a strong JWT_SECRET_KEY in your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not self.TELEGRAM_BOT_TOKEN:
            print(
                "WARNING: TELEGRAM_BOT_TOKEN not set — Telegram alerts disabled.",
                file=sys.stderr,
            )
        if not self.SCRAPER_PRO_HMAC_SECRET:
            print(
                "WARNING: SCRAPER_PRO_HMAC_SECRET not set — bounce forwarding disabled.",
                file=sys.stderr,
            )
        if not self.MAILWIZZ_API_URL and not self.MAILWIZZ_DB_PASSWORD:
            print(
                "WARNING: Neither MailWizz API nor MySQL configured — warmup quota updates disabled.",
                file=sys.stderr,
            )
        return self


settings = Settings()
