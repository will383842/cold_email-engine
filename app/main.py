"""FastAPI application with APScheduler lifespan."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import blacklists, domains, health, ips, metrics, warmup, webhooks
from app.database import engine
from app.logging_config import setup_logging
from app.models import Base
from app.scheduler.setup import create_scheduler

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables + start scheduler. Shutdown: stop scheduler."""
    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Email Engine",
    description="Professional email infrastructure manager — PowerMTA + MailWizz",
    version="1.0.0",
    lifespan=lifespan,
)

# Public endpoints (no API key)
app.include_router(health.router)
app.include_router(metrics.router)

# Protected endpoints
API_PREFIX = "/api/v1"
app.include_router(ips.router, prefix=API_PREFIX)
app.include_router(domains.router, prefix=API_PREFIX)
app.include_router(warmup.router, prefix=API_PREFIX)
app.include_router(blacklists.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
