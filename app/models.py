"""SQLAlchemy ORM models — Enterprise multi-tenant architecture."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# =============================================================================
# ENTERPRISE MULTI-TENANT MODELS (Added 2026-02-16)
# =============================================================================


class Tenant(Base):
    """Tenants - SOS-Expat, Ulixai (complete isolation)."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    brand_domain = Column(String(255), nullable=False)  # sos-expat.com
    sending_domain_base = Column(String(255), nullable=False)  # sos-mail.com
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    data_sources = relationship("DataSource", back_populates="tenant", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="tenant", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="tenant", cascade="all, delete-orphan")
    email_templates = relationship("EmailTemplate", back_populates="tenant", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="tenant", cascade="all, delete-orphan")
    mailwizz_instance = relationship("MailwizzInstance", back_populates="tenant", uselist=False)
    ips = relationship("IP", back_populates="tenant")
    domains = relationship("Domain", back_populates="tenant")


class DataSource(Base):
    """Data sources - Scraper-Pro, Backlink Engine, CSV, API."""

    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(30), nullable=False)  # scraper_pro, backlink_engine, csv, api
    config = Column(Text)  # JSON config
    is_active = Column(Boolean, nullable=False, default=True)
    last_sync_at = Column(DateTime)
    total_contacts_ingested = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="data_sources")
    contacts = relationship("Contact", back_populates="data_source")


class Tag(Base):
    """Tags - Hierarchical tagging system."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    slug = Column(String(100), nullable=False, index=True)
    label = Column(String(150), nullable=False)
    parent_id = Column(Integer, ForeignKey("tags.id"), nullable=True)
    color = Column(String(7), default="#3B82F6")
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_tenant_tag_slug"),)

    # Relationships
    tenant = relationship("Tenant", back_populates="tags")
    parent = relationship("Tag", remote_side=[id], backref="children")
    contact_tags = relationship("ContactTag", back_populates="tag", cascade="all, delete-orphan")


class Contact(Base):
    """Contacts - Prospects with tags, language, category."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))
    website = Column(String(500))
    language = Column(String(5), nullable=False, default="en")  # ISO 639-1
    category = Column(String(50))  # avocat, blogger, influencer, chatter, etc.
    phone = Column(String(30))
    country = Column(String(2))  # ISO 3166-1 alpha-2
    city = Column(String(100))
    linkedin_url = Column(String(500))
    facebook_url = Column(String(500))
    instagram_url = Column(String(500))
    twitter_url = Column(String(500))
    custom_fields = Column(Text)  # JSON
    status = Column(String(20), nullable=False, default="pending")  # pending, valid, invalid, blacklisted, unsubscribed
    validation_status = Column(String(20))  # valid, invalid, risky, unknown
    validation_score = Column(Float)
    validation_errors = Column(Text)  # JSON array
    mailwizz_subscriber_id = Column(Integer)
    mailwizz_list_id = Column(Integer)
    last_campaign_sent_at = Column(DateTime)
    total_campaigns_received = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_tenant_contact_email"),)

    # Relationships
    tenant = relationship("Tenant", back_populates="contacts")
    data_source = relationship("DataSource", back_populates="contacts")
    contact_tags = relationship("ContactTag", back_populates="contact", cascade="all, delete-orphan")
    events = relationship("ContactEvent", back_populates="contact", cascade="all, delete-orphan")


class ContactTag(Base):
    """Contact-Tag Many-to-Many relationship."""

    __tablename__ = "contact_tags"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("contact_id", "tag_id", name="uq_contact_tag"),)

    # Relationships
    contact = relationship("Contact", back_populates="contact_tags")
    tag = relationship("Tag", back_populates="contact_tags")


class EmailTemplate(Base):
    """Email templates - 9 languages + category-specific."""

    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    language = Column(String(5), nullable=False)  # fr, en, es, de, pt, ru, zh, hi, ar
    category = Column(String(50))  # avocat, blogger, influencer, null = general
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text)
    variables = Column(Text)  # JSON array: ["firstName", "company", "website"]
    is_default = Column(Boolean, default=False)
    total_sent = Column(Integer, default=0)
    avg_open_rate = Column(Float, default=0.0)
    avg_click_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", "language", "category", name="uq_tenant_template"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="email_templates")
    campaigns = relationship("Campaign", back_populates="template")


class Campaign(Base):
    """Campaigns - Multi-language campaigns."""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="draft")  # draft, scheduled, sending, sent, paused, cancelled
    template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    language = Column(String(5))
    category = Column(String(50))
    tags_all = Column(Text)  # JSON array - AND condition
    tags_any = Column(Text)  # JSON array - OR condition
    exclude_tags = Column(Text)  # JSON array
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    unsubscribed_count = Column(Integer, default=0)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    mailwizz_campaign_id = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="campaigns")
    template = relationship("EmailTemplate", back_populates="campaigns")
    events = relationship("ContactEvent", back_populates="campaign")


class ContactEvent(Base):
    """Contact events - Audit trail for contacts."""

    __tablename__ = "contact_events"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    event_type = Column(String(30), nullable=False)  # ingested, validated, sent, delivered, opened, clicked, bounced, unsubscribed
    event_data = Column(Text)  # JSON
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    contact = relationship("Contact", back_populates="events")
    campaign = relationship("Campaign", back_populates="events")


class MailwizzInstance(Base):
    """MailWizz instances - 2 instances (SOS-Expat, Ulixai)."""

    __tablename__ = "mailwizz_instances"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_public_key = Column(String(255))
    api_private_key = Column(String(255))
    default_list_id = Column(Integer)
    is_active = Column(Boolean, nullable=False, default=True)
    last_health_check = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="mailwizz_instance")


# =============================================================================
# EXISTING MODELS (Updated with tenant relationship)
# =============================================================================


class IP(Base):
    __tablename__ = "ips"

    id = Column(Integer, primary_key=True)
    address = Column(String(45), unique=True, nullable=False)
    hostname = Column(String(255), nullable=False)
    purpose = Column(String(20), nullable=False, default="marketing")
    status = Column(String(20), nullable=False, default="standby")
    weight = Column(Integer, nullable=False, default=100)
    vmta_name = Column(String(100))
    pool_name = Column(String(100))
    mailwizz_server_id = Column(Integer)
    quarantine_until = Column(DateTime)
    blacklisted_on = Column(Text, default="[]")  # JSON array
    status_changed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)  # Added 2026-02-16

    domains = relationship("Domain", back_populates="ip")
    warmup_plan = relationship("WarmupPlan", back_populates="ip", uselist=False)
    blacklist_events = relationship(
        "BlacklistEvent", back_populates="ip", foreign_keys="[BlacklistEvent.ip_id]"
    )
    tenant = relationship("Tenant", back_populates="ips")  # Added 2026-02-16


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    purpose = Column(String(20), nullable=False, default="marketing")
    ip_id = Column(Integer, ForeignKey("ips.id"), nullable=True)
    dkim_selector = Column(String(63), default="default")
    dkim_key_path = Column(String(500))
    spf_valid = Column(Boolean, default=False)
    dkim_valid = Column(Boolean, default=False)
    dmarc_valid = Column(Boolean, default=False)
    ptr_valid = Column(Boolean, default=False)
    last_dns_check = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)  # Added 2026-02-16

    ip = relationship("IP", back_populates="domains")
    tenant = relationship("Tenant", back_populates="domains")  # Added 2026-02-16


class WarmupPlan(Base):
    __tablename__ = "warmup_plans"

    id = Column(Integer, primary_key=True)
    ip_id = Column(Integer, ForeignKey("ips.id"), unique=True, nullable=False)
    phase = Column(String(20), nullable=False, default="week_1")
    started_at = Column(DateTime, default=datetime.utcnow)
    current_daily_quota = Column(Integer, nullable=False, default=50)
    target_daily_quota = Column(Integer, nullable=False, default=10000)
    bounce_rate_7d = Column(Float, default=0.0)
    spam_rate_7d = Column(Float, default=0.0)
    paused = Column(Boolean, default=False)
    pause_until = Column(DateTime)

    ip = relationship("IP", back_populates="warmup_plan")
    daily_stats = relationship("WarmupDailyStat", back_populates="plan")


class WarmupDailyStat(Base):
    __tablename__ = "warmup_daily_stats"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("warmup_plans.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    sent = Column(Integer, default=0)
    delivered = Column(Integer, default=0)
    bounced = Column(Integer, default=0)
    complaints = Column(Integer, default=0)
    opens = Column(Integer, default=0)
    clicks = Column(Integer, default=0)

    plan = relationship("WarmupPlan", back_populates="daily_stats")

    __table_args__ = (UniqueConstraint("plan_id", "date", name="uq_plan_date"),)


class BlacklistEvent(Base):
    __tablename__ = "blacklist_events"

    id = Column(Integer, primary_key=True)
    ip_id = Column(Integer, ForeignKey("ips.id"), nullable=False)
    blacklist_name = Column(String(100), nullable=False)
    listed_at = Column(DateTime, default=datetime.utcnow)
    delisted_at = Column(DateTime)
    auto_recovered = Column(Boolean, default=False)
    standby_ip_activated_id = Column(Integer, ForeignKey("ips.id"))

    ip = relationship("IP", back_populates="blacklist_events", foreign_keys=[ip_id])


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    pmta_running = Column(Boolean, nullable=False)
    pmta_queue_size = Column(Integer, default=0)
    disk_usage_pct = Column(Float, default=0.0)
    ram_usage_pct = Column(Float, default=0.0)


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    severity = Column(String(20), nullable=False)
    category = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    telegram_sent = Column(Boolean, default=False)


class User(Base):
    """User accounts for JWT authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # user, admin
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)

    audit_logs = relationship("AuditLog", back_populates="user")


class APIKey(Base):
    """API keys for rotation and multi-key support."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # human-readable identifier
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime)


class AuditLog(Base):
    """Audit trail for compliance (who did what when)."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = system action
    action = Column(String(50), nullable=False)  # create_ip, delete_domain, etc.
    resource_type = Column(String(50), nullable=False)  # ip, domain, warmup_plan, etc.
    resource_id = Column(Integer, nullable=True)  # FK to resource
    details = Column(Text)  # JSON with additional context
    ip_address = Column(String(45))  # client IP
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
