"""API v2 - Enterprise Clean Architecture endpoints."""

from fastapi import APIRouter

from .contacts import router as contacts_router
from .templates import router as templates_router
from .campaigns import router as campaigns_router
from .tags import router as tags_router
from .data_sources import router as data_sources_router
from .stats import router as stats_router
from .webhooks import router as webhooks_router
from .quotas import router as quotas_router
from .powermta import router as powermta_router

# Main API v2 router
router = APIRouter(prefix="/api/v2", tags=["v2"])

# Register sub-routers
router.include_router(contacts_router, prefix="/contacts", tags=["contacts"])
router.include_router(templates_router, prefix="/templates", tags=["templates"])
router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
router.include_router(tags_router, prefix="/tags", tags=["tags"])
router.include_router(data_sources_router, prefix="/data-sources", tags=["data-sources"])
router.include_router(stats_router, prefix="/stats", tags=["stats"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
router.include_router(quotas_router, prefix="/quotas", tags=["quotas"])
router.include_router(powermta_router, prefix="/powermta", tags=["powermta"])
