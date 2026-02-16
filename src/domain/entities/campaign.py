"""Campaign Entity - Domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.enums import CampaignStatus
from src.domain.value_objects import Language, TagSlug


@dataclass
class Campaign:
    """Campaign aggregate."""

    # Identity
    id: Optional[int] = None
    tenant_id: int = 0

    # Attributes
    name: str = ""
    status: CampaignStatus = CampaignStatus.DRAFT
    template_id: Optional[int] = None
    language: Optional[Language] = None
    category: Optional[str] = None

    # Tag-based segmentation
    tags_all: list[TagSlug] = field(default_factory=list)  # AND condition
    tags_any: list[TagSlug] = field(default_factory=list)  # OR condition
    exclude_tags: list[TagSlug] = field(default_factory=list)

    # Metrics
    total_recipients: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    bounced_count: int = 0
    unsubscribed_count: int = 0

    # Timestamps
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # MailWizz integration
    mailwizz_campaign_id: Optional[int] = None

    # =========================================================================
    # Business Methods
    # =========================================================================

    def schedule(self, scheduled_at: datetime) -> None:
        """Schedule campaign for future sending."""
        if self.status != CampaignStatus.DRAFT:
            raise ValueError("Can only schedule draft campaigns")
        self.status = CampaignStatus.SCHEDULED
        self.scheduled_at = scheduled_at
        self.updated_at = datetime.utcnow()

    def start(self) -> None:
        """Start sending campaign."""
        if self.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            raise ValueError("Can only start draft or scheduled campaigns")
        self.status = CampaignStatus.SENDING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark campaign as completed."""
        if self.status != CampaignStatus.SENDING:
            raise ValueError("Can only complete sending campaigns")
        self.status = CampaignStatus.SENT
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def pause(self) -> None:
        """Pause campaign."""
        if self.status != CampaignStatus.SENDING:
            raise ValueError("Can only pause sending campaigns")
        self.status = CampaignStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel campaign."""
        if self.status in [CampaignStatus.SENT, CampaignStatus.CANCELLED]:
            raise ValueError("Cannot cancel sent or already cancelled campaigns")
        self.status = CampaignStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def record_sent(self) -> None:
        """Record email sent."""
        self.sent_count += 1
        self.updated_at = datetime.utcnow()

    def record_delivered(self) -> None:
        """Record email delivered."""
        self.delivered_count += 1
        self.updated_at = datetime.utcnow()

    def record_opened(self) -> None:
        """Record email opened."""
        self.opened_count += 1
        self.updated_at = datetime.utcnow()

    def record_clicked(self) -> None:
        """Record email clicked."""
        self.clicked_count += 1
        self.updated_at = datetime.utcnow()

    def record_bounced(self) -> None:
        """Record email bounced."""
        self.bounced_count += 1
        self.updated_at = datetime.utcnow()

    def record_unsubscribed(self) -> None:
        """Record unsubscribe."""
        self.unsubscribed_count += 1
        self.updated_at = datetime.utcnow()

    def open_rate(self) -> float:
        """Calculate open rate."""
        if self.delivered_count == 0:
            return 0.0
        return (self.opened_count / self.delivered_count) * 100

    def click_rate(self) -> float:
        """Calculate click rate."""
        if self.delivered_count == 0:
            return 0.0
        return (self.clicked_count / self.delivered_count) * 100

    def bounce_rate(self) -> float:
        """Calculate bounce rate."""
        if self.sent_count == 0:
            return 0.0
        return (self.bounced_count / self.sent_count) * 100

    def __repr__(self) -> str:
        return f"<Campaign id={self.id} name={self.name} status={self.status.value}>"
