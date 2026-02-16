"""Enterprise multi-tenant architecture.

Revision ID: 003
Revises: 002
Create Date: 2026-02-16

Adds multi-tenant support with:
- tenants (SOS-Expat, Ulixai)
- data_sources (Scraper-Pro, Backlink Engine, CSV, API)
- contacts (prospects with tags, language, category)
- campaigns (multi-language campaigns)
- email_templates (9 languages + category-specific)
- tags (hierarchical tagging system)
- contact_tags (many-to-many)
- contact_events (audit trail for contacts)
- mailwizz_instances (2 instances: SOS-Expat, Ulixai)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # TENANTS - Isolation complète SOS-Expat / Ulixai
    # =========================================================================
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("brand_domain", sa.String(255), nullable=False),  # sos-expat.com
        sa.Column("sending_domain_base", sa.String(255), nullable=False),  # sos-mail.com
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )

    # =========================================================================
    # DATA SOURCES - Scraper-Pro, Backlink Engine, CSV, API
    # =========================================================================
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),  # scraper_pro, backlink_engine, csv, api
        sa.Column("config", sa.Text),  # JSON config
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("last_sync_at", sa.DateTime),
        sa.Column("total_contacts_ingested", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )

    # =========================================================================
    # TAGS - Hierarchical tagging system
    # =========================================================================
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("slug", sa.String(100), nullable=False, index=True),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("tags.id"), nullable=True),
        sa.Column("color", sa.String(7), server_default="#3B82F6"),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tenant_tag_slug"),
    )

    # =========================================================================
    # CONTACTS - Prospects avec tags, langue, catégorie
    # =========================================================================
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("data_source_id", sa.Integer, sa.ForeignKey("data_sources.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("company", sa.String(200)),
        sa.Column("website", sa.String(500)),
        sa.Column("language", sa.String(5), nullable=False, server_default="en"),  # ISO 639-1
        sa.Column("category", sa.String(50)),  # avocat, blogger, influencer, chatter, etc.
        sa.Column("phone", sa.String(30)),
        sa.Column("country", sa.String(2)),  # ISO 3166-1 alpha-2
        sa.Column("city", sa.String(100)),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("facebook_url", sa.String(500)),
        sa.Column("instagram_url", sa.String(500)),
        sa.Column("twitter_url", sa.String(500)),
        sa.Column("custom_fields", sa.Text),  # JSON pour champs custom
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),  # pending, valid, invalid, blacklisted, unsubscribed
        sa.Column("validation_status", sa.String(20)),  # valid, invalid, risky, unknown
        sa.Column("validation_score", sa.Float),
        sa.Column("validation_errors", sa.Text),  # JSON array
        sa.Column("mailwizz_subscriber_id", sa.Integer),
        sa.Column("mailwizz_list_id", sa.Integer),
        sa.Column("last_campaign_sent_at", sa.DateTime),
        sa.Column("total_campaigns_received", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime),
        sa.UniqueConstraint("tenant_id", "email", name="uq_tenant_contact_email"),
    )

    # =========================================================================
    # CONTACT_TAGS - Many-to-Many
    # =========================================================================
    op.create_table(
        "contact_tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("added_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("contact_id", "tag_id", name="uq_contact_tag"),
    )

    # =========================================================================
    # EMAIL TEMPLATES - 9 langues + catégorie
    # =========================================================================
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),  # fr, en, es, de, pt, ru, zh, hi, ar
        sa.Column("category", sa.String(50)),  # avocat, blogger, influencer, null = general
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text, nullable=False),
        sa.Column("body_text", sa.Text),
        sa.Column("variables", sa.Text),  # JSON array: ["firstName", "company", "website"]
        sa.Column("is_default", sa.Boolean, server_default="0"),
        sa.Column("total_sent", sa.Integer, server_default="0"),
        sa.Column("avg_open_rate", sa.Float, server_default="0"),
        sa.Column("avg_click_rate", sa.Float, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
        sa.UniqueConstraint("tenant_id", "name", "language", "category", name="uq_tenant_template"),
    )

    # =========================================================================
    # CAMPAIGNS - Campagnes multi-langue
    # =========================================================================
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),  # draft, scheduled, sending, sent, paused, cancelled
        sa.Column("template_id", sa.Integer, sa.ForeignKey("email_templates.id"), nullable=True),
        sa.Column("language", sa.String(5)),
        sa.Column("category", sa.String(50)),
        sa.Column("tags_all", sa.Text),  # JSON array - AND condition
        sa.Column("tags_any", sa.Text),  # JSON array - OR condition
        sa.Column("exclude_tags", sa.Text),  # JSON array
        sa.Column("total_recipients", sa.Integer, server_default="0"),
        sa.Column("sent_count", sa.Integer, server_default="0"),
        sa.Column("delivered_count", sa.Integer, server_default="0"),
        sa.Column("opened_count", sa.Integer, server_default="0"),
        sa.Column("clicked_count", sa.Integer, server_default="0"),
        sa.Column("bounced_count", sa.Integer, server_default="0"),
        sa.Column("unsubscribed_count", sa.Integer, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime),
        sa.Column("started_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("mailwizz_campaign_id", sa.Integer),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )

    # =========================================================================
    # CONTACT EVENTS - Audit trail
    # =========================================================================
    op.create_table(
        "contact_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id"), nullable=True, index=True),
        sa.Column("event_type", sa.String(30), nullable=False),  # ingested, validated, sent, delivered, opened, clicked, bounced, unsubscribed
        sa.Column("event_data", sa.Text),  # JSON
        sa.Column("timestamp", sa.DateTime, nullable=False, index=True),
    )

    # =========================================================================
    # MAILWIZZ INSTANCES - 2 instances (SOS-Expat, Ulixai)
    # =========================================================================
    op.create_table(
        "mailwizz_instances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("api_public_key", sa.String(255)),
        sa.Column("api_private_key", sa.String(255)),
        sa.Column("default_list_id", sa.Integer),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("last_health_check", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
    )

    # =========================================================================
    # ADD TENANT_ID to existing IPs and Domains tables
    # =========================================================================
    op.add_column("ips", sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True))
    op.add_column("domains", sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("domains", "tenant_id")
    op.drop_column("ips", "tenant_id")
    op.drop_table("mailwizz_instances")
    op.drop_table("contact_events")
    op.drop_table("campaigns")
    op.drop_table("email_templates")
    op.drop_table("contact_tags")
    op.drop_table("contacts")
    op.drop_table("tags")
    op.drop_table("data_sources")
    op.drop_table("tenants")
