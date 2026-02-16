"""Email Value Object."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """Email address value object with validation."""

    value: str

    def __post_init__(self):
        """Validate email format."""
        if not self.is_valid(self.value):
            raise ValueError(f"Invalid email address: {self.value}")

    @staticmethod
    def is_valid(email: str) -> bool:
        """Validate email format (basic regex)."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def __str__(self) -> str:
        return self.value

    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split("@")[1]

    def local_part(self) -> str:
        """Extract local part from email."""
        return self.value.split("@")[0]
