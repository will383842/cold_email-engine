"""Language Value Object."""

from dataclasses import dataclass

from app.enums import Language as LanguageEnum


@dataclass(frozen=True)
class Language:
    """Language value object (ISO 639-1)."""

    code: str

    def __post_init__(self):
        """Validate language code."""
        valid_codes = [lang.value for lang in LanguageEnum]
        if self.code not in valid_codes:
            raise ValueError(f"Invalid language code: {self.code}. Must be one of {valid_codes}")

    def __str__(self) -> str:
        return self.code

    @classmethod
    def from_enum(cls, lang_enum: LanguageEnum) -> "Language":
        """Create from enum."""
        return cls(code=lang_enum.value)

    def to_enum(self) -> LanguageEnum:
        """Convert to enum."""
        return LanguageEnum(self.code)
