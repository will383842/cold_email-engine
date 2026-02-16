"""Templates API v2 - Multi-language template management."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from src.domain.services import TemplateSelector
from src.infrastructure.persistence import SQLAlchemyTemplateRepository

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CreateTemplateRequest(BaseModel):
    """Request schema for creating a template."""

    tenant_id: int
    name: str
    language: str  # ISO 639-1 (fr, en, es, etc.)
    category: Optional[str] = None  # avocat, blogger, etc. (null = general)
    subject: str
    body_html: str
    body_text: Optional[str] = None
    variables: Optional[List[str]] = None  # ["firstName", "company", etc.]
    is_default: bool = False


class UpdateTemplateRequest(BaseModel):
    """Request schema for updating a template."""

    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    variables: Optional[List[str]] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Response schema for a template."""

    id: int
    tenant_id: int
    name: str
    language: str
    category: Optional[str]
    subject: str
    body_html: str
    body_text: Optional[str]
    variables: Optional[str]
    is_default: bool
    total_sent: int
    avg_open_rate: float
    avg_click_rate: float


class SelectTemplateRequest(BaseModel):
    """Request for intelligent template selection."""

    tenant_id: int
    language: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class RenderTemplateRequest(BaseModel):
    """Request for template rendering."""

    template_id: int
    variables: dict  # {"firstName": "Jean", "company": "ACME"}


class RenderTemplateResponse(BaseModel):
    """Response for template rendering."""

    subject: str
    body_html: str


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/", response_model=TemplateResponse)
def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new email template.

    Supports:
    - 9 languages (fr, en, es, de, pt, ru, zh, hi, ar)
    - Category-specific templates (avocat, blogger, etc.)
    - General templates (category=null)
    - RTL support for Arabic (AR) - use dir="rtl" in body_html
    """
    try:
        template_repo = SQLAlchemyTemplateRepository(db)

        template_data = {
            "tenant_id": request.tenant_id,
            "name": request.name,
            "language": request.language,
            "category": request.category,
            "subject": request.subject,
            "body_html": request.body_html,
            "body_text": request.body_text,
            "variables": request.variables or [],
            "is_default": request.is_default,
        }

        template_model = template_repo.save(template_data)
        db.commit()

        return TemplateResponse(
            id=template_model.id,
            tenant_id=template_model.tenant_id,
            name=template_model.name,
            language=template_model.language,
            category=template_model.category,
            subject=template_model.subject,
            body_html=template_model.body_html,
            body_text=template_model.body_text,
            variables=template_model.variables,
            is_default=template_model.is_default,
            total_sent=template_model.total_sent,
            avg_open_rate=template_model.avg_open_rate,
            avg_click_rate=template_model.avg_click_rate,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.get("/{tenant_id}", response_model=List[TemplateResponse])
def list_templates(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """List all templates for a tenant."""
    try:
        template_repo = SQLAlchemyTemplateRepository(db)
        templates = template_repo.find_all_by_tenant(tenant_id)

        return [
            TemplateResponse(
                id=t.id,
                tenant_id=t.tenant_id,
                name=t.name,
                language=t.language,
                category=t.category,
                subject=t.subject,
                body_html=t.body_html,
                body_text=t.body_text,
                variables=t.variables,
                is_default=t.is_default,
                total_sent=t.total_sent,
                avg_open_rate=t.avg_open_rate,
                avg_click_rate=t.avg_click_rate,
            )
            for t in templates
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/{tenant_id}/{template_id}", response_model=TemplateResponse)
def get_template(
    tenant_id: int,
    template_id: int,
    db: Session = Depends(get_db),
):
    """Get a single template."""
    try:
        template_repo = SQLAlchemyTemplateRepository(db)
        template = template_repo.find_by_id(template_id)

        if not template or template.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Template not found")

        return TemplateResponse(
            id=template.id,
            tenant_id=template.tenant_id,
            name=template.name,
            language=template.language,
            category=template.category,
            subject=template.subject,
            body_html=template.body_html,
            body_text=template.body_text,
            variables=template.variables,
            is_default=template.is_default,
            total_sent=template.total_sent,
            avg_open_rate=template.avg_open_rate,
            avg_click_rate=template.avg_click_rate,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.put("/{tenant_id}/{template_id}", response_model=TemplateResponse)
def update_template(
    tenant_id: int,
    template_id: int,
    request: UpdateTemplateRequest,
    db: Session = Depends(get_db),
):
    """Update a template."""
    try:
        template_repo = SQLAlchemyTemplateRepository(db)
        template = template_repo.find_by_id(template_id)

        if not template or template.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Template not found")

        # Build update data
        update_data = {"id": template_id}
        if request.name is not None:
            update_data["name"] = request.name
        if request.subject is not None:
            update_data["subject"] = request.subject
        if request.body_html is not None:
            update_data["body_html"] = request.body_html
        if request.body_text is not None:
            update_data["body_text"] = request.body_text
        if request.variables is not None:
            update_data["variables"] = request.variables
        if request.is_default is not None:
            update_data["is_default"] = request.is_default

        updated = template_repo.save(update_data)
        db.commit()

        return TemplateResponse(
            id=updated.id,
            tenant_id=updated.tenant_id,
            name=updated.name,
            language=updated.language,
            category=updated.category,
            subject=updated.subject,
            body_html=updated.body_html,
            body_text=updated.body_text,
            variables=updated.variables,
            is_default=updated.is_default,
            total_sent=updated.total_sent,
            avg_open_rate=updated.avg_open_rate,
            avg_click_rate=updated.avg_click_rate,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/{tenant_id}/{template_id}")
def delete_template(
    tenant_id: int,
    template_id: int,
    db: Session = Depends(get_db),
):
    """Delete a template."""
    try:
        template_repo = SQLAlchemyTemplateRepository(db)
        template = template_repo.find_by_id(template_id)

        if not template or template.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Template not found")

        template_repo.delete(template_id)
        db.commit()

        return {"success": True, "message": "Template deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.post("/select", response_model=TemplateResponse)
def select_template(
    request: SelectTemplateRequest,
    db: Session = Depends(get_db),
):
    """
    Intelligent template selection.

    Selection priority:
    1. language + category (exact match)
    2. language + general (category=null)
    3. EN + category (fallback)
    4. EN + general (last resort)

    Example:
        # French lawyer
        POST /api/v2/templates/select
        {"tenant_id": 1, "language": "fr", "category": "avocat"}
        → Returns template(language="fr", category="avocat")
    """
    try:
        template_repo = SQLAlchemyTemplateRepository(db)
        selector = TemplateSelector(template_repo)

        template_dict = selector.select(
            tenant_id=request.tenant_id,
            language=request.language,
            category=request.category,
            tags=request.tags,
        )

        if not template_dict:
            raise HTTPException(status_code=404, detail="No matching template found")

        return TemplateResponse(**template_dict, total_sent=0, avg_open_rate=0.0, avg_click_rate=0.0)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select template: {str(e)}")


@router.post("/render", response_model=RenderTemplateResponse)
def render_template(
    request: RenderTemplateRequest,
    db: Session = Depends(get_db),
):
    """
    Render template with variables.

    Replaces {variable} placeholders with actual values.

    Example:
        POST /api/v2/templates/render
        {
            "template_id": 123,
            "variables": {
                "firstName": "Jean",
                "company": "ACME Corp"
            }
        }
        → Returns rendered subject and body_html
    """
    try:
        template_repo = SQLAlchemyTemplateRepository(db)
        selector = TemplateSelector(template_repo)

        template = template_repo.find_by_id(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        template_dict = {
            "subject": template.subject,
            "body_html": template.body_html,
        }

        subject, body_html = selector.render_template(template_dict, request.variables)

        return RenderTemplateResponse(subject=subject, body_html=body_html)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render template: {str(e)}")
