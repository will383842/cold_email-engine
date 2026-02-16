"""Create Template Use Case."""

from dataclasses import dataclass
from typing import Optional

from src.domain.repositories import ITemplateRepository


@dataclass
class CreateTemplateDTO:
    """DTO for creating a template."""

    tenant_id: int
    name: str
    language: str
    category: Optional[str] = None
    subject: str = ""
    body_html: str = ""
    body_text: Optional[str] = None
    variables: Optional[list[str]] = None
    is_default: bool = False


class CreateTemplateUseCase:
    """Use case for creating a new template."""

    def __init__(self, template_repo: ITemplateRepository):
        self.template_repo = template_repo

    def execute(self, dto: CreateTemplateDTO) -> dict:
        """
        Create a new email template.

        Args:
            dto: Template creation data

        Returns:
            Created template dict
        """
        template_data = {
            "tenant_id": dto.tenant_id,
            "name": dto.name,
            "language": dto.language,
            "category": dto.category,
            "subject": dto.subject,
            "body_html": dto.body_html,
            "body_text": dto.body_text,
            "variables": dto.variables or [],
            "is_default": dto.is_default,
        }

        # Save via repository
        template = self.template_repo.save(template_data)

        return {
            "id": template.id,
            "tenant_id": template.tenant_id,
            "name": template.name,
            "language": template.language,
            "category": template.category,
        }
