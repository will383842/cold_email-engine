"""Add tenant_id to WarmupPlan, ContactEvent, BlacklistEvent for isolation.

Revision ID: 005
Revises: 004
Create Date: 2026-02-20

Changes (CRITICAL tenant isolation):
- warmup_plans.tenant_id     : FK to tenants (backfilled from ips.tenant_id)
- contact_events.tenant_id    : FK to tenants (backfilled from contacts.tenant_id)
- blacklist_events.tenant_id  : FK to tenants (backfilled from ips.tenant_id)

All with indexes for query performance + NOT NULL constraint after backfill.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═════════════════════════════════════════════════════════════════════════
    # Table: warmup_plans — Ajout tenant_id (CRITICAL)
    # ═════════════════════════════════════════════════════════════════════════

    # 1. Ajout colonne tenant_id (nullable temporairement pour backfill)
    op.add_column(
        "warmup_plans",
        sa.Column(
            "tenant_id",
            sa.Integer,
            nullable=True,
            comment="Tenant owner (isolation critique)",
        ),
    )

    # 2. Backfill tenant_id depuis ips.tenant_id via warmup_plans.ip_id
    op.execute("""
        UPDATE warmup_plans
        SET tenant_id = ips.tenant_id
        FROM ips
        WHERE warmup_plans.ip_id = ips.id
    """)

    # 3. Rendre NOT NULL après backfill (garantit pas de plans orphelins)
    op.alter_column(
        "warmup_plans",
        "tenant_id",
        nullable=False,
    )

    # 4. Ajouter FK constraint vers tenants
    op.create_foreign_key(
        "fk_warmup_plans_tenant_id",
        "warmup_plans",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Index pour filtrage rapide par tenant (GET /warmup-plans?tenant_id=X)
    op.create_index(
        "ix_warmup_plans_tenant_id",
        "warmup_plans",
        ["tenant_id"],
        unique=False,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # Table: contact_events — Ajout tenant_id (RECOMMENDED performance)
    # ═════════════════════════════════════════════════════════════════════════

    # 1. Ajout colonne tenant_id (nullable temporairement)
    op.add_column(
        "contact_events",
        sa.Column(
            "tenant_id",
            sa.Integer,
            nullable=True,
            comment="Tenant owner (denormalisé pour queries rapides)",
        ),
    )

    # 2. Backfill depuis contacts.tenant_id via contact_events.contact_id
    op.execute("""
        UPDATE contact_events
        SET tenant_id = contacts.tenant_id
        FROM contacts
        WHERE contact_events.contact_id = contacts.id
    """)

    # 3. Rendre NOT NULL après backfill
    op.alter_column(
        "contact_events",
        "tenant_id",
        nullable=False,
    )

    # 4. FK constraint
    op.create_foreign_key(
        "fk_contact_events_tenant_id",
        "contact_events",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Index composé (tenant_id, event_type) pour analytics par tenant
    op.create_index(
        "ix_contact_events_tenant_event",
        "contact_events",
        ["tenant_id", "event_type"],
        unique=False,
    )

    # ═════════════════════════════════════════════════════════════════════════
    # Table: blacklist_events — Ajout tenant_id (RECOMMENDED performance)
    # ═════════════════════════════════════════════════════════════════════════

    # 1. Ajout colonne tenant_id (nullable temporairement)
    op.add_column(
        "blacklist_events",
        sa.Column(
            "tenant_id",
            sa.Integer,
            nullable=True,
            comment="Tenant owner (denormalisé pour queries rapides)",
        ),
    )

    # 2. Backfill depuis ips.tenant_id via blacklist_events.ip_id
    op.execute("""
        UPDATE blacklist_events
        SET tenant_id = ips.tenant_id
        FROM ips
        WHERE blacklist_events.ip_id = ips.id
    """)

    # 3. Rendre NOT NULL après backfill
    op.alter_column(
        "blacklist_events",
        "tenant_id",
        nullable=False,
    )

    # 4. FK constraint
    op.create_foreign_key(
        "fk_blacklist_events_tenant_id",
        "blacklist_events",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Index pour filtrage rapide par tenant
    op.create_index(
        "ix_blacklist_events_tenant_id",
        "blacklist_events",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    """Rollback tenant isolation (retrait tenant_id des 3 tables)."""

    # blacklist_events
    op.drop_index("ix_blacklist_events_tenant_id", table_name="blacklist_events")
    op.drop_constraint("fk_blacklist_events_tenant_id", "blacklist_events", type_="foreignkey")
    op.drop_column("blacklist_events", "tenant_id")

    # contact_events
    op.drop_index("ix_contact_events_tenant_event", table_name="contact_events")
    op.drop_constraint("fk_contact_events_tenant_id", "contact_events", type_="foreignkey")
    op.drop_column("contact_events", "tenant_id")

    # warmup_plans
    op.drop_index("ix_warmup_plans_tenant_id", table_name="warmup_plans")
    op.drop_constraint("fk_warmup_plans_tenant_id", "warmup_plans", type_="foreignkey")
    op.drop_column("warmup_plans", "tenant_id")
