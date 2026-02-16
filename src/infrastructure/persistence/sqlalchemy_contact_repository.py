"""SQLAlchemy Contact Repository Implementation."""

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.enums import ContactStatus as ContactStatusEnum
from app.enums import ValidationStatus as ValidationStatusEnum
from app.models import Contact as ContactModel
from app.models import ContactTag as ContactTagModel
from app.models import Tag as TagModel
from src.domain.entities import Contact
from src.domain.repositories import IContactRepository
from src.domain.value_objects import Email, Language, TagSlug


class SQLAlchemyContactRepository(IContactRepository):
    """SQLAlchemy implementation of Contact Repository."""

    def __init__(self, db: Session):
        self.db = db

    def save(self, contact: Contact) -> Contact:
        """Save contact (insert or update)."""
        if contact.id:
            # Update existing
            contact_model = self.db.query(ContactModel).filter_by(id=contact.id).first()
            if not contact_model:
                raise ValueError(f"Contact {contact.id} not found")
            self._update_model(contact_model, contact)
        else:
            # Insert new
            contact_model = self._to_model(contact)
            self.db.add(contact_model)

        self.db.flush()
        contact.id = contact_model.id
        return contact

    def find_by_id(self, contact_id: int) -> Optional[Contact]:
        """Find contact by ID."""
        contact_model = self.db.query(ContactModel).filter_by(id=contact_id).first()
        if not contact_model:
            return None
        return self._to_entity(contact_model)

    def find_by_email(self, tenant_id: int, email: Email) -> Optional[Contact]:
        """Find contact by email (scoped to tenant)."""
        contact_model = (
            self.db.query(ContactModel)
            .filter_by(tenant_id=tenant_id, email=email.value)
            .first()
        )
        if not contact_model:
            return None
        return self._to_entity(contact_model)

    def find_by_tags(
        self,
        tenant_id: int,
        tags_all: Optional[list[TagSlug]] = None,
        tags_any: Optional[list[TagSlug]] = None,
        exclude_tags: Optional[list[TagSlug]] = None,
        limit: int = 100,
    ) -> list[Contact]:
        """Find contacts by tag filters."""
        query = self.db.query(ContactModel).filter_by(tenant_id=tenant_id)

        # Tags ALL (AND condition)
        if tags_all:
            for tag_slug in tags_all:
                query = query.join(ContactTagModel).join(TagModel).filter(
                    TagModel.slug == tag_slug.value
                )

        # Tags ANY (OR condition) - TODO: Implement properly with subquery
        # For now, this is a simplified version
        if tags_any:
            tag_slugs = [t.value for t in tags_any]
            query = query.join(ContactTagModel).join(TagModel).filter(
                TagModel.slug.in_(tag_slugs)
            )

        # Exclude tags
        if exclude_tags:
            # TODO: Implement exclude properly with NOT IN subquery
            pass

        # Limit and execute
        contact_models = query.limit(limit).all()
        return [self._to_entity(cm) for cm in contact_models]

    def delete(self, contact_id: int) -> None:
        """Delete contact."""
        contact_model = self.db.query(ContactModel).filter_by(id=contact_id).first()
        if contact_model:
            self.db.delete(contact_model)
            self.db.flush()

    def count_by_tenant(self, tenant_id: int) -> int:
        """Count contacts for a tenant."""
        return self.db.query(ContactModel).filter_by(tenant_id=tenant_id).count()

    # =========================================================================
    # Entity <-> Model Mapping
    # =========================================================================

    def _to_entity(self, model: ContactModel) -> Contact:
        """Convert SQLAlchemy model to domain entity."""
        # Parse tags
        tags = []
        for ct in model.contact_tags:
            tags.append(TagSlug(ct.tag.slug))

        # Parse custom fields
        custom_fields = {}
        if model.custom_fields:
            try:
                custom_fields = json.loads(model.custom_fields)
            except json.JSONDecodeError:
                custom_fields = {}

        # Parse validation errors
        validation_errors = []
        if model.validation_errors:
            try:
                validation_errors = json.loads(model.validation_errors)
            except json.JSONDecodeError:
                validation_errors = []

        return Contact(
            id=model.id,
            tenant_id=model.tenant_id,
            data_source_id=model.data_source_id,
            email=Email(model.email),
            language=Language(model.language),
            first_name=model.first_name,
            last_name=model.last_name,
            company=model.company,
            website=model.website,
            category=model.category,
            phone=model.phone,
            country=model.country,
            city=model.city,
            linkedin_url=model.linkedin_url,
            facebook_url=model.facebook_url,
            instagram_url=model.instagram_url,
            twitter_url=model.twitter_url,
            custom_fields=custom_fields,
            status=ContactStatusEnum(model.status),
            validation_status=ValidationStatusEnum(model.validation_status)
            if model.validation_status
            else None,
            validation_score=model.validation_score,
            validation_errors=validation_errors,
            tags=tags,
            mailwizz_subscriber_id=model.mailwizz_subscriber_id,
            mailwizz_list_id=model.mailwizz_list_id,
            last_campaign_sent_at=model.last_campaign_sent_at,
            total_campaigns_received=model.total_campaigns_received,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Contact) -> ContactModel:
        """Convert domain entity to SQLAlchemy model."""
        return ContactModel(
            tenant_id=entity.tenant_id,
            data_source_id=entity.data_source_id,
            email=entity.email.value,
            first_name=entity.first_name,
            last_name=entity.last_name,
            company=entity.company,
            website=entity.website,
            language=entity.language.code,
            category=entity.category,
            phone=entity.phone,
            country=entity.country,
            city=entity.city,
            linkedin_url=entity.linkedin_url,
            facebook_url=entity.facebook_url,
            instagram_url=entity.instagram_url,
            twitter_url=entity.twitter_url,
            custom_fields=json.dumps(entity.custom_fields),
            status=entity.status.value,
            validation_status=entity.validation_status.value if entity.validation_status else None,
            validation_score=entity.validation_score,
            validation_errors=json.dumps(entity.validation_errors),
            mailwizz_subscriber_id=entity.mailwizz_subscriber_id,
            mailwizz_list_id=entity.mailwizz_list_id,
            last_campaign_sent_at=entity.last_campaign_sent_at,
            total_campaigns_received=entity.total_campaigns_received,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _update_model(self, model: ContactModel, entity: Contact) -> None:
        """Update SQLAlchemy model from domain entity."""
        model.email = entity.email.value
        model.first_name = entity.first_name
        model.last_name = entity.last_name
        model.company = entity.company
        model.website = entity.website
        model.language = entity.language.code
        model.category = entity.category
        model.phone = entity.phone
        model.country = entity.country
        model.city = entity.city
        model.linkedin_url = entity.linkedin_url
        model.facebook_url = entity.facebook_url
        model.instagram_url = entity.instagram_url
        model.twitter_url = entity.twitter_url
        model.custom_fields = json.dumps(entity.custom_fields)
        model.status = entity.status.value
        model.validation_status = entity.validation_status.value if entity.validation_status else None
        model.validation_score = entity.validation_score
        model.validation_errors = json.dumps(entity.validation_errors)
        model.mailwizz_subscriber_id = entity.mailwizz_subscriber_id
        model.mailwizz_list_id = entity.mailwizz_list_id
        model.last_campaign_sent_at = entity.last_campaign_sent_at
        model.total_campaigns_received = entity.total_campaigns_received
        model.updated_at = entity.updated_at
