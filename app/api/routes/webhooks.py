"""PowerMTA bounce webhook receiver → forward to scraper-pro."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import PMTABouncePayload
from app.database import get_db
from app.services.scraper_pro_client import scraper_pro_client

router = APIRouter(prefix="/webhooks", tags=["Webhooks"], dependencies=[Depends(verify_api_key)])


@router.post("/pmta-bounce")
async def pmta_bounce(payload: PMTABouncePayload, db: Session = Depends(get_db)):
    """Receive bounce from PowerMTA accounting pipe and forward to scraper-pro."""
    forwarded = await scraper_pro_client.forward_bounce(
        email=payload.email,
        bounce_type=payload.bounce_type.value,
        reason=payload.reason,
        ip_address=payload.source_ip,
    )
    return {
        "received": True,
        "forwarded_to_scraper_pro": forwarded,
        "email": payload.email,
        "bounce_type": payload.bounce_type.value,
    }
