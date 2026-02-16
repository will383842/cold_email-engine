"""TagSlug Value Object."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TagSlug:
    """Tag slug value object (URL-safe identifier)."""

    value: str

    def __post_init__(self):
        """Validate slug format."""
        if not self.is_valid(self.value):
            raise ValueError(
                f"Invalid tag slug: {self.value}. Must be lowercase alphanumeric with hyphens."
            )

    @staticmethod
    def is_valid(slug: str) -> bool:
        """Validate slug format (lowercase, alphanumeric, hyphens)."""
        pattern = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
        return bool(re.match(pattern, slug))

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, text: str) -> "TagSlug":
        """Create slug from arbitrary string."""
        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and underscores with hyphens
        slug = re.sub(r"[\s_]+", "-", slug)
        # Remove non-alphanumeric characters (except hyphens)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        # Remove consecutive hyphens
        slug = re.sub(r"-+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        return cls(value=slug)
