"""Enumerations for the email engine."""

import enum


class IPStatus(str, enum.Enum):
    ACTIVE = "active"
    RETIRING = "retiring"
    RESTING = "resting"
    WARMING = "warming"
    BLACKLISTED = "blacklisted"
    STANDBY = "standby"


class IPPurpose(str, enum.Enum):
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    COLD = "cold"
    STANDBY = "standby"


class WarmupPhase(str, enum.Enum):
    WEEK_1 = "week_1"
    WEEK_2 = "week_2"
    WEEK_3 = "week_3"
    WEEK_4 = "week_4"
    WEEK_5 = "week_5"
    WEEK_6 = "week_6"
    COMPLETED = "completed"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(str, enum.Enum):
    BLACKLIST = "blacklist"
    HEALTH = "health"
    WARMUP = "warmup"
    ROTATION = "rotation"
    DNS = "dns"
    BOUNCE = "bounce"


class BounceType(str, enum.Enum):
    HARD = "hard"
    SOFT = "soft"
    COMPLAINT = "complaint"


class UserRole(str, enum.Enum):
    """User roles for RBAC."""

    USER = "user"
    ADMIN = "admin"


# =============================================================================
# ENTERPRISE MULTI-TENANT ENUMS (Added 2026-02-16)
# =============================================================================


class DataSourceType(str, enum.Enum):
    """Data source types."""

    SCRAPER_PRO = "scraper_pro"
    BACKLINK_ENGINE = "backlink_engine"
    CSV_IMPORT = "csv"
    API_WEBHOOK = "api"
    MANUAL = "manual"


class ContactStatus(str, enum.Enum):
    """Contact status."""

    PENDING = "pending"  # Just ingested, not yet validated
    VALID = "valid"  # Email validated, ready for campaigns
    INVALID = "invalid"  # Email validation failed
    BLACKLISTED = "blacklisted"  # On suppression list
    UNSUBSCRIBED = "unsubscribed"  # User unsubscribed


class ValidationStatus(str, enum.Enum):
    """Email validation status."""

    VALID = "valid"  # Deliverable
    INVALID = "invalid"  # Undeliverable
    RISKY = "risky"  # Accept-all, catch-all
    UNKNOWN = "unknown"  # Cannot determine


class CampaignStatus(str, enum.Enum):
    """Campaign status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class EventType(str, enum.Enum):
    """Contact event types."""

    INGESTED = "ingested"
    VALIDATED = "validated"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    COMPLAINED = "complained"


class Language(str, enum.Enum):
    """Supported languages (9 + fallback)."""

    FRENCH = "fr"
    ENGLISH = "en"
    SPANISH = "es"
    GERMAN = "de"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    CHINESE = "zh"
    HINDI = "hi"
    ARABIC = "ar"


class ProspectCategory(str, enum.Enum):
    """SOS-Expat prospect categories."""

    # Prestataires
    AVOCAT = "avocat"
    EXPAT_AIDANT = "expat_aidant"

    # Marketing Partners
    BLOGGER = "blogger"
    INFLUENCER = "influencer"
    CHATTER = "chatter"
    ADMIN_GROUP = "admin_group"

    # Clients (grouped)
    CLIENT = "client"  # Vacanciers, Expats, Digital Nomades
