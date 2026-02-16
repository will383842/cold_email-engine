"""Send Campaign Use Case."""

from dataclasses import dataclass

from app.enums import CampaignStatus
from src.domain.repositories import ICampaignRepository


@dataclass
class SendCampaignResult:
    """Result of campaign send operation."""

    campaign_id: int
    status: str
    message: str


class SendCampaignUseCase:
    """Use case for sending a campaign."""

    def __init__(self, campaign_repo: ICampaignRepository):
        self.campaign_repo = campaign_repo

    def execute(self, campaign_id: int) -> SendCampaignResult:
        """
        Send a campaign (or schedule it for sending).

        This triggers the background job to send the campaign via MailWizz.

        Args:
            campaign_id: Campaign ID to send

        Returns:
            SendCampaignResult with status

        Raises:
            ValueError: If campaign not found or not in sendable state
        """
        # Get campaign
        campaign = self.campaign_repo.find_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Check if campaign can be sent
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError(
                f"Campaign {campaign_id} cannot be sent (status: {campaign.status.value})"
            )

        # Start campaign (business logic in entity)
        campaign.start()

        # Save updated campaign
        self.campaign_repo.save(campaign)

        # Trigger background job (Celery task)
        try:
            from src.infrastructure.background import send_campaign_task

            send_campaign_task.delay(campaign_id)
            message = "Campaign queued for sending"
        except ImportError:
            # Celery not available (development mode)
            message = "Campaign status updated (Celery not available)"

        return SendCampaignResult(
            campaign_id=campaign_id,
            status=campaign.status.value,
            message=message,
        )
