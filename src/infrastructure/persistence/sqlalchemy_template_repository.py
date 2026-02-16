"""SQLAlchemy Template Repository Implementation."""

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models import EmailTemplate as TemplateModel
from src.domain.repositories import ITemplateRepository


class SQLAlchemyTemplateRepository(ITemplateRepository):
    """SQLAlchemy implementation of Template Repository."""

    def __init__(self, db: Session):
        self.db = db

    def save(self, template_data: dict) -> TemplateModel:
        """
        Save template (insert or update).

        Args:
            template_data: Dict with template fields

        Returns:
            Saved template model
        """
        template_id = template_data.get("id")

        if template_id:
            # Update existing
            template_model = self.db.query(TemplateModel).filter_by(id=template_id).first()
            if not template_model:
                raise ValueError(f"Template {template_id} not found")
            self._update_model(template_model, template_data)
        else:
            # Insert new
            template_model = self._to_model(template_data)
            self.db.add(template_model)

        self.db.flush()
        return template_model

    def find_by_id(self, template_id: int) -> Optional[TemplateModel]:
        """Find template by ID."""
        return self.db.query(TemplateModel).filter_by(id=template_id).first()

    def find_by_language_and_category(
        self,
        tenant_id: int,
        language: str,
        category: Optional[str] = None,
    ) -> Optional[TemplateModel]:
        """
        Find template by language and category.

        Priority:
        1. Exact match (language + category)
        2. Language + general (category=None)
        """
        query = self.db.query(TemplateModel).filter_by(
            tenant_id=tenant_id,
            language=language,
        )

        if category is not None:
            query = query.filter_by(category=category)
        else:
            query = query.filter(TemplateModel.category.is_(None))

        return query.first()

    def find_default(self, tenant_id: int, language: str) -> Optional[TemplateModel]:
        """Find default template for a language."""
        return (
            self.db.query(TemplateModel)
            .filter_by(tenant_id=tenant_id, language=language, is_default=True)
            .first()
        )

    def find_all_by_tenant(self, tenant_id: int) -> list[TemplateModel]:
        """Find all templates for a tenant."""
        return (
            self.db.query(TemplateModel)
            .filter_by(tenant_id=tenant_id)
            .order_by(TemplateModel.language, TemplateModel.category)
            .all()
        )

    def delete(self, template_id: int) -> None:
        """Delete template."""
        template_model = self.db.query(TemplateModel).filter_by(id=template_id).first()
        if template_model:
            self.db.delete(template_model)
            self.db.flush()

    def count_by_tenant(self, tenant_id: int) -> int:
        """Count templates for a tenant."""
        return self.db.query(TemplateModel).filter_by(tenant_id=tenant_id).count()

    # =========================================================================
    # Dict <-> Model Mapping
    # =========================================================================

    def _to_model(self, data: dict) -> TemplateModel:
        """Convert dict to SQLAlchemy model."""
        # Parse variables if it's a list
        variables = data.get("variables", [])
        if isinstance(variables, list):
            variables = json.dumps(variables)

        return TemplateModel(
            tenant_id=data["tenant_id"],
            name=data["name"],
            language=data["language"],
            category=data.get("category"),
            subject=data["subject"],
            body_html=data["body_html"],
            body_text=data.get("body_text"),
            variables=variables,
            is_default=data.get("is_default", False),
        )

    def _update_model(self, model: TemplateModel, data: dict) -> None:
        """Update SQLAlchemy model from dict."""
        model.name = data.get("name", model.name)
        model.language = data.get("language", model.language)
        model.category = data.get("category", model.category)
        model.subject = data.get("subject", model.subject)
        model.body_html = data.get("body_html", model.body_html)
        model.body_text = data.get("body_text", model.body_text)
        model.is_default = data.get("is_default", model.is_default)

        # Handle variables
        if "variables" in data:
            variables = data["variables"]
            if isinstance(variables, list):
                model.variables = json.dumps(variables)
            else:
                model.variables = variables
