"""Update Campaign Use Case."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.repositories import ICampaignRepository


@dataclass
class UpdateCampaignDTO:
    """DTO for updating a campaign."""

    campaign_id: int
    name: Optional[str] = None
    template_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None


class UpdateCampaignUseCase:
    """Use case for updating a campaign."""

    def __init__(self, campaign_repo: ICampaignRepository):
        self.campaign_repo = campaign_repo

    def execute(self, dto: UpdateCampaignDTO) -> dict:
        """
        Update campaign fields.

        Args:
            dto: Campaign update data

        Returns:
            Updated campaign dict

        Raises:
            ValueError: If campaign not found
        """
        # Get campaign
        campaign = self.campaign_repo.find_by_id(dto.campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {dto.campaign_id} not found")

        # Update fields
        if dto.name:
            campaign.name = dto.name
        if dto.template_id:
            campaign.template_id = dto.template_id
        if dto.scheduled_at:
            campaign.schedule(dto.scheduled_at)

        # Save
        self.campaign_repo.save(campaign)

        return {
            "campaign_id": campaign.id,
            "name": campaign.name,
            "status": campaign.status.value,
            "scheduled_at": campaign.scheduled_at,
        }
