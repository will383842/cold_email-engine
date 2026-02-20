"""FastAPI application with APScheduler lifespan and rate limiting."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import (
    admin,
    audit,
    auth,
    blacklists,
    domains,
    health,
    ips,
    metrics,
    validation,
    warmup,
    webhooks,
)
from app.config import settings
from app.database import engine
from app.logging_config import setup_logging
from app.models import Base
from app.scheduler.setup import create_scheduler

# Import API v2 router (Clean Architecture) — optionnel, pas encore déployé
try:
    from src.presentation.api.v2 import router as api_v2_router  # type: ignore
    _v2_available = True
except ImportError:
    api_v2_router = None
    _v2_available = False

setup_logging()

# Rate limiting with Redis backend (production) or in-memory (dev)
try:
    import redis

    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["60/minute"],
        storage_uri=settings.REDIS_URL,
    )
except Exception:
    # Fallback to in-memory if Redis unavailable (development only)
    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables + start scheduler. Shutdown: stop scheduler."""
    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Email Engine API",
    description="""
    ## Enterprise Cold Email Infrastructure Manager

    Multi-tenant email marketing platform with PowerMTA + MailWizz integration.

    ### Features
    - **Multi-tenant**: Complete isolation for SOS-Expat and Ulixai
    - **Multi-language**: 9 languages (FR, EN, ES, DE, PT, RU, ZH, HI, AR)
    - **Clean Architecture**: Domain-Driven Design with hexagonal architecture
    - **IP Warmup**: Automated 6-week warmup schedule
    - **Tag-based Segmentation**: Advanced contact filtering
    - **Background Jobs**: Celery for async processing
    - **Real-time Webhooks**: MailWizz & PowerMTA event handling

    ### API Versions
    - **v1**: Legacy endpoints (authentication, IP management, warmup)
    - **v2**: New Clean Architecture endpoints (contacts, campaigns, templates, stats)
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Email Engine Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "Proprietary",
    },
)

app.state.limiter = limiter

# =============================================================================
# CORS Configuration
# =============================================================================
# Get CORS origins from environment (comma-separated)
cors_origins = []
if hasattr(settings, 'CORS_ORIGINS'):
    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(',')]
else:
    # Default CORS origins for development
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


# Public endpoints (no auth required)
app.include_router(health.router)
app.include_router(metrics.router)

# Authentication endpoints (public)
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)

# Protected endpoints (JWT or API key required)
app.include_router(ips.router, prefix=API_PREFIX)
app.include_router(domains.router, prefix=API_PREFIX)
app.include_router(warmup.router, prefix=API_PREFIX)
app.include_router(blacklists.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(validation.router, prefix=API_PREFIX)

# Admin endpoints (API key required)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)

# =============================================================================
# API v2 - Clean Architecture Endpoints (optionnel — déployé ultérieurement)
# =============================================================================
if _v2_available and api_v2_router is not None:
    app.include_router(api_v2_router)
