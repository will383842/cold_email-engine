"""Value Objects - Immutable domain concepts."""

from .email import Email
from .language import Language
from .tag_slug import TagSlug

__all__ = ["Email", "Language", "TagSlug"]
