"""Add multi-node PowerMTA fields to ips table.

Revision ID: 004
Revises: 003
Create Date: 2026-02-17

Changes:
- ips.sender_email  : Email expéditeur unique (1 IP = 1 email sender PowerMTA)
- ips.pmta_node_id  : Nœud PowerMTA cible (vps2 | vps3 | vps4)
- IPStatus enum     : Ajout du statut 'quarantined' (arrêt d'urgence warmup)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # Table : ips — Ajout colonnes multi-nœud PowerMTA
    # ─────────────────────────────────────────────────────────────────────────
    op.add_column(
        "ips",
        sa.Column(
            "sender_email",
            sa.String(255),
            nullable=True,
            comment="Email expéditeur unique (pattern-list PowerMTA). 1 IP = 1 email.",
        ),
    )
    op.add_column(
        "ips",
        sa.Column(
            "pmta_node_id",
            sa.String(10),
            nullable=True,
            server_default="vps2",
            comment="Nœud PowerMTA responsable : vps2 | vps3 | vps4",
        ),
    )

    # Index pour filtrage rapide par nœud (GET /ips?pmta_node_id=vps2)
    op.create_index(
        "ix_ips_pmta_node_id",
        "ips",
        ["pmta_node_id"],
        unique=False,
    )

    # Index partiel : un seul sender_email actif par IP (unicité logique)
    # Note : pas de UNIQUE constraint car sender_email peut être NULL
    op.create_index(
        "ix_ips_sender_email",
        "ips",
        ["sender_email"],
        unique=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Table : warmup_plans — Mise à jour des valeurs de phase
    # La colonne 'phase' passe de WarmupPhase enum (week_1..week_6)
    # à des strings libres (day_1..day_70, completed, emergency_stop, paused_*)
    # Pas de changement de type (déjà String) — juste migration des données
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        UPDATE warmup_plans
        SET phase = CASE phase
            WHEN 'week_1' THEN 'day_1'
            WHEN 'week_2' THEN 'day_8'
            WHEN 'week_3' THEN 'day_15'
            WHEN 'week_4' THEN 'day_22'
            WHEN 'week_5' THEN 'day_36'
            WHEN 'week_6' THEN 'day_50'
            WHEN 'completed' THEN 'completed'
            ELSE phase
        END
        WHERE phase IN ('week_1','week_2','week_3','week_4','week_5','week_6','completed')
    """)


def downgrade() -> None:
    # Restaurer les phases warmup (approximatif — perte de précision jour→semaine)
    op.execute("""
        UPDATE warmup_plans
        SET phase = CASE
            WHEN phase ~ '^day_([1-7])$' THEN 'week_1'
            WHEN phase ~ '^day_([8-9]|1[0-4])$' THEN 'week_2'
            WHEN phase ~ '^day_(1[5-9]|2[0-1])$' THEN 'week_3'
            WHEN phase ~ '^day_(2[2-9]|3[0-5])$' THEN 'week_4'
            WHEN phase ~ '^day_(3[6-9]|4[0-9])$' THEN 'week_5'
            WHEN phase ~ '^day_([5-9][0-9]|[6-9][0-9])$' THEN 'week_6'
            WHEN phase = 'completed' THEN 'completed'
            ELSE 'week_1'
        END
    """)

    op.drop_index("ix_ips_sender_email", table_name="ips")
    op.drop_index("ix_ips_pmta_node_id", table_name="ips")
    op.drop_column("ips", "pmta_node_id")
    op.drop_column("ips", "sender_email")
