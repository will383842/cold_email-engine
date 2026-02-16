"""Campaign Repository Interface (Port)."""

from abc import ABC, abstractmethod
from typing import Optional

from app.enums import CampaignStatus
from src.domain.entities import Campaign


class ICampaignRepository(ABC):
    """Campaign repository interface (Port)."""

    @abstractmethod
    def save(self, campaign: Campaign) -> Campaign:
        """Save campaign (insert or update)."""
        pass

    @abstractmethod
    def find_by_id(self, campaign_id: int) -> Optional[Campaign]:
        """Find campaign by ID."""
        pass

    @abstractmethod
    def find_by_status(self, tenant_id: int, status: CampaignStatus) -> list[Campaign]:
        """Find campaigns by status."""
        pass

    @abstractmethod
    def delete(self, campaign_id: int) -> None:
        """Delete campaign."""
        pass

    @abstractmethod
    def count_by_tenant(self, tenant_id: int) -> int:
        """Count campaigns for a tenant."""
        pass
