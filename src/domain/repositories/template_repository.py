"""Email Template Repository Interface (Port)."""

from abc import ABC, abstractmethod
from typing import Optional


class ITemplateRepository(ABC):
    """Email template repository interface (Port)."""

    @abstractmethod
    def save(self, template) -> any:
        """Save template (insert or update)."""
        pass

    @abstractmethod
    def find_by_id(self, template_id: int) -> Optional[any]:
        """Find template by ID."""
        pass

    @abstractmethod
    def find_by_language_and_category(
        self,
        tenant_id: int,
        language: str,
        category: Optional[str] = None,
    ) -> Optional[any]:
        """
        Find template by language and category.

        Args:
            tenant_id: Tenant ID
            language: ISO 639-1 code (fr, en, etc.)
            category: Optional category (avocat, blogger, etc.) or None for general

        Returns:
            Template or None
        """
        pass

    @abstractmethod
    def find_default(self, tenant_id: int, language: str) -> Optional[any]:
        """
        Find default template for a language.

        Args:
            tenant_id: Tenant ID
            language: ISO 639-1 code

        Returns:
            Default template or None
        """
        pass

    @abstractmethod
    def find_all_by_tenant(self, tenant_id: int) -> list[any]:
        """Find all templates for a tenant."""
        pass

    @abstractmethod
    def delete(self, template_id: int) -> None:
        """Delete template."""
        pass

    @abstractmethod
    def count_by_tenant(self, tenant_id: int) -> int:
        """Count templates for a tenant."""
        pass
