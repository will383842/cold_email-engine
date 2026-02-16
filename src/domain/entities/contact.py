"""Contact Entity - Domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.enums import ContactStatus, ValidationStatus
from src.domain.value_objects import Email, Language, TagSlug


@dataclass
class Contact:
    """Contact aggregate - central domain entity."""

    # Identity
    id: Optional[int] = None
    tenant_id: int = 0
    data_source_id: int = 0

    # Value Objects
    email: Email = field(default_factory=lambda: Email("default@example.com"))
    language: Language = field(default_factory=lambda: Language("en"))

    # Attributes
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None  # avocat, blogger, etc.
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

    # Social
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None

    # Custom fields (JSON)
    custom_fields: dict = field(default_factory=dict)

    # Status
    status: ContactStatus = ContactStatus.PENDING
    validation_status: Optional[ValidationStatus] = None
    validation_score: Optional[float] = None
    validation_errors: list[str] = field(default_factory=list)

    # Tags
    tags: list[TagSlug] = field(default_factory=list)

    # MailWizz integration
    mailwizz_subscriber_id: Optional[int] = None
    mailwizz_list_id: Optional[int] = None

    # Metrics
    last_campaign_sent_at: Optional[datetime] = None
    total_campaigns_received: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # =========================================================================
    # Business Methods
    # =========================================================================

    def validate(self, validation_status: ValidationStatus, score: float) -> None:
        """Mark contact as validated."""
        self.validation_status = validation_status
        self.validation_score = score
        self.updated_at = datetime.utcnow()

        # Update contact status based on validation
        if validation_status == ValidationStatus.VALID:
            self.status = ContactStatus.VALID
        elif validation_status == ValidationStatus.INVALID:
            self.status = ContactStatus.INVALID

    def add_tag(self, tag: TagSlug) -> None:
        """Add tag to contact."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag: TagSlug) -> None:
        """Remove tag from contact."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()

    def unsubscribe(self) -> None:
        """Unsubscribe contact."""
        self.status = ContactStatus.UNSUBSCRIBED
        self.updated_at = datetime.utcnow()

    def blacklist(self) -> None:
        """Blacklist contact."""
        self.status = ContactStatus.BLACKLISTED
        self.updated_at = datetime.utcnow()

    def record_campaign_sent(self) -> None:
        """Record that a campaign was sent to this contact."""
        self.last_campaign_sent_at = datetime.utcnow()
        self.total_campaigns_received += 1
        self.updated_at = datetime.utcnow()

    def full_name(self) -> str:
        """Get full name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else "Unknown"

    def is_eligible_for_campaign(self) -> bool:
        """Check if contact can receive campaigns."""
        return self.status == ContactStatus.VALID

    def __repr__(self) -> str:
        return f"<Contact id={self.id} email={self.email} status={self.status.value}>"
