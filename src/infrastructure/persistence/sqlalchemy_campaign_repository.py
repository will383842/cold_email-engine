"""SQLAlchemy Campaign Repository Implementation."""

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.enums import CampaignStatus as CampaignStatusEnum
from app.models import Campaign as CampaignModel
from src.domain.entities import Campaign
from src.domain.repositories import ICampaignRepository
from src.domain.value_objects import Language, TagSlug


class SQLAlchemyCampaignRepository(ICampaignRepository):
    """SQLAlchemy implementation of Campaign Repository."""

    def __init__(self, db: Session):
        self.db = db

    def save(self, campaign: Campaign) -> Campaign:
        """Save campaign (insert or update)."""
        if campaign.id:
            # Update existing
            campaign_model = self.db.query(CampaignModel).filter_by(id=campaign.id).first()
            if not campaign_model:
                raise ValueError(f"Campaign {campaign.id} not found")
            self._update_model(campaign_model, campaign)
        else:
            # Insert new
            campaign_model = self._to_model(campaign)
            self.db.add(campaign_model)

        self.db.flush()
        campaign.id = campaign_model.id
        return campaign

    def find_by_id(self, campaign_id: int) -> Optional[Campaign]:
        """Find campaign by ID."""
        campaign_model = self.db.query(CampaignModel).filter_by(id=campaign_id).first()
        if not campaign_model:
            return None
        return self._to_entity(campaign_model)

    def find_by_status(self, tenant_id: int, status: CampaignStatusEnum) -> list[Campaign]:
        """Find campaigns by status."""
        campaign_models = (
            self.db.query(CampaignModel)
            .filter_by(tenant_id=tenant_id, status=status.value)
            .all()
        )
        return [self._to_entity(cm) for cm in campaign_models]

    def delete(self, campaign_id: int) -> None:
        """Delete campaign."""
        campaign_model = self.db.query(CampaignModel).filter_by(id=campaign_id).first()
        if campaign_model:
            self.db.delete(campaign_model)
            self.db.flush()

    def count_by_tenant(self, tenant_id: int) -> int:
        """Count campaigns for a tenant."""
        return self.db.query(CampaignModel).filter_by(tenant_id=tenant_id).count()

    # =========================================================================
    # Entity <-> Model Mapping
    # =========================================================================

    def _to_entity(self, model: CampaignModel) -> Campaign:
        """Convert SQLAlchemy model to domain entity."""
        # Parse tag filters
        tags_all = self._parse_tag_list(model.tags_all)
        tags_any = self._parse_tag_list(model.tags_any)
        exclude_tags = self._parse_tag_list(model.exclude_tags)

        return Campaign(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            status=CampaignStatusEnum(model.status),
            template_id=model.template_id,
            language=Language(model.language) if model.language else None,
            category=model.category,
            tags_all=tags_all,
            tags_any=tags_any,
            exclude_tags=exclude_tags,
            total_recipients=model.total_recipients,
            sent_count=model.sent_count,
            delivered_count=model.delivered_count,
            opened_count=model.opened_count,
            clicked_count=model.clicked_count,
            bounced_count=model.bounced_count,
            unsubscribed_count=model.unsubscribed_count,
            scheduled_at=model.scheduled_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            mailwizz_campaign_id=model.mailwizz_campaign_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Campaign) -> CampaignModel:
        """Convert domain entity to SQLAlchemy model."""
        return CampaignModel(
            tenant_id=entity.tenant_id,
            name=entity.name,
            status=entity.status.value,
            template_id=entity.template_id,
            language=entity.language.code if entity.language else None,
            category=entity.category,
            tags_all=self._serialize_tag_list(entity.tags_all),
            tags_any=self._serialize_tag_list(entity.tags_any),
            exclude_tags=self._serialize_tag_list(entity.exclude_tags),
            total_recipients=entity.total_recipients,
            sent_count=entity.sent_count,
            delivered_count=entity.delivered_count,
            opened_count=entity.opened_count,
            clicked_count=entity.clicked_count,
            bounced_count=entity.bounced_count,
            unsubscribed_count=entity.unsubscribed_count,
            scheduled_at=entity.scheduled_at,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            mailwizz_campaign_id=entity.mailwizz_campaign_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _update_model(self, model: CampaignModel, entity: Campaign) -> None:
        """Update SQLAlchemy model from domain entity."""
        model.name = entity.name
        model.status = entity.status.value
        model.template_id = entity.template_id
        model.language = entity.language.code if entity.language else None
        model.category = entity.category
        model.tags_all = self._serialize_tag_list(entity.tags_all)
        model.tags_any = self._serialize_tag_list(entity.tags_any)
        model.exclude_tags = self._serialize_tag_list(entity.exclude_tags)
        model.total_recipients = entity.total_recipients
        model.sent_count = entity.sent_count
        model.delivered_count = entity.delivered_count
        model.opened_count = entity.opened_count
        model.clicked_count = entity.clicked_count
        model.bounced_count = entity.bounced_count
        model.unsubscribed_count = entity.unsubscribed_count
        model.scheduled_at = entity.scheduled_at
        model.started_at = entity.started_at
        model.completed_at = entity.completed_at
        model.mailwizz_campaign_id = entity.mailwizz_campaign_id
        model.updated_at = entity.updated_at

    def _parse_tag_list(self, json_str: Optional[str]) -> list[TagSlug]:
        """Parse JSON string to list of TagSlug."""
        if not json_str:
            return []
        try:
            slugs = json.loads(json_str)
            return [TagSlug(slug) for slug in slugs]
        except (json.JSONDecodeError, ValueError):
            return []

    def _serialize_tag_list(self, tags: list[TagSlug]) -> str:
        """Serialize list of TagSlug to JSON string."""
        return json.dumps([tag.value for tag in tags])
