"""Persistence adapters - SQLAlchemy implementations."""

from .sqlalchemy_contact_repository import SQLAlchemyContactRepository
from .sqlalchemy_campaign_repository import SQLAlchemyCampaignRepository
from .sqlalchemy_template_repository import SQLAlchemyTemplateRepository

__all__ = [
    "SQLAlchemyContactRepository",
    "SQLAlchemyCampaignRepository",
    "SQLAlchemyTemplateRepository",
]
