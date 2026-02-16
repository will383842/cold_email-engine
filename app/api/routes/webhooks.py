"""PowerMTA webhook receivers → forward to scraper-pro."""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import PMTABouncePayload, PMTADeliveryPayload
from app.database import get_db
from app.services.scraper_pro_client import scraper_pro_client

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"], dependencies=[Depends(verify_api_key)])


@router.post("/pmta-bounce")
@limiter.limit("200/minute")
async def pmta_bounce(request: Request, payload: PMTABouncePayload, db: Session = Depends(get_db)):
    """Receive bounce from PowerMTA accounting pipe and forward to scraper-pro."""
    from app.api.routes.metrics import bounces_forwarded, bounces_received

    bounces_received.inc()

    forwarded = await scraper_pro_client.forward_bounce(
        email=payload.email,
        bounce_type=payload.bounce_type.value,
        reason=payload.reason,
        ip_address=payload.source_ip,
    )
    if forwarded:
        bounces_forwarded.inc()

    return {
        "received": True,
        "forwarded_to_scraper_pro": forwarded,
        "email": payload.email,
        "bounce_type": payload.bounce_type.value,
    }


@router.post("/pmta-delivery")
@limiter.limit("200/minute")
async def pmta_delivery(request: Request, payload: PMTADeliveryPayload, db: Session = Depends(get_db)):
    """Receive delivery stats from PowerMTA and forward to scraper-pro for bounce rate calculation."""
    from app.api.routes.metrics import deliveries_reported

    deliveries_reported.inc(payload.count)

    forwarded = await scraper_pro_client.forward_delivery_feedback(
        domain=payload.domain,
        count=payload.count,
    )

    return {
        "received": True,
        "forwarded_to_scraper_pro": forwarded,
        "domain": payload.domain,
        "count": payload.count,
    }
