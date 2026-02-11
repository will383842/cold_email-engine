"""Tests for blacklist checker."""

from unittest.mock import patch

from app.models import IP, BlacklistEvent
from app.services.blacklist_checker import BlacklistChecker, _reverse_ip


def _make_ip(db, address="1.2.3.4"):
    ip = IP(address=address, hostname="mail.test.com", status="active", purpose="marketing")
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return ip


def test_reverse_ip():
    assert _reverse_ip("1.2.3.4") == "4.3.2.1"
    assert _reverse_ip("192.168.1.100") == "100.1.168.192"


@patch.object(BlacklistChecker, "check_single", return_value=False)
def test_check_ip_clean(mock_check, db):
    checker = BlacklistChecker(db)
    result = checker.check_ip("1.2.3.4")
    assert result == []


@patch.object(BlacklistChecker, "check_single", side_effect=lambda ip, bl: bl == "zen.spamhaus.org")
def test_check_ip_listed(mock_check, db):
    checker = BlacklistChecker(db)
    result = checker.check_ip("1.2.3.4")
    assert "zen.spamhaus.org" in result
    assert len(result) == 1


@patch.object(BlacklistChecker, "check_single", return_value=True)
def test_record_listing(mock_check, db):
    ip = _make_ip(db)
    checker = BlacklistChecker(db)
    checker._record_listing(ip, ["zen.spamhaus.org"])
    events = db.query(BlacklistEvent).filter(BlacklistEvent.ip_id == ip.id).all()
    assert len(events) == 1
    assert events[0].blacklist_name == "zen.spamhaus.org"


@patch.object(BlacklistChecker, "check_single", return_value=True)
def test_no_duplicate_listing(mock_check, db):
    ip = _make_ip(db)
    checker = BlacklistChecker(db)
    checker._record_listing(ip, ["zen.spamhaus.org"])
    checker._record_listing(ip, ["zen.spamhaus.org"])
    events = db.query(BlacklistEvent).filter(BlacklistEvent.ip_id == ip.id).all()
    assert len(events) == 1
