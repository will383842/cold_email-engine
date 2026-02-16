"""Quotas API v2 - Check warmup quotas and available capacity."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from src.domain.services import QuotaChecker
from .auth import no_auth

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class QuotaInfoResponse(BaseModel):
    """Quota information for a single IP."""

    ip_id: int
    ip_address: str
    status: str
    phase: str | None = None
    daily_quota: int | str  # int for warming, "unlimited" for active
    sent_today: int
    remaining: int | str  # int for warming, "unlimited" for active
    paused: bool = False
    pause_until: str | None = None
    bounce_rate_7d: float | None = None
    spam_rate_7d: float | None = None


class TenantCapacityResponse(BaseModel):
    """Total capacity for a tenant."""

    tenant_id: int
    total_ips: int
    active_ips: int
    warming_ips: int
    paused_ips: int
    total_daily_capacity: int | str  # Total emails that can be sent today
    remaining_today: int | str  # Remaining capacity for today
    ips: List[QuotaInfoResponse]


class QuotaCheckRequest(BaseModel):
    """Request to check if X emails can be sent."""

    emails_to_send: int


class QuotaCheckResponse(BaseModel):
    """Response for quota check."""

    can_send: bool
    message: str
    available_ips: List[dict]
    recommended_ip: dict | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/{tenant_id}", response_model=TenantCapacityResponse, dependencies=[Depends(no_auth)])
def get_tenant_quotas(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """
    Get quota information for all IPs of a tenant.

    Returns current capacity, what's been sent today, and what remains.
    """
    try:
        from app.models import IP

        checker = QuotaChecker(db)

        # Get all IPs for tenant
        ips = db.query(IP).filter_by(tenant_id=tenant_id).all()

        if not ips:
            raise HTTPException(status_code=404, detail=f"No IPs found for tenant {tenant_id}")

        # Build response
        ip_responses = []
        total_daily_capacity = 0
        remaining_today = 0
        active_count = 0
        warming_count = 0
        paused_count = 0
        has_unlimited = False

        for ip in ips:
            quota_info = checker.get_quota_info(ip.id)

            if not quota_info:
                continue

            # Count by status
            if quota_info.get("status") == "active":
                active_count += 1
                has_unlimited = True
            elif quota_info.get("status") == "warming":
                warming_count += 1
                if quota_info.get("paused"):
                    paused_count += 1

            # Calculate totals
            daily_quota = quota_info.get("daily_quota", 0)
            if isinstance(daily_quota, int):
                total_daily_capacity += daily_quota

            remaining = quota_info.get("remaining", 0)
            if isinstance(remaining, int):
                remaining_today += remaining

            ip_responses.append(QuotaInfoResponse(
                ip_id=ip.id,
                ip_address=quota_info.get("ip_address", ip.address),
                status=quota_info.get("status", "unknown"),
                phase=quota_info.get("phase"),
                daily_quota=quota_info.get("daily_quota", 0),
                sent_today=quota_info.get("sent_today", 0),
                remaining=quota_info.get("remaining", 0),
                paused=quota_info.get("paused", False),
                pause_until=quota_info.get("pause_until"),
                bounce_rate_7d=quota_info.get("bounce_rate_7d"),
                spam_rate_7d=quota_info.get("spam_rate_7d"),
            ))

        return TenantCapacityResponse(
            tenant_id=tenant_id,
            total_ips=len(ips),
            active_ips=active_count,
            warming_ips=warming_count,
            paused_ips=paused_count,
            total_daily_capacity="unlimited" if has_unlimited else total_daily_capacity,
            remaining_today="unlimited" if has_unlimited else remaining_today,
            ips=ip_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quotas: {str(e)}")


@router.post("/{tenant_id}/check", response_model=QuotaCheckResponse, dependencies=[Depends(no_auth)])
def check_quota(
    tenant_id: int,
    request: QuotaCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Check if tenant can send X emails today.

    Returns list of available IPs and recommended IP to use.
    """
    try:
        checker = QuotaChecker(db)

        # Get available IPs
        available_ips = checker.get_available_ips_for_sending(
            tenant_id=tenant_id,
            emails_to_send=request.emails_to_send
        )

        can_send = len(available_ips) > 0
        recommended_ip = available_ips[0] if available_ips else None

        if can_send:
            message = (
                f"✅ Can send {request.emails_to_send} emails. "
                f"Recommended IP: {recommended_ip['address']} "
                f"({recommended_ip['remaining']} remaining today)"
            )
        else:
            message = (
                f"❌ Cannot send {request.emails_to_send} emails. "
                f"No IPs with sufficient quota available."
            )

        return QuotaCheckResponse(
            can_send=can_send,
            message=message,
            available_ips=available_ips,
            recommended_ip=recommended_ip,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check quota: {str(e)}")


@router.get("/{tenant_id}/ip/{ip_id}", response_model=QuotaInfoResponse, dependencies=[Depends(no_auth)])
def get_ip_quota(
    tenant_id: int,
    ip_id: int,
    db: Session = Depends(get_db),
):
    """Get quota information for a specific IP."""
    try:
        from app.models import IP

        # Verify IP belongs to tenant
        ip = db.query(IP).filter_by(id=ip_id, tenant_id=tenant_id).first()

        if not ip:
            raise HTTPException(status_code=404, detail=f"IP {ip_id} not found for tenant {tenant_id}")

        checker = QuotaChecker(db)
        quota_info = checker.get_quota_info(ip_id)

        if not quota_info:
            raise HTTPException(status_code=404, detail=f"No quota info for IP {ip_id}")

        return QuotaInfoResponse(
            ip_id=ip.id,
            ip_address=quota_info.get("ip_address", ip.address),
            status=quota_info.get("status", "unknown"),
            phase=quota_info.get("phase"),
            daily_quota=quota_info.get("daily_quota", 0),
            sent_today=quota_info.get("sent_today", 0),
            remaining=quota_info.get("remaining", 0),
            paused=quota_info.get("paused", False),
            pause_until=quota_info.get("pause_until"),
            bounce_rate_7d=quota_info.get("bounce_rate_7d"),
            spam_rate_7d=quota_info.get("spam_rate_7d"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IP quota: {str(e)}")
