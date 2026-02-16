"""Validate Contacts Bulk Use Case."""

from dataclasses import dataclass

from src.domain.repositories import IContactRepository
from src.domain.services import ContactValidator


@dataclass
class ValidateContactsBulkResult:
    """Result of bulk validation."""

    total_validated: int
    valid_count: int
    invalid_count: int
    risky_count: int


class ValidateContactsBulkUseCase:
    """Use case for bulk validating contacts."""

    def __init__(self, contact_repo: IContactRepository, validator: ContactValidator = None):
        self.contact_repo = contact_repo
        self.validator = validator or ContactValidator()

    def execute(self, tenant_id: int, limit: int = 100) -> ValidateContactsBulkResult:
        """
        Validate all pending contacts for a tenant.

        Args:
            tenant_id: Tenant ID
            limit: Max contacts to validate in one batch

        Returns:
            ValidateContactsBulkResult with counts
        """
        from app.enums import ContactStatus, ValidationStatus

        # Get pending contacts
        contacts = self.contact_repo.find_by_tags(
            tenant_id=tenant_id,
            tags_all=None,
            tags_any=None,
            exclude_tags=None,
            limit=limit,
        )

        # Filter only pending
        pending_contacts = [c for c in contacts if c.status == ContactStatus.PENDING]

        valid_count = 0
        invalid_count = 0
        risky_count = 0

        for contact in pending_contacts:
            # Validate email
            status, score, errors = self.validator.validate(str(contact.email))

            # Update contact
            contact.validate(status, score)

            if status == ValidationStatus.VALID:
                valid_count += 1
            elif status == ValidationStatus.INVALID:
                invalid_count += 1
            elif status == ValidationStatus.RISKY:
                risky_count += 1

            # Save
            self.contact_repo.save(contact)

        return ValidateContactsBulkResult(
            total_validated=len(pending_contacts),
            valid_count=valid_count,
            invalid_count=invalid_count,
            risky_count=risky_count,
        )
