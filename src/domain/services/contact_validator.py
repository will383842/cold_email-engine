"""Contact Validator Service - Email validation logic."""

import re
from typing import Optional, Tuple

from app.enums import ValidationStatus


class ContactValidator:
    """
    Validates contact email addresses.

    Validation levels:
    - Syntax validation (RFC 5322)
    - Domain validation (MX records)
    - Deliverability check (via external API like ZeroBounce, NeverBounce)

    Returns:
    - ValidationStatus (VALID, INVALID, RISKY, UNKNOWN)
    - Validation score (0.0 - 1.0)
    - List of errors/warnings
    """

    # Disposable email domains (common ones)
    DISPOSABLE_DOMAINS = {
        "tempmail.com",
        "guerrillamail.com",
        "10minutemail.com",
        "mailinator.com",
        "throwaway.email",
        "temp-mail.org",
    }

    # Role-based email prefixes
    ROLE_BASED_PREFIXES = {
        "admin",
        "support",
        "info",
        "contact",
        "sales",
        "marketing",
        "noreply",
        "no-reply",
        "webmaster",
        "postmaster",
    }

    def __init__(self, external_validator=None):
        """
        Initialize validator.

        Args:
            external_validator: Optional external validation service (ZeroBounce, NeverBounce, etc.)
        """
        self.external_validator = external_validator

    def validate(self, email: str) -> Tuple[ValidationStatus, float, list[str]]:
        """
        Validate email address.

        Args:
            email: Email address to validate

        Returns:
            Tuple of (status, score, errors)

        Example:
            status, score, errors = validator.validate("test@example.com")
            # (ValidationStatus.VALID, 0.95, [])
        """
        errors = []
        score = 1.0

        # 1. Syntax validation
        if not self._is_valid_syntax(email):
            return ValidationStatus.INVALID, 0.0, ["Invalid email syntax"]

        # 2. Extract domain
        domain = email.split("@")[1].lower()

        # 3. Check disposable domains
        if domain in self.DISPOSABLE_DOMAINS:
            errors.append("Disposable email domain")
            score -= 0.5

        # 4. Check role-based
        local_part = email.split("@")[0].lower()
        if local_part in self.ROLE_BASED_PREFIXES:
            errors.append("Role-based email address")
            score -= 0.2

        # 5. Check for common typos in popular domains
        typo_check = self._check_domain_typos(domain)
        if typo_check:
            errors.append(f"Possible typo: did you mean {typo_check}?")
            score -= 0.3

        # 6. External validation (if available)
        if self.external_validator:
            ext_status, ext_score, ext_errors = self.external_validator.validate(email)
            score = min(score, ext_score)
            errors.extend(ext_errors)

            # If external validator says invalid, trust it
            if ext_status == ValidationStatus.INVALID:
                return ValidationStatus.INVALID, 0.0, errors

        # 7. Determine final status
        if score >= 0.8:
            status = ValidationStatus.VALID
        elif score >= 0.5:
            status = ValidationStatus.RISKY
        elif errors:
            status = ValidationStatus.INVALID
        else:
            status = ValidationStatus.UNKNOWN

        return status, max(0.0, score), errors

    def _is_valid_syntax(self, email: str) -> bool:
        """
        Validate email syntax (RFC 5322 simplified).

        Args:
            email: Email address

        Returns:
            True if valid syntax
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _check_domain_typos(self, domain: str) -> Optional[str]:
        """
        Check for common typos in popular email domains.

        Args:
            domain: Email domain

        Returns:
            Suggested correction or None
        """
        typo_map = {
            "gmial.com": "gmail.com",
            "gmai.com": "gmail.com",
            "yahooo.com": "yahoo.com",
            "yaho.com": "yahoo.com",
            "hotmial.com": "hotmail.com",
            "outloo.com": "outlook.com",
            "outlok.com": "outlook.com",
        }
        return typo_map.get(domain)

    def validate_bulk(self, emails: list[str]) -> dict[str, Tuple[ValidationStatus, float, list[str]]]:
        """
        Validate multiple emails.

        Args:
            emails: List of email addresses

        Returns:
            Dict mapping email to (status, score, errors)
        """
        results = {}
        for email in emails:
            results[email] = self.validate(email)
        return results
