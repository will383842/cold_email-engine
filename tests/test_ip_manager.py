"""Tests for IP lifecycle state machine."""

from datetime import datetime, timedelta

from app.enums import IPStatus
from app.models import IP
from app.services.ip_manager import IPManager


def _make_ip(db, status="active", address="1.2.3.4"):
    ip = IP(address=address, hostname="mail.test.com", status=status, purpose="marketing")
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return ip


def test_valid_transition_active_to_retiring(db):
    ip = _make_ip(db, status="active")
    mgr = IPManager(db)
    assert mgr.transition(ip, IPStatus.RETIRING, reason="test")
    assert ip.status == "retiring"


def test_invalid_transition_active_to_resting(db):
    ip = _make_ip(db, status="active")
    mgr = IPManager(db)
    assert not mgr.transition(ip, IPStatus.RESTING, reason="test")
    assert ip.status == "active"


def test_resting_sets_quarantine(db):
    ip = _make_ip(db, status="retiring")
    mgr = IPManager(db)
    mgr.transition(ip, IPStatus.RESTING, reason="test")
    assert ip.quarantine_until is not None
    assert ip.quarantine_until > datetime.utcnow()


def test_get_active_ips(db):
    _make_ip(db, status="active", address="1.1.1.1")
    _make_ip(db, status="standby", address="2.2.2.2")
    mgr = IPManager(db)
    active = mgr.get_active_ips()
    assert len(active) == 1
    assert active[0].address == "1.1.1.1"


def test_quarantine_release(db):
    ip = _make_ip(db, status="resting")
    ip.quarantine_until = datetime.utcnow() - timedelta(hours=1)
    db.commit()
    mgr = IPManager(db)
    released = mgr.check_quarantine_release()
    assert len(released) == 1
    assert released[0].status == "warming"


def test_monthly_rotation(db):
    _make_ip(db, status="active", address="1.1.1.1")
    _make_ip(db, status="active", address="2.2.2.2")
    mgr = IPManager(db)
    result = mgr.monthly_rotation()
    assert result["count"] == 2
