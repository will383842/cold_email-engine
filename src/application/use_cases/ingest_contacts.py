"""Ingest Contacts Use Case."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.enums import ContactStatus
from src.domain.entities import Contact
from src.domain.repositories import IContactRepository
from src.domain.value_objects import Email, Language, TagSlug


@dataclass
class IngestContactDTO:
    """DTO for ingesting a single contact."""

    tenant_id: int
    data_source_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    language: str = "en"
    category: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_fields: Optional[dict] = None
    tags: Optional[list[str]] = None  # Tag slugs


@dataclass
class IngestContactsResult:
    """Result of contact ingestion."""

    total_processed: int
    new_contacts: int
    updated_contacts: int
    duplicates_skipped: int
    errors: list[str]


class IngestContactsUseCase:
    """Use case for ingesting contacts from external sources."""

    def __init__(self, contact_repo: IContactRepository):
        self.contact_repo = contact_repo

    def execute(self, contacts_data: list[IngestContactDTO]) -> IngestContactsResult:
        """Ingest multiple contacts."""
        result = IngestContactsResult(
            total_processed=0,
            new_contacts=0,
            updated_contacts=0,
            duplicates_skipped=0,
            errors=[],
        )

        for contact_dto in contacts_data:
            try:
                # Validate email
                email = Email(contact_dto.email)

                # Check if contact already exists
                existing = self.contact_repo.find_by_email(contact_dto.tenant_id, email)

                if existing:
                    # Update existing contact
                    self._update_contact(existing, contact_dto)
                    self.contact_repo.save(existing)
                    result.updated_contacts += 1
                else:
                    # Create new contact
                    contact = self._create_contact(contact_dto, email)
                    self.contact_repo.save(contact)
                    result.new_contacts += 1

                result.total_processed += 1

            except ValueError as e:
                result.errors.append(f"Invalid email {contact_dto.email}: {str(e)}")
            except Exception as e:
                result.errors.append(f"Error processing {contact_dto.email}: {str(e)}")

        return result

    def _create_contact(self, dto: IngestContactDTO, email: Email) -> Contact:
        """Create new contact entity."""
        # Create language value object
        language = Language(dto.language)

        # Create tag slugs
        tags = []
        if dto.tags:
            for tag_str in dto.tags:
                tags.append(TagSlug.from_string(tag_str))

        # Create contact entity
        contact = Contact(
            tenant_id=dto.tenant_id,
            data_source_id=dto.data_source_id,
            email=email,
            language=language,
            first_name=dto.first_name,
            last_name=dto.last_name,
            company=dto.company,
            website=dto.website,
            category=dto.category,
            phone=dto.phone,
            country=dto.country,
            city=dto.city,
            linkedin_url=dto.linkedin_url,
            facebook_url=dto.facebook_url,
            instagram_url=dto.instagram_url,
            twitter_url=dto.twitter_url,
            custom_fields=dto.custom_fields or {},
            tags=tags,
            status=ContactStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        return contact

    def _update_contact(self, contact: Contact, dto: IngestContactDTO) -> None:
        """Update existing contact with new data."""
        # Update attributes (only if provided)
        if dto.first_name:
            contact.first_name = dto.first_name
        if dto.last_name:
            contact.last_name = dto.last_name
        if dto.company:
            contact.company = dto.company
        if dto.website:
            contact.website = dto.website
        if dto.category:
            contact.category = dto.category
        if dto.phone:
            contact.phone = dto.phone
        if dto.country:
            contact.country = dto.country
        if dto.city:
            contact.city = dto.city
        if dto.linkedin_url:
            contact.linkedin_url = dto.linkedin_url
        if dto.facebook_url:
            contact.facebook_url = dto.facebook_url
        if dto.instagram_url:
            contact.instagram_url = dto.instagram_url
        if dto.twitter_url:
            contact.twitter_url = dto.twitter_url

        # Merge custom fields
        if dto.custom_fields:
            contact.custom_fields.update(dto.custom_fields)

        # Add new tags (don't remove existing ones)
        if dto.tags:
            for tag_str in dto.tags:
                tag_slug = TagSlug.from_string(tag_str)
                if tag_slug not in contact.tags:
                    contact.add_tag(tag_slug)

        contact.updated_at = datetime.utcnow()
