"""Campaigns API v2 - CRUD operations."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from src.application.use_cases import (
    CreateCampaignUseCase,
    SendCampaignUseCase,
    UpdateCampaignUseCase,
)
from src.application.use_cases.create_campaign import CreateCampaignDTO
from src.application.use_cases.update_campaign import UpdateCampaignDTO
from src.infrastructure.persistence import SQLAlchemyCampaignRepository
from .auth import no_auth  # Simple auth for internal tool

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CreateCampaignRequest(BaseModel):
    """Request schema for creating a campaign."""

    tenant_id: int
    name: str
    template_id: Optional[int] = None
    language: Optional[str] = None
    category: Optional[str] = None
    tags_all: Optional[List[str]] = None
    tags_any: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None


class UpdateCampaignRequest(BaseModel):
    """Request schema for updating a campaign."""

    name: Optional[str] = None
    template_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None


class CampaignResponse(BaseModel):
    """Response schema for a campaign."""

    id: int
    tenant_id: int
    name: str
    status: str
    template_id: Optional[int]
    language: Optional[str]
    category: Optional[str]
    total_recipients: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    scheduled_at: Optional[datetime]


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/", dependencies=[Depends(no_auth)])
def create_campaign(
    request: CreateCampaignRequest,
    db: Session = Depends(get_db),
):
    """Create a new campaign."""
    try:
        campaign_repo = SQLAlchemyCampaignRepository(db)
        use_case = CreateCampaignUseCase(campaign_repo)

        dto = CreateCampaignDTO(
            tenant_id=request.tenant_id,
            name=request.name,
            template_id=request.template_id,
            language=request.language,
            category=request.category,
            tags_all=request.tags_all,
            tags_any=request.tags_any,
            exclude_tags=request.exclude_tags,
            scheduled_at=request.scheduled_at,
        )

        result = use_case.execute(dto)
        db.commit()

        return {"success": True, "campaign": result}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


@router.get("/{tenant_id}", response_model=List[CampaignResponse], dependencies=[Depends(no_auth)])
def list_campaigns(
    tenant_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List campaigns for a tenant."""
    try:
        campaign_repo = SQLAlchemyCampaignRepository(db)

        if status:
            from app.enums import CampaignStatus

            campaigns = campaign_repo.find_by_status(tenant_id, CampaignStatus(status))
        else:
            # Get all (would need a new repo method, for now just return empty or implement)
            campaigns = []

        return [
            CampaignResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                name=c.name,
                status=c.status.value,
                template_id=c.template_id,
                language=c.language.code if c.language else None,
                category=c.category,
                total_recipients=c.total_recipients,
                sent_count=c.sent_count,
                delivered_count=c.delivered_count,
                opened_count=c.opened_count,
                clicked_count=c.clicked_count,
                scheduled_at=c.scheduled_at,
            )
            for c in campaigns
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list campaigns: {str(e)}")


@router.get("/{tenant_id}/{campaign_id}", response_model=CampaignResponse, dependencies=[Depends(no_auth)])
def get_campaign(
    tenant_id: int,
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Get a single campaign."""
    try:
        campaign_repo = SQLAlchemyCampaignRepository(db)
        campaign = campaign_repo.find_by_id(campaign_id)

        if not campaign or campaign.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return CampaignResponse(
            id=campaign.id,
            tenant_id=campaign.tenant_id,
            name=campaign.name,
            status=campaign.status.value,
            template_id=campaign.template_id,
            language=campaign.language.code if campaign.language else None,
            category=campaign.category,
            total_recipients=campaign.total_recipients,
            sent_count=campaign.sent_count,
            delivered_count=campaign.delivered_count,
            opened_count=campaign.opened_count,
            clicked_count=campaign.clicked_count,
            scheduled_at=campaign.scheduled_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign: {str(e)}")


@router.put("/{tenant_id}/{campaign_id}", dependencies=[Depends(no_auth)])
def update_campaign(
    tenant_id: int,
    campaign_id: int,
    request: UpdateCampaignRequest,
    db: Session = Depends(get_db),
):
    """Update a campaign."""
    try:
        campaign_repo = SQLAlchemyCampaignRepository(db)
        use_case = UpdateCampaignUseCase(campaign_repo)

        dto = UpdateCampaignDTO(
            campaign_id=campaign_id,
            name=request.name,
            template_id=request.template_id,
            scheduled_at=request.scheduled_at,
        )

        result = use_case.execute(dto)
        db.commit()

        return {"success": True, "campaign": result}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update campaign: {str(e)}")


@router.post("/{tenant_id}/{campaign_id}/send", dependencies=[Depends(no_auth)])
def send_campaign(
    tenant_id: int,
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Send a campaign (triggers background job)."""
    try:
        campaign_repo = SQLAlchemyCampaignRepository(db)
        use_case = SendCampaignUseCase(campaign_repo)

        result = use_case.execute(campaign_id)
        db.commit()

        return {
            "success": True,
            "campaign_id": result.campaign_id,
            "status": result.status,
            "message": result.message,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to send campaign: {str(e)}")


@router.delete("/{tenant_id}/{campaign_id}", dependencies=[Depends(no_auth)])
def delete_campaign(
    tenant_id: int,
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Delete a campaign."""
    try:
        campaign_repo = SQLAlchemyCampaignRepository(db)

        # Verify it belongs to tenant
        campaign = campaign_repo.find_by_id(campaign_id)
        if not campaign or campaign.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign_repo.delete(campaign_id)
        db.commit()

        return {"success": True, "message": "Campaign deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")
