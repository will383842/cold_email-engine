"""Webhooks API v2 - Handle external webhooks (MailWizz, PowerMTA, etc.)."""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ContactEvent, Contact
from app.enums import EventType
from .auth import no_auth  # Simple auth for internal tool

router = APIRouter()


# =============================================================================
# Request Schemas
# =============================================================================


class MailWizzWebhookRequest(BaseModel):
    """MailWizz webhook payload."""

    event: str  # delivered, opened, clicked, bounced, complained, unsubscribed
    subscriber_uid: str
    campaign_uid: str
    email: str
    timestamp: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None  # For click events
    bounce_type: Optional[str] = None  # For bounce events
    bounce_message: Optional[str] = None


class PowerMTAWebhookRequest(BaseModel):
    """PowerMTA webhook/accounting payload."""

    event: str  # delivered, bounced, deferred
    recipient: str
    vmta: str
    domain: str
    message_id: str
    sending_ip: Optional[str] = None  # IP address used for sending
    timestamp: Optional[str] = None
    smtp_response: Optional[str] = None
    bounce_category: Optional[str] = None


class GenericEventRequest(BaseModel):
    """Generic event webhook (for custom integrations)."""

    email: str
    event_type: str  # sent, delivered, opened, clicked, bounced, complained, unsubscribed
    campaign_id: Optional[int] = None
    metadata: Optional[dict] = None
    timestamp: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _map_mailwizz_event(event: str) -> EventType:
    """Map MailWizz event names to EventType enum."""
    mapping = {
        "delivered": EventType.DELIVERED,
        "opened": EventType.OPENED,
        "clicked": EventType.CLICKED,
        "bounced": EventType.BOUNCED,
        "complained": EventType.COMPLAINED,
        "unsubscribed": EventType.UNSUBSCRIBED,
    }
    return mapping.get(event.lower())


def _map_powermta_event(event: str) -> EventType:
    """Map PowerMTA event names to EventType enum."""
    mapping = {
        "delivered": EventType.DELIVERED,
        "bounced": EventType.BOUNCED,
        "deferred": EventType.BOUNCED,  # Treat deferred as soft bounce
    }
    return mapping.get(event.lower())


def _create_contact_event(
    db: Session,
    contact_id: int,
    event_type: EventType,
    campaign_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> ContactEvent:
    """Create a contact event."""
    # Récupérer le contact pour obtenir le tenant_id
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise ValueError(f"Contact {contact_id} not found")

    event = ContactEvent(
        tenant_id=contact.tenant_id,
        contact_id=contact_id,
        campaign_id=campaign_id,
        event_type=event_type,
        metadata=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _track_warmup_event(
    db: Session,
    sending_ip: Optional[str],
    event_type: EventType,
) -> None:
    """
    Track warmup stats for IPs in warming status.

    Increments Redis counters for daily warmup tracking.
    These counters are consolidated to PostgreSQL daily by consolidate_warmup_stats_task.

    Args:
        db: Database session
        sending_ip: IP address that sent the email
        event_type: Type of event (sent, delivered, bounced, etc.)

    Redis Keys:
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:sent
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:delivered
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:bounced
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:complaints
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:opens
        warmup:ip:{ip_id}:date:{YYYY-MM-DD}:clicks
    """
    if not sending_ip:
        return

    from app.models import IP
    from src.infrastructure.cache import get_cache

    # Find IP in warming status
    ip = db.query(IP).filter(
        IP.address == sending_ip,
        IP.status == "warming"
    ).first()

    if not ip or not ip.warmup_plan:
        return  # Not in warmup, nothing to track

    # Get cache
    cache = get_cache()

    # Build Redis key for today
    today = datetime.utcnow().date().isoformat()
    key_prefix = f"warmup:ip:{ip.id}:date:{today}"

    # Increment appropriate counter
    if event_type == EventType.SENT:
        cache.increment(f"{key_prefix}:sent")
    elif event_type == EventType.DELIVERED:
        cache.increment(f"{key_prefix}:delivered")
    elif event_type == EventType.BOUNCED:
        cache.increment(f"{key_prefix}:bounced")
    elif event_type == EventType.COMPLAINED:
        cache.increment(f"{key_prefix}:complaints")
    elif event_type == EventType.OPENED:
        cache.increment(f"{key_prefix}:opens")
    elif event_type == EventType.CLICKED:
        cache.increment(f"{key_prefix}:clicks")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/mailwizz", dependencies=[Depends(no_auth)])
def mailwizz_webhook(
    request: MailWizzWebhookRequest,
    db: Session = Depends(get_db),
):
    """
    Handle MailWizz delivery webhooks.

    MailWizz can send webhooks for: delivered, opened, clicked, bounced, complained, unsubscribed.
    """
    try:
        # Map event type
        event_type = _map_mailwizz_event(request.event)
        if not event_type:
            return {"success": False, "error": f"Unknown event type: {request.event}"}

        # Find contact by email
        contact = db.query(Contact).filter(Contact.email == request.email).first()

        if not contact:
            return {"success": False, "error": f"Contact not found: {request.email}"}

        # Build metadata
        metadata = {
            "subscriber_uid": request.subscriber_uid,
            "campaign_uid": request.campaign_uid,
            "ip_address": request.ip_address,
            "user_agent": request.user_agent,
        }

        if request.url:
            metadata["url"] = request.url
        if request.bounce_type:
            metadata["bounce_type"] = request.bounce_type
        if request.bounce_message:
            metadata["bounce_message"] = request.bounce_message

        # Create event
        _create_contact_event(
            db=db,
            contact_id=contact.id,
            event_type=event_type,
            metadata=metadata,
        )

        # Track warmup stats if IP is in warming status
        _track_warmup_event(
            db=db,
            sending_ip=request.ip_address,
            event_type=event_type,
        )

        # Update contact status based on event
        from app.enums import ContactStatus

        if event_type == EventType.BOUNCED:
            contact.status = ContactStatus.BOUNCED
            db.commit()
        elif event_type == EventType.COMPLAINED:
            contact.status = ContactStatus.COMPLAINED
            db.commit()
        elif event_type == EventType.UNSUBSCRIBED:
            contact.status = ContactStatus.UNSUBSCRIBED
            db.commit()

        return {
            "success": True,
            "message": f"Event {request.event} recorded for {request.email}",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


@router.post("/powermta", dependencies=[Depends(no_auth)])
def powermta_webhook(
    request: PowerMTAWebhookRequest,
    db: Session = Depends(get_db),
):
    """
    Handle PowerMTA accounting webhooks.

    PowerMTA can send: delivered, bounced, deferred.
    """
    try:
        # Map event type
        event_type = _map_powermta_event(request.event)
        if not event_type:
            return {"success": False, "error": f"Unknown event type: {request.event}"}

        # Find contact by email
        contact = db.query(Contact).filter(Contact.email == request.recipient).first()

        if not contact:
            return {"success": False, "error": f"Contact not found: {request.recipient}"}

        # Build metadata
        metadata = {
            "vmta": request.vmta,
            "domain": request.domain,
            "message_id": request.message_id,
            "smtp_response": request.smtp_response,
            "bounce_category": request.bounce_category,
        }

        # Create event
        _create_contact_event(
            db=db,
            contact_id=contact.id,
            event_type=event_type,
            metadata=metadata,
        )

        # Track warmup stats if IP is in warming status
        # PowerMTA includes sending_ip in webhook payload
        _track_warmup_event(
            db=db,
            sending_ip=request.sending_ip,
            event_type=event_type,
        )

        # Update contact status for bounces
        from app.enums import ContactStatus

        if event_type == EventType.BOUNCED:
            # Determine if hard or soft bounce
            is_hard_bounce = request.bounce_category in ["bad-mailbox", "bad-domain", "policy-related"]

            if is_hard_bounce:
                contact.status = ContactStatus.BOUNCED
                db.commit()

        return {
            "success": True,
            "message": f"Event {request.event} recorded for {request.recipient}",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


@router.post("/generic", dependencies=[Depends(no_auth)])
def generic_webhook(
    request: GenericEventRequest,
    db: Session = Depends(get_db),
):
    """
    Generic webhook handler for custom integrations.

    Accepts any event and stores it.
    """
    try:
        # Map event type
        try:
            event_type = EventType(request.event_type.lower())
        except ValueError:
            return {"success": False, "error": f"Invalid event type: {request.event_type}"}

        # Find contact by email
        contact = db.query(Contact).filter(Contact.email == request.email).first()

        if not contact:
            return {"success": False, "error": f"Contact not found: {request.email}"}

        # Create event
        _create_contact_event(
            db=db,
            contact_id=contact.id,
            event_type=event_type,
            campaign_id=request.campaign_id,
            metadata=request.metadata or {},
        )

        return {
            "success": True,
            "message": f"Event {request.event_type} recorded for {request.email}",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


@router.post("/test", dependencies=[Depends(no_auth)])
def test_webhook(request: Request):
    """
    Test endpoint to inspect webhook payloads.

    Returns the raw request body for debugging.
    """
    import json

    try:
        body = request.json()
        return {
            "success": True,
            "message": "Webhook received",
            "payload": body,
            "headers": dict(request.headers),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "body_preview": request.body()[:500] if hasattr(request, "body") else None,
        }


@router.get("/health", dependencies=[Depends(no_auth)])
def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            "/webhooks/mailwizz",
            "/webhooks/powermta",
            "/webhooks/generic",
            "/webhooks/test",
        ],
    }
