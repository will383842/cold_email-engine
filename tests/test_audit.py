"""Tests for audit logging."""

from app.enums import UserRole
from app.services.audit import AuditLogger
from app.services.auth import create_user


def test_audit_log_creation(db):
    """Test creating an audit log entry."""
    auditor = AuditLogger(db)
    user = create_user(db, "audit@example.com", "audituser", "password123", UserRole.ADMIN)

    log = auditor.log(
        action="create_ip",
        resource_type="ip",
        resource_id=1,
        user=user,
        details={"ip_address": "192.0.2.1"},
        ip_address="203.0.113.1",
    )

    assert log.action == "create_ip"
    assert log.resource_type == "ip"
    assert log.resource_id == 1
    assert log.user_id == user.id
    assert log.ip_address == "203.0.113.1"


def test_audit_log_system_action(db):
    """Test audit log for system actions (no user)."""
    auditor = AuditLogger(db)

    log = auditor.log(
        action="auto_blacklist",
        resource_type="ip",
        resource_id=1,
        user=None,
        details={"reason": "listed on spamhaus"},
    )

    assert log.user_id is None
    assert log.action == "auto_blacklist"


def test_get_audit_logs(db):
    """Test querying audit logs."""
    auditor = AuditLogger(db)
    user = create_user(db, "query@example.com", "queryuser", "password123", UserRole.ADMIN)

    # Create some logs
    auditor.log("create_ip", "ip", 1, user=user)
    auditor.log("delete_ip", "ip", 1, user=user)
    auditor.log("create_domain", "domain", 1, user=user)

    # Query all logs
    logs = auditor.get_logs(limit=10)
    assert len(logs) == 3

    # Query by user
    logs = auditor.get_logs(user_id=user.id, limit=10)
    assert len(logs) == 3

    # Query by action
    logs = auditor.get_logs(action="create_ip", limit=10)
    assert len(logs) == 1

    # Query by resource type
    logs = auditor.get_logs(resource_type="ip", limit=10)
    assert len(logs) == 2
