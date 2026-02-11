"""Initial schema — 7 tables.

Revision ID: 001
Revises:
Create Date: 2026-02-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ips",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("address", sa.String(45), unique=True, nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="marketing"),
        sa.Column("status", sa.String(20), nullable=False, server_default="standby"),
        sa.Column("weight", sa.Integer, nullable=False, server_default="100"),
        sa.Column("vmta_name", sa.String(100)),
        sa.Column("pool_name", sa.String(100)),
        sa.Column("mailwizz_server_id", sa.Integer),
        sa.Column("quarantine_until", sa.DateTime),
        sa.Column("blacklisted_on", sa.Text, server_default="[]"),
        sa.Column("status_changed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "domains",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="marketing"),
        sa.Column("ip_id", sa.Integer, sa.ForeignKey("ips.id")),
        sa.Column("dkim_selector", sa.String(63), server_default="default"),
        sa.Column("dkim_key_path", sa.String(500)),
        sa.Column("spf_valid", sa.Boolean, server_default="0"),
        sa.Column("dkim_valid", sa.Boolean, server_default="0"),
        sa.Column("dmarc_valid", sa.Boolean, server_default="0"),
        sa.Column("ptr_valid", sa.Boolean, server_default="0"),
        sa.Column("last_dns_check", sa.DateTime),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "warmup_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ip_id", sa.Integer, sa.ForeignKey("ips.id"), unique=True, nullable=False),
        sa.Column("phase", sa.String(20), nullable=False, server_default="week_1"),
        sa.Column("started_at", sa.DateTime),
        sa.Column("current_daily_quota", sa.Integer, nullable=False, server_default="50"),
        sa.Column("target_daily_quota", sa.Integer, nullable=False, server_default="10000"),
        sa.Column("bounce_rate_7d", sa.Float, server_default="0"),
        sa.Column("spam_rate_7d", sa.Float, server_default="0"),
        sa.Column("paused", sa.Boolean, server_default="0"),
        sa.Column("pause_until", sa.DateTime),
    )

    op.create_table(
        "warmup_daily_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("warmup_plans.id"), nullable=False),
        sa.Column("date", sa.DateTime, nullable=False),
        sa.Column("sent", sa.Integer, server_default="0"),
        sa.Column("delivered", sa.Integer, server_default="0"),
        sa.Column("bounced", sa.Integer, server_default="0"),
        sa.Column("complaints", sa.Integer, server_default="0"),
        sa.Column("opens", sa.Integer, server_default="0"),
        sa.Column("clicks", sa.Integer, server_default="0"),
        sa.UniqueConstraint("plan_id", "date", name="uq_plan_date"),
    )

    op.create_table(
        "blacklist_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ip_id", sa.Integer, sa.ForeignKey("ips.id"), nullable=False),
        sa.Column("blacklist_name", sa.String(100), nullable=False),
        sa.Column("listed_at", sa.DateTime),
        sa.Column("delisted_at", sa.DateTime),
        sa.Column("auto_recovered", sa.Boolean, server_default="0"),
        sa.Column("standby_ip_activated_id", sa.Integer, sa.ForeignKey("ips.id")),
    )

    op.create_table(
        "health_checks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("pmta_running", sa.Boolean, nullable=False),
        sa.Column("pmta_queue_size", sa.Integer, server_default="0"),
        sa.Column("disk_usage_pct", sa.Float, server_default="0"),
        sa.Column("ram_usage_pct", sa.Float, server_default="0"),
    )

    op.create_table(
        "alert_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("telegram_sent", sa.Boolean, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("alert_logs")
    op.drop_table("health_checks")
    op.drop_table("blacklist_events")
    op.drop_table("warmup_daily_stats")
    op.drop_table("warmup_plans")
    op.drop_table("domains")
    op.drop_table("ips")
