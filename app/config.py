"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All settings loaded from .env file."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # --- API ---
    API_KEY: str = "changeme"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./email_engine.db"

    # --- PowerMTA ---
    PMTA_CONFIG_PATH: str = "/etc/pmta/config"
    PMTA_BIN_PATH: str = "/usr/sbin/pmta"

    # --- MailWizz MySQL ---
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


settings = Settings()
