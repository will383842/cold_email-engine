"""Contact Repository Interface (Port)."""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities import Contact
from src.domain.value_objects import Email, TagSlug


class IContactRepository(ABC):
    """Contact repository interface (Port)."""

    @abstractmethod
    def save(self, contact: Contact) -> Contact:
        """Save contact (insert or update)."""
        pass

    @abstractmethod
    def find_by_id(self, contact_id: int) -> Optional[Contact]:
        """Find contact by ID."""
        pass

    @abstractmethod
    def find_by_email(self, tenant_id: int, email: Email) -> Optional[Contact]:
        """Find contact by email (scoped to tenant)."""
        pass

    @abstractmethod
    def find_by_tags(
        self,
        tenant_id: int,
        tags_all: Optional[list[TagSlug]] = None,
        tags_any: Optional[list[TagSlug]] = None,
        exclude_tags: Optional[list[TagSlug]] = None,
        limit: int = 100,
    ) -> list[Contact]:
        """Find contacts by tag filters."""
        pass

    @abstractmethod
    def delete(self, contact_id: int) -> None:
        """Delete contact."""
        pass

    @abstractmethod
    def count_by_tenant(self, tenant_id: int) -> int:
        """Count contacts for a tenant."""
        pass
