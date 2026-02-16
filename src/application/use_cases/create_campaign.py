"""Create Campaign Use Case."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.enums import CampaignStatus
from src.domain.repositories import ICampaignRepository


@dataclass
class CreateCampaignDTO:
    """DTO for creating a campaign."""

    tenant_id: int
    name: str
    template_id: Optional[int] = None
    language: Optional[str] = None
    category: Optional[str] = None
    tags_all: Optional[list[str]] = None  # AND condition
    tags_any: Optional[list[str]] = None  # OR condition
    exclude_tags: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None


@dataclass
class CreateCampaignResult:
    """Result of campaign creation."""

    campaign_id: int
    name: str
    status: str


class CreateCampaignUseCase:
    """Use case for creating a new campaign."""

    def __init__(self, campaign_repo: ICampaignRepository):
        self.campaign_repo = campaign_repo

    def execute(self, dto: CreateCampaignDTO) -> CreateCampaignResult:
        """
        Create a new campaign.

        Args:
            dto: Campaign creation data

        Returns:
            CreateCampaignResult with campaign ID and status
        """
        # Import here to avoid circular dependency
        from src.domain.entities import Campaign as CampaignEntity
        from src.domain.value_objects import TagSlug, Language

        # Create campaign entity
        campaign = CampaignEntity(
            tenant_id=dto.tenant_id,
            name=dto.name,
            status=CampaignStatus.DRAFT,
            template_id=dto.template_id,
            language=Language(dto.language) if dto.language else None,
            category=dto.category,
            scheduled_at=dto.scheduled_at,
        )

        # Add tag filters
        if dto.tags_all:
            campaign.tags_all = [TagSlug.from_string(tag) for tag in dto.tags_all]
        if dto.tags_any:
            campaign.tags_any = [TagSlug.from_string(tag) for tag in dto.tags_any]
        if dto.exclude_tags:
            campaign.exclude_tags = [TagSlug.from_string(tag) for tag in dto.exclude_tags]

        # Save via repository
        saved_campaign = self.campaign_repo.save(campaign)

        return CreateCampaignResult(
            campaign_id=saved_campaign.id,
            name=saved_campaign.name,
            status=saved_campaign.status.value,
        )
