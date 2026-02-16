"""Audit logging service for compliance."""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, User


class AuditLogger:
    """Service for logging user actions to audit trail."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        user: Optional[User] = None,
        user_id: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an action to the audit trail.

        Args:
            action: Action performed (e.g., "create_ip", "delete_domain")
            resource_type: Type of resource (e.g., "ip", "domain", "warmup_plan")
            resource_id: ID of the resource (optional)
            user: User object (optional, takes precedence over user_id)
            user_id: User ID (optional, used if user not provided)
            details: Additional context as dict (will be JSON serialized)
            ip_address: Client IP address

        Returns:
            The created AuditLog instance
        """
        log_entry = AuditLog(
            user_id=user.id if user else user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def get_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """
        Query audit logs with filters.

        Args:
            user_id: Filter by user ID
            action: Filter by action
            resource_type: Filter by resource type
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of AuditLog instances
        """
        query = self.db.query(AuditLog).order_by(AuditLog.timestamp.desc())

        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        return query.limit(limit).offset(offset).all()
