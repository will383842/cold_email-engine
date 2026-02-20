"""PowerMTA webhook receivers → forward to scraper-pro.

Sécurité :
  - Validation signature HMAC-SHA256 (si WEBHOOK_SECRET configuré)
  - Whitelist IPs PowerMTA (si PMTA_ALLOWED_IPS configuré)
  - Rate limiting : 200 req/min par IP
"""

import hashlib
import hmac
import secrets as secrets_module

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import PMTABouncePayload, PMTADeliveryPayload
from app.config import settings
from app.database import get_db
from app.services.scraper_pro_client import scraper_pro_client

logger = structlog.get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# =============================================================================
# Helpers sécurité webhook
# =============================================================================

def _validate_hmac(body: bytes, signature: str | None) -> bool:
    """
    Valide la signature HMAC-SHA256 du payload.

    PowerMTA / MailWizz envoient le header :
        X-Webhook-Signature: sha256=<hex_digest>

    Si WEBHOOK_SECRET n'est pas configuré → passe (mode dev).
    Si configuré → valide ou rejette (403).
    """
    if not settings.WEBHOOK_SECRET:
        return True  # Mode dev / non sécurisé
    if not signature:
        return False
    # Supporte les formats "sha256=abc..." et "abc..." directement
    sig_value = signature.removeprefix("sha256=")
    expected = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return secrets_module.compare_digest(expected, sig_value)


def _validate_client_ip(request: Request) -> None:
    """
    Vérifie que l'IP source est dans la whitelist PMTA_ALLOWED_IPS.

    Si la variable est vide → aucune restriction (mode dev).
    Format .env : PMTA_ALLOWED_IPS=1.2.3.4,5.6.7.8
    """
    if not settings.PMTA_ALLOWED_IPS:
        return  # Pas de restriction
    allowed = {ip.strip() for ip in settings.PMTA_ALLOWED_IPS.split(",") if ip.strip()}
    client_ip = request.client.host if request.client else ""
    if client_ip not in allowed:
        logger.warning("webhook_ip_rejected", client_ip=client_ip, allowed=list(allowed))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP non autorisée pour ce webhook",
        )


async def _validate_webhook_request(request: Request) -> bytes:
    """
    Lit le body + valide IP + valide HMAC.
    Retourne le body bytes pour utilisation downstream.
    """
    _validate_client_ip(request)
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    if not _validate_hmac(body, signature):
        logger.warning(
            "webhook_invalid_signature",
            path=request.url.path,
            has_sig=bool(signature),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature webhook invalide",
        )
    return body


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/pmta-bounce")
@limiter.limit("200/minute")
async def pmta_bounce(
    request: Request,
    payload: PMTABouncePayload,
    db: Session = Depends(get_db),
):
    """Receive bounce from PowerMTA accounting pipe and forward to scraper-pro."""
    await _validate_webhook_request(request)

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
async def pmta_delivery(
    request: Request,
    payload: PMTADeliveryPayload,
    db: Session = Depends(get_db),
):
    """Receive delivery stats from PowerMTA and forward to scraper-pro for bounce rate calculation."""
    await _validate_webhook_request(request)

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
