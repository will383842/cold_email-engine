"""Tests for warmup engine."""

import pytest

from app.enums import WarmupPhase
from app.models import IP, WarmupPlan
from app.services.warmup_engine import WarmupEngine


def _make_ip(db, status="warming"):
    ip = IP(address="1.2.3.4", hostname="mail.test.com", status=status, purpose="marketing")
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return ip


def test_create_plan(db):
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    assert plan.phase == WarmupPhase.WEEK_1.value
    assert plan.current_daily_quota == 50
    assert plan.ip_id == ip.id


def test_record_daily_stats(db):
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    stat = engine.record_daily_stats(plan, sent=40, delivered=38, bounced=2, complaints=0)
    assert stat.sent == 40
    assert stat.bounced == 2


@pytest.mark.asyncio
async def test_safety_check_passes(db):
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    # No stats yet, rates should be 0 → safe
    assert await engine.check_safety(plan) is True


@pytest.mark.asyncio
async def test_safety_check_pauses_on_high_bounce(db):
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    # Record stats with high bounce
    engine.record_daily_stats(plan, sent=100, delivered=80, bounced=20, complaints=0)
    safe = await engine.check_safety(plan)
    assert safe is False
    assert plan.paused is True


def test_next_phase_progression(db):
    engine = WarmupEngine(db)
    assert engine._next_phase(WarmupPhase.WEEK_1) == WarmupPhase.WEEK_2
    assert engine._next_phase(WarmupPhase.WEEK_6) == WarmupPhase.COMPLETED
    assert engine._next_phase(WarmupPhase.COMPLETED) == WarmupPhase.COMPLETED
