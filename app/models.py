"""SQLAlchemy ORM models — 7 tables."""

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

    domains = relationship("Domain", back_populates="ip")
    warmup_plan = relationship("WarmupPlan", back_populates="ip", uselist=False)
    blacklist_events = relationship(
        "BlacklistEvent", back_populates="ip", foreign_keys="[BlacklistEvent.ip_id]"
    )


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

    ip = relationship("IP", back_populates="domains")


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
