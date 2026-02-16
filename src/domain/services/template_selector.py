"""Template Selector Service - Intelligent template selection."""

from typing import Optional

from app.enums import Language


class TemplateSelector:
    """
    Selects the best template based on:
    1. Language + Category (exact match)
    2. Language only (general template)
    3. English fallback + Category
    4. English fallback (general)

    Example:
        # For a French lawyer contact
        selector.select(language="fr", category="avocat")
        → Returns: Template(language="fr", category="avocat")

        # If French lawyer template doesn't exist
        → Fallback: Template(language="fr", category=None)  # General French

        # If no French template exists
        → Fallback: Template(language="en", category="avocat")  # English lawyer

        # Last resort
        → Fallback: Template(language="en", category=None)  # General English
    """

    def __init__(self, template_repository):
        """
        Initialize with template repository.

        Args:
            template_repository: Repository implementing ITemplateRepository
        """
        self.template_repo = template_repository

    def select(
        self,
        tenant_id: int,
        language: str,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """
        Select best template for given criteria.

        Args:
            tenant_id: Tenant ID (SOS-Expat or Ulixai)
            language: ISO 639-1 language code (fr, en, es, etc.)
            category: Optional category (avocat, blogger, etc.)
            tags: Optional list of tag slugs for future tag-based selection

        Returns:
            Template dict or None if no template found

        Selection priority:
            1. language + category (exact match)
            2. language + general (category=None)
            3. EN + category (fallback)
            4. EN + general (last resort)
        """
        # Normalize language code
        language = language.lower()

        # Priority 1: Exact match (language + category)
        if category:
            template = self.template_repo.find_by_language_and_category(
                tenant_id=tenant_id,
                language=language,
                category=category,
            )
            if template:
                return self._to_dict(template)

        # Priority 2: Language + general (no category)
        template = self.template_repo.find_by_language_and_category(
            tenant_id=tenant_id,
            language=language,
            category=None,
        )
        if template:
            return self._to_dict(template)

        # Priority 3: English fallback + category
        if language != "en" and category:
            template = self.template_repo.find_by_language_and_category(
                tenant_id=tenant_id,
                language="en",
                category=category,
            )
            if template:
                return self._to_dict(template)

        # Priority 4: English fallback + general
        if language != "en":
            template = self.template_repo.find_by_language_and_category(
                tenant_id=tenant_id,
                language="en",
                category=None,
            )
            if template:
                return self._to_dict(template)

        # No template found
        return None

    def select_default(self, tenant_id: int, language: str) -> Optional[dict]:
        """
        Select default template for a language.

        Args:
            tenant_id: Tenant ID
            language: ISO 639-1 language code

        Returns:
            Default template or None
        """
        template = self.template_repo.find_default(
            tenant_id=tenant_id,
            language=language,
        )
        if template:
            return self._to_dict(template)

        # Fallback to English default
        if language != "en":
            template = self.template_repo.find_default(
                tenant_id=tenant_id,
                language="en",
            )
            if template:
                return self._to_dict(template)

        return None

    def render_template(
        self,
        template: dict,
        variables: dict,
    ) -> tuple[str, str]:
        """
        Render template with variables.

        Args:
            template: Template dict with subject and body_html
            variables: Dict of variables to replace (e.g., {"firstName": "Jean", "company": "ACME"})

        Returns:
            Tuple of (rendered_subject, rendered_body_html)

        Example:
            subject = "Bonjour {firstName}"
            variables = {"firstName": "Jean"}
            → "Bonjour Jean"
        """
        subject = template.get("subject", "")
        body_html = template.get("body_html", "")

        # Replace variables
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value))
            body_html = body_html.replace(placeholder, str(value))

        return subject, body_html

    def _to_dict(self, template) -> dict:
        """Convert template entity/model to dict."""
        if hasattr(template, "__dict__"):
            # SQLAlchemy model
            return {
                "id": template.id,
                "name": template.name,
                "language": template.language,
                "category": template.category,
                "subject": template.subject,
                "body_html": template.body_html,
                "body_text": template.body_text,
                "variables": template.variables,
                "is_default": template.is_default,
            }
        return template
