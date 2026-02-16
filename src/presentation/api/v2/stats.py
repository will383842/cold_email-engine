"""Stats API v2 - Statistics and metrics endpoints."""

from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models import Contact, Campaign, ContactEvent, EmailTemplate
from app.enums import ContactStatus, ValidationStatus, CampaignStatus, EventType, Language
from .auth import no_auth  # Simple auth for internal tool

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class ContactStatsResponse(BaseModel):
    """Contact statistics response."""

    total_contacts: int
    by_status: dict[str, int]
    by_validation: dict[str, int]
    by_language: dict[str, int]
    valid_percentage: float
    risky_percentage: float
    invalid_percentage: float


class CampaignStatsResponse(BaseModel):
    """Campaign statistics response."""

    total_campaigns: int
    by_status: dict[str, int]
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    delivery_rate: float
    open_rate: float
    click_rate: float


class EventStatsResponse(BaseModel):
    """Event statistics response."""

    total_events: int
    by_type: dict[str, int]
    recent_events: int  # Last 24h
    bounce_rate: float
    complaint_rate: float


class TenantOverviewResponse(BaseModel):
    """Tenant overview statistics."""

    tenant_id: int
    contacts: ContactStatsResponse
    campaigns: CampaignStatsResponse
    events: EventStatsResponse
    templates_count: int


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics over time."""

    period: str
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    complaint_count: int
    delivery_rate: float
    open_rate: float
    click_rate: float


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/{tenant_id}/contacts", response_model=ContactStatsResponse, dependencies=[Depends(no_auth)])
def get_contact_stats(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """Get contact statistics for a tenant."""
    try:
        # Total contacts
        total = db.query(Contact).filter(Contact.tenant_id == tenant_id).count()

        # By status
        status_counts = (
            db.query(Contact.status, func.count(Contact.id))
            .filter(Contact.tenant_id == tenant_id)
            .group_by(Contact.status)
            .all()
        )
        by_status = {status.value: count for status, count in status_counts}

        # By validation
        validation_counts = (
            db.query(Contact.validation_status, func.count(Contact.id))
            .filter(Contact.tenant_id == tenant_id)
            .group_by(Contact.validation_status)
            .all()
        )
        by_validation = {
            status.value if status else "pending": count
            for status, count in validation_counts
        }

        # By language
        language_counts = (
            db.query(Contact.language, func.count(Contact.id))
            .filter(Contact.tenant_id == tenant_id)
            .group_by(Contact.language)
            .all()
        )
        by_language = {lang.value: count for lang, count in language_counts}

        # Percentages
        valid = by_validation.get("valid", 0)
        risky = by_validation.get("risky", 0)
        invalid = by_validation.get("invalid", 0)
        validated_total = valid + risky + invalid

        return ContactStatsResponse(
            total_contacts=total,
            by_status=by_status,
            by_validation=by_validation,
            by_language=by_language,
            valid_percentage=round((valid / validated_total * 100) if validated_total > 0 else 0, 2),
            risky_percentage=round((risky / validated_total * 100) if validated_total > 0 else 0, 2),
            invalid_percentage=round((invalid / validated_total * 100) if validated_total > 0 else 0, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contact stats: {str(e)}")


@router.get("/{tenant_id}/campaigns", response_model=CampaignStatsResponse, dependencies=[Depends(no_auth)])
def get_campaign_stats(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """Get campaign statistics for a tenant."""
    try:
        # Total campaigns
        total = db.query(Campaign).filter(Campaign.tenant_id == tenant_id).count()

        # By status
        status_counts = (
            db.query(Campaign.status, func.count(Campaign.id))
            .filter(Campaign.tenant_id == tenant_id)
            .group_by(Campaign.status)
            .all()
        )
        by_status = {status.value: count for status, count in status_counts}

        # Aggregated metrics
        metrics = (
            db.query(
                func.sum(Campaign.sent_count).label("total_sent"),
                func.sum(Campaign.delivered_count).label("total_delivered"),
                func.sum(Campaign.opened_count).label("total_opened"),
                func.sum(Campaign.clicked_count).label("total_clicked"),
            )
            .filter(Campaign.tenant_id == tenant_id)
            .first()
        )

        total_sent = metrics.total_sent or 0
        total_delivered = metrics.total_delivered or 0
        total_opened = metrics.total_opened or 0
        total_clicked = metrics.total_clicked or 0

        return CampaignStatsResponse(
            total_campaigns=total,
            by_status=by_status,
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_opened=total_opened,
            total_clicked=total_clicked,
            delivery_rate=round((total_delivered / total_sent * 100) if total_sent > 0 else 0, 2),
            open_rate=round((total_opened / total_delivered * 100) if total_delivered > 0 else 0, 2),
            click_rate=round((total_clicked / total_delivered * 100) if total_delivered > 0 else 0, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign stats: {str(e)}")


@router.get("/{tenant_id}/events", response_model=EventStatsResponse, dependencies=[Depends(no_auth)])
def get_event_stats(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """Get event statistics for a tenant."""
    try:
        from app.models import Contact

        # Total events
        total = (
            db.query(ContactEvent)
            .join(Contact)
            .filter(Contact.tenant_id == tenant_id)
            .count()
        )

        # By type
        type_counts = (
            db.query(ContactEvent.event_type, func.count(ContactEvent.id))
            .join(Contact)
            .filter(Contact.tenant_id == tenant_id)
            .group_by(ContactEvent.event_type)
            .all()
        )
        by_type = {event_type.value: count for event_type, count in type_counts}

        # Recent events (last 24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent = (
            db.query(ContactEvent)
            .join(Contact)
            .filter(
                Contact.tenant_id == tenant_id,
                ContactEvent.created_at >= yesterday,
            )
            .count()
        )

        # Rates
        delivered = by_type.get("delivered", 0)
        bounced = by_type.get("bounced", 0)
        complained = by_type.get("complained", 0)

        total_sends = delivered + bounced

        return EventStatsResponse(
            total_events=total,
            by_type=by_type,
            recent_events=recent,
            bounce_rate=round((bounced / total_sends * 100) if total_sends > 0 else 0, 2),
            complaint_rate=round((complained / delivered * 100) if delivered > 0 else 0, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get event stats: {str(e)}")


@router.get("/{tenant_id}/overview", response_model=TenantOverviewResponse, dependencies=[Depends(no_auth)])
def get_tenant_overview(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """Get complete overview for a tenant."""
    try:
        # Get all stats
        contact_stats = get_contact_stats(tenant_id, db)
        campaign_stats = get_campaign_stats(tenant_id, db)
        event_stats = get_event_stats(tenant_id, db)

        # Template count
        templates_count = (
            db.query(EmailTemplate).filter(EmailTemplate.tenant_id == tenant_id).count()
        )

        return TenantOverviewResponse(
            tenant_id=tenant_id,
            contacts=contact_stats,
            campaigns=campaign_stats,
            events=event_stats,
            templates_count=templates_count,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tenant overview: {str(e)}")


@router.get("/{tenant_id}/performance", response_model=list[PerformanceMetricsResponse], dependencies=[Depends(no_auth)])
def get_performance_metrics(
    tenant_id: int,
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db),
):
    """
    Get performance metrics over time (daily breakdown).

    Returns metrics for the last N days.
    """
    try:
        from app.models import Contact

        metrics = []
        today = datetime.utcnow().date()

        for day_offset in range(days):
            date = today - timedelta(days=day_offset)
            next_date = date + timedelta(days=1)

            # Get events for this day
            day_events = (
                db.query(ContactEvent.event_type, func.count(ContactEvent.id))
                .join(Contact)
                .filter(
                    Contact.tenant_id == tenant_id,
                    ContactEvent.created_at >= date,
                    ContactEvent.created_at < next_date,
                )
                .group_by(ContactEvent.event_type)
                .all()
            )

            event_counts = {event_type.value: count for event_type, count in day_events}

            sent = event_counts.get("sent", 0)
            delivered = event_counts.get("delivered", 0)
            opened = event_counts.get("opened", 0)
            clicked = event_counts.get("clicked", 0)
            bounced = event_counts.get("bounced", 0)
            complained = event_counts.get("complained", 0)

            metrics.append(
                PerformanceMetricsResponse(
                    period=date.isoformat(),
                    sent_count=sent,
                    delivered_count=delivered,
                    opened_count=opened,
                    clicked_count=clicked,
                    bounced_count=bounced,
                    complaint_count=complained,
                    delivery_rate=round((delivered / sent * 100) if sent > 0 else 0, 2),
                    open_rate=round((opened / delivered * 100) if delivered > 0 else 0, 2),
                    click_rate=round((clicked / delivered * 100) if delivered > 0 else 0, 2),
                )
            )

        # Return in chronological order
        return list(reversed(metrics))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")
