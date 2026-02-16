"""Update Template Use Case."""

from dataclasses import dataclass
from typing import Optional

from src.domain.repositories import ITemplateRepository


@dataclass
class UpdateTemplateDTO:
    """DTO for updating a template."""

    template_id: int
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    variables: Optional[list[str]] = None
    is_default: Optional[bool] = None


class UpdateTemplateUseCase:
    """Use case for updating a template."""

    def __init__(self, template_repo: ITemplateRepository):
        self.template_repo = template_repo

    def execute(self, dto: UpdateTemplateDTO) -> dict:
        """
        Update template fields.

        Args:
            dto: Template update data

        Returns:
            Updated template dict

        Raises:
            ValueError: If template not found
        """
        # Get template
        template = self.template_repo.find_by_id(dto.template_id)
        if not template:
            raise ValueError(f"Template {dto.template_id} not found")

        # Build update data
        update_data = {"id": dto.template_id}

        if dto.name is not None:
            update_data["name"] = dto.name
        if dto.subject is not None:
            update_data["subject"] = dto.subject
        if dto.body_html is not None:
            update_data["body_html"] = dto.body_html
        if dto.body_text is not None:
            update_data["body_text"] = dto.body_text
        if dto.variables is not None:
            update_data["variables"] = dto.variables
        if dto.is_default is not None:
            update_data["is_default"] = dto.is_default

        # Save
        updated = self.template_repo.save(update_data)

        return {
            "id": updated.id,
            "name": updated.name,
            "subject": updated.subject,
            "language": updated.language,
        }
