"""Tests for warmup engine — day-based progression (70 days / 10 weeks).

Tests couverts :
  - DAILY_QUOTAS : structure, monotonie, valeurs de fin de semaine
  - get_quota_for_day() : cas limites (0, négatif, > 70)
  - daily_to_hourly_quota() : formule et plancher
  - WarmupEngine.create_plan() : état initial correct
  - WarmupEngine.record_daily_stats() : création + upsert
  - WarmupEngine.check_safety() : 4 scénarios (OK, bounce, spam, urgence)
  - WarmupEngine._get_day_number() : avec et sans stats
  - WarmupEngine.get_status() : résumé complet
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.models import IP, Tenant, WarmupDailyStat, WarmupPlan
from app.services.warmup_engine import (
    DAILY_QUOTAS,
    WARMUP_TOTAL_DAYS,
    WarmupEngine,
    daily_to_hourly_quota,
    get_quota_for_day,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_tenant(db, slug="test-tenant"):
    """Crée un tenant de test."""
    tenant = Tenant(
        slug=slug,
        name="Test Tenant",
        brand_domain="test.com",
        sending_domain_base="mail.test.com",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _make_ip(db, status="warming", tenant=None):
    """Crée une IP de test. Si tenant non fourni, en crée un."""
    if tenant is None:
        tenant = _make_tenant(db)

    ip = IP(
        tenant_id=tenant.id,
        address="1.2.3.4",
        hostname="mail.test.com",
        status=status,
        purpose="marketing",
    )
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return ip


def _add_stats(db, plan, n_days: int, bounced_pct: float = 0.0, complaints_pct: float = 0.0):
    """Ajoute N jours de stats à un plan warmup (répartis dans le passé).

    Utilise sent=1000 et round() pour éviter la troncature entière sur les
    petits pourcentages (ex: int(100 * 0.5 / 100) = 0 au lieu de 0.5).
    Utilisé principalement pour les tests de _get_day_number().
    """
    base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(n_days):
        sent = 1000
        bounced = round(sent * bounced_pct / 100)
        complaints = round(sent * complaints_pct / 100)
        stat = WarmupDailyStat(
            plan_id=plan.id,
            date=base - timedelta(days=n_days - 1 - i),
            sent=sent,
            delivered=max(0, sent - bounced - complaints),
            bounced=bounced,
            complaints=complaints,
            opens=0,
            clicks=0,
        )
        db.add(stat)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# DAILY_QUOTAS — structure
# ─────────────────────────────────────────────────────────────────────────────

def test_daily_quotas_length():
    """La liste doit contenir exactement 70 valeurs (10 semaines × 7 jours)."""
    assert len(DAILY_QUOTAS) == 70
    assert WARMUP_TOTAL_DAYS == 70


def test_daily_quotas_boundaries():
    """Démarre à 5 emails/jour et atteint 20 000 au jour 70."""
    assert DAILY_QUOTAS[0] == 5
    assert DAILY_QUOTAS[-1] == 20_000


def test_daily_quotas_monotonic():
    """Chaque jour doit avoir un quota strictement supérieur au précédent."""
    for i in range(1, len(DAILY_QUOTAS)):
        assert DAILY_QUOTAS[i] > DAILY_QUOTAS[i - 1], (
            f"Jour {i + 1} ({DAILY_QUOTAS[i]}) ≤ jour {i} ({DAILY_QUOTAS[i - 1]})"
        )


def test_daily_quotas_end_of_week_targets():
    """Cibles de fin de semaine conformes aux specs (index 0-based = jour - 1)."""
    assert DAILY_QUOTAS[6] == 20      # Fin semaine 1  → max 20/j
    assert DAILY_QUOTAS[13] == 50     # Fin semaine 2  → max 50/j
    assert DAILY_QUOTAS[20] == 110    # Fin semaine 3  → max 110/j
    assert DAILY_QUOTAS[27] == 250    # Fin semaine 4  → max 250/j
    assert DAILY_QUOTAS[34] == 550    # Fin semaine 5  → max 550/j
    assert DAILY_QUOTAS[41] == 1_200  # Fin semaine 6  → max 1200/j
    assert DAILY_QUOTAS[48] == 2_600  # Fin semaine 7  → max 2600/j
    assert DAILY_QUOTAS[55] == 5_500  # Fin semaine 8  → max 5500/j
    assert DAILY_QUOTAS[62] == 10_000 # Fin semaine 9  → max 10000/j
    assert DAILY_QUOTAS[69] == 20_000 # Fin semaine 10 → max 20000/j


# ─────────────────────────────────────────────────────────────────────────────
# get_quota_for_day()
# ─────────────────────────────────────────────────────────────────────────────

def test_get_quota_for_day_first():
    assert get_quota_for_day(1) == 5


def test_get_quota_for_day_last():
    assert get_quota_for_day(70) == 20_000


def test_get_quota_for_day_mid():
    assert get_quota_for_day(7) == 20    # Fin semaine 1
    assert get_quota_for_day(14) == 50   # Fin semaine 2
    assert get_quota_for_day(35) == 550  # Fin semaine 5


def test_get_quota_for_day_zero_clamped():
    """Jour 0 ou négatif → retourne le premier quota (plancher)."""
    assert get_quota_for_day(0) == 5
    assert get_quota_for_day(-10) == 5


def test_get_quota_for_day_over_70_clamped():
    """Jour > 70 → retourne le dernier quota (IP mature)."""
    assert get_quota_for_day(71) == 20_000
    assert get_quota_for_day(1000) == 20_000


# ─────────────────────────────────────────────────────────────────────────────
# daily_to_hourly_quota()
# ─────────────────────────────────────────────────────────────────────────────

def test_hourly_quota_formula():
    """Formule : max(1, int(daily / 16 * 0.8))."""
    # 5 / 16 * 0.8 = 0.25 → int = 0 → max(1, 0) = 1
    assert daily_to_hourly_quota(5) == 1
    # 50 / 16 * 0.8 = 2.5 → int = 2
    assert daily_to_hourly_quota(50) == 2
    # 1000 / 16 * 0.8 = 50.0 → int = 50
    assert daily_to_hourly_quota(1_000) == 50
    # 20000 / 16 * 0.8 = 1000.0 → int = 1000
    assert daily_to_hourly_quota(20_000) == 1_000


def test_hourly_quota_minimum_is_one():
    """Le quota horaire ne peut jamais être inférieur à 1."""
    assert daily_to_hourly_quota(1) == 1
    assert daily_to_hourly_quota(0) == 1


def test_hourly_quota_day1():
    """Jour 1 (5 emails) → 1 email/heure maximum."""
    assert daily_to_hourly_quota(get_quota_for_day(1)) == 1


def test_hourly_quota_day70():
    """IP mature (20 000 emails/jour) → 1000 emails/heure."""
    assert daily_to_hourly_quota(get_quota_for_day(70)) == 1_000


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — create_plan()
# ─────────────────────────────────────────────────────────────────────────────

def test_create_plan_initial_state(db):
    """Plan créé avec état initial correct (jour 1, quota 5)."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    assert plan.phase == "day_1"
    assert plan.current_daily_quota == 5
    assert plan.target_daily_quota == 20_000
    assert plan.ip_id == ip.id
    assert plan.paused is False
    assert plan.started_at is not None


def test_create_plan_persisted(db):
    """Le plan doit être récupérable en base après création."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    fetched = db.query(WarmupPlan).filter(WarmupPlan.id == plan.id).first()
    assert fetched is not None
    assert fetched.current_daily_quota == 5
    assert fetched.phase == "day_1"


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — record_daily_stats()
# ─────────────────────────────────────────────────────────────────────────────

def test_record_daily_stats_creates_record(db):
    """Enregistrement des stats crée un WarmupDailyStat en base."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    stat = engine.record_daily_stats(plan, sent=40, delivered=38, bounced=2, complaints=0)

    assert stat.sent == 40
    assert stat.delivered == 38
    assert stat.bounced == 2
    assert stat.complaints == 0


def test_record_daily_stats_with_opens_clicks(db):
    """Les champs opens et clicks sont optionnels (défaut 0)."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    stat = engine.record_daily_stats(
        plan, sent=100, delivered=95, bounced=3, complaints=0,
        opens=60, clicks=20
    )
    assert stat.opens == 60
    assert stat.clicks == 20


def test_record_daily_stats_upsert(db):
    """Appeler record_daily_stats deux fois le même jour met à jour l'existant."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    engine.record_daily_stats(plan, sent=10, delivered=9, bounced=1, complaints=0)
    stat = engine.record_daily_stats(plan, sent=50, delivered=48, bounced=2, complaints=0)

    assert stat.sent == 50  # Mis à jour, pas dupliqué
    count = db.query(WarmupDailyStat).filter(WarmupDailyStat.plan_id == plan.id).count()
    assert count == 1  # Un seul enregistrement


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — _get_day_number()
# ─────────────────────────────────────────────────────────────────────────────

def test_get_day_number_fresh_plan(db):
    """Plan sans stats → jour 1."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    assert engine._get_day_number(plan) == 1


def test_get_day_number_with_stats(db):
    """Plan avec N jours de stats → prochain jour = N + 1."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    _add_stats(db, plan, n_days=5)
    assert engine._get_day_number(plan) == 6


def test_get_day_number_capped_at_total(db):
    """Après 70 jours, le numéro est cappé à 71 (au-delà du warmup)."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    _add_stats(db, plan, n_days=70)
    day = engine._get_day_number(plan)
    assert day == WARMUP_TOTAL_DAYS + 1


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — check_safety() — scénario nominal (pas de stats)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_check_passes_no_stats(db):
    """Aucune stat → taux = 0 → safe."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    with patch("app.services.warmup_engine.alerter.send", new_callable=AsyncMock):
        with patch("app.services.warmup_engine.mailwizz_db.pause_delivery_server", new_callable=AsyncMock):
            result = await engine.check_safety(plan)

    assert result is True
    assert plan.paused is False


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — check_safety() — pause sur bounce élevé (seuil 7j)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_check_pauses_on_high_bounce(db):
    """Bounce > 2% (seuil 7j) mais < 5% (urgence 24h) → pause normale 72h.

    Utilise record_daily_stats (aujourd'hui) avec 3% bounce :
      - Sécurité 24h : 3% < 5% → pas d'urgence
      - Sécurité 7j  : 3% > 2% → PAUSE 72h
    """
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    # 3% bounce (> seuil 2% mais < urgence 5%)
    engine.record_daily_stats(plan, sent=100, delivered=97, bounced=3, complaints=0)

    with patch("app.services.warmup_engine.alerter.send", new_callable=AsyncMock):
        with patch("app.services.warmup_engine.mailwizz_db.pause_delivery_server", new_callable=AsyncMock):
            result = await engine.check_safety(plan)

    assert result is False
    assert plan.paused is True
    assert plan.pause_until is not None


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — check_safety() — pause sur spam élevé (seuil 7j)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_check_pauses_on_high_spam(db):
    """Spam > 0.03% (seuil 7j) mais < 0.1% (urgence 24h) → pause normale 96h.

    Utilise sent=10000 pour avoir une précision suffisante :
      5 complaints / 10000 sent = 0.05%
      0.05% > 0.03% (seuil normal) → PAUSE
      0.05% < 0.1% (seuil urgence) → pas d'emergency stop
    """
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    # 0.05% spam (> seuil 0.03% mais < urgence 0.1%)
    engine.record_daily_stats(plan, sent=10000, delivered=9995, bounced=0, complaints=5)

    with patch("app.services.warmup_engine.alerter.send", new_callable=AsyncMock):
        with patch("app.services.warmup_engine.mailwizz_db.pause_delivery_server", new_callable=AsyncMock):
            result = await engine.check_safety(plan)

    assert result is False
    assert plan.paused is True


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — check_safety() — arrêt d'urgence (seuil 24h)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_check_emergency_stop_critical_bounce(db):
    """Bounce > 5% sur 24h → emergency_stop + IP quarantined.

    70 bounced / 100 sent = 70% → dépasse le seuil d'urgence de 5%.
    """
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    # 70% bounce (> urgence 5%)
    engine.record_daily_stats(plan, sent=100, delivered=30, bounced=70, complaints=0)

    with patch("app.services.warmup_engine.alerter.send", new_callable=AsyncMock):
        with patch("app.services.warmup_engine.mailwizz_db.pause_delivery_server", new_callable=AsyncMock):
            result = await engine.check_safety(plan)

    assert result is False
    assert plan.phase == "emergency_stop"
    # L'IP doit être mise en quarantine
    db.refresh(ip)
    assert ip.status == "quarantined"
    assert ip.quarantine_until is not None


@pytest.mark.asyncio
async def test_safety_check_emergency_stop_critical_spam(db):
    """Spam > 0.1% sur 24h → emergency_stop.

    10 complaints / 1000 sent = 1% → dépasse le seuil d'urgence de 0.1%.
    """
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    # 1% spam (> urgence 0.1%)
    engine.record_daily_stats(plan, sent=1000, delivered=990, bounced=0, complaints=10)

    with patch("app.services.warmup_engine.alerter.send", new_callable=AsyncMock):
        with patch("app.services.warmup_engine.mailwizz_db.pause_delivery_server", new_callable=AsyncMock):
            result = await engine.check_safety(plan)

    assert result is False
    assert plan.phase == "emergency_stop"


# ─────────────────────────────────────────────────────────────────────────────
# WarmupEngine — get_status()
# ─────────────────────────────────────────────────────────────────────────────

def test_get_status_structure(db):
    """get_status() retourne un dict avec tous les champs attendus."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    status = engine.get_status(plan)

    assert "phase" in status
    assert "day_number" in status
    assert "days_remaining" in status
    assert "current_daily_quota" in status
    assert "hourly_quota" in status
    assert "paused" in status
    assert "bounce_rate_7d" in status
    assert "spam_rate_7d" in status
    assert "thresholds" in status
    assert "quota_schedule" in status


def test_get_status_fresh_plan(db):
    """Plan tout frais : jour 1, 69 jours restants, non pausé."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    status = engine.get_status(plan)

    assert status["phase"] == "day_1"
    assert status["day_number"] == 1
    assert status["days_remaining"] == 69
    assert status["current_daily_quota"] == 5
    assert status["paused"] is False
    assert status["bounce_rate_7d"] == 0.0


def test_get_status_quota_schedule_size(db):
    """Le planning des quotas contient 70 entrées (day_1 à day_70)."""
    ip = _make_ip(db)
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)

    status = engine.get_status(plan)
    assert len(status["quota_schedule"]) == 70
    assert "day_1" in status["quota_schedule"]
    assert "day_70" in status["quota_schedule"]
