"""Repository Interfaces (Ports) - Domain layer."""

from .contact_repository import IContactRepository
from .campaign_repository import ICampaignRepository
from .template_repository import ITemplateRepository

__all__ = ["IContactRepository", "ICampaignRepository", "ITemplateRepository"]
