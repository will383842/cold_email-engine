"""Tests for DNS validator."""

from unittest.mock import MagicMock, patch

from app.models import Domain, IP
from app.services.dns_validator import DNSValidator


def _make_domain(db, name="example.com"):
    ip = IP(address="1.2.3.4", hostname="mail.example.com", status="active", purpose="marketing")
    db.add(ip)
    db.commit()
    db.refresh(ip)

    domain = Domain(
        name=name,
        purpose="marketing",
        ip_id=ip.id,
        dkim_selector="default",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@patch.object(DNSValidator, "check_spf", return_value=True)
@patch.object(DNSValidator, "check_dkim", return_value=True)
@patch.object(DNSValidator, "check_dmarc", return_value=True)
@patch.object(DNSValidator, "check_ptr", return_value=True)
@patch.object(DNSValidator, "check_mx", return_value=True)
def test_validate_domain_all_pass(m_mx, m_ptr, m_dmarc, m_dkim, m_spf, db):
    domain = _make_domain(db)
    validator = DNSValidator(db)
    results = validator.validate_domain(domain)
    assert results["spf"] is True
    assert results["dkim"] is True
    assert results["dmarc"] is True
    assert results["ptr"] is True
    assert domain.spf_valid is True
    assert domain.last_dns_check is not None


@patch.object(DNSValidator, "check_spf", return_value=False)
@patch.object(DNSValidator, "check_dkim", return_value=True)
@patch.object(DNSValidator, "check_dmarc", return_value=False)
@patch.object(DNSValidator, "check_ptr", return_value=True)
@patch.object(DNSValidator, "check_mx", return_value=True)
def test_validate_domain_partial_fail(m_mx, m_ptr, m_dmarc, m_dkim, m_spf, db):
    domain = _make_domain(db)
    validator = DNSValidator(db)
    results = validator.validate_domain(domain)
    assert results["spf"] is False
    assert results["dmarc"] is False
    assert domain.spf_valid is False
    assert domain.dmarc_valid is False
