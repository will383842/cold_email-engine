"""Contacts API v2 - Enterprise endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from src.application.use_cases import IngestContactsUseCase
from src.application.use_cases.ingest_contacts import (
    IngestContactDTO,
    IngestContactsResult,
)
from src.infrastructure.persistence import SQLAlchemyContactRepository

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class IngestContactRequest(BaseModel):
    """Request schema for ingesting a single contact."""

    tenant_id: int
    data_source_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    language: str = "en"
    category: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_fields: Optional[dict] = None
    tags: Optional[List[str]] = None


class IngestContactsRequest(BaseModel):
    """Request schema for batch contact ingestion."""

    contacts: List[IngestContactRequest]


class IngestContactsResponse(BaseModel):
    """Response schema for contact ingestion."""

    success: bool
    total_processed: int
    new_contacts: int
    updated_contacts: int
    duplicates_skipped: int
    errors: List[str]


class ContactResponse(BaseModel):
    """Response schema for a single contact."""

    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    company: Optional[str]
    language: str
    category: Optional[str]
    status: str
    tags: List[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/ingest", response_model=IngestContactsResponse)
def ingest_contacts(
    request: IngestContactsRequest,
    db: Session = Depends(get_db),
):
    """
    Ingest contacts from external sources (Scraper-Pro, Backlink Engine, CSV, API).

    This endpoint demonstrates the Clean Architecture pattern:
    1. Presentation layer receives HTTP request
    2. Maps request to DTOs
    3. Calls Use Case with dependencies injected
    4. Use Case orchestrates business logic
    5. Repository handles persistence
    6. Response is returned to client
    """
    try:
        # 1. Map request to DTOs
        contact_dtos = [
            IngestContactDTO(
                tenant_id=c.tenant_id,
                data_source_id=c.data_source_id,
                email=c.email,
                first_name=c.first_name,
                last_name=c.last_name,
                company=c.company,
                website=c.website,
                language=c.language,
                category=c.category,
                phone=c.phone,
                country=c.country,
                city=c.city,
                linkedin_url=c.linkedin_url,
                facebook_url=c.facebook_url,
                instagram_url=c.instagram_url,
                twitter_url=c.twitter_url,
                custom_fields=c.custom_fields,
                tags=c.tags,
            )
            for c in request.contacts
        ]

        # 2. Create repository and use case (Dependency Injection)
        contact_repo = SQLAlchemyContactRepository(db)
        use_case = IngestContactsUseCase(contact_repo)

        # 3. Execute use case
        result: IngestContactsResult = use_case.execute(contact_dtos)

        # 4. Commit transaction
        db.commit()

        # 5. Return response
        return IngestContactsResponse(
            success=True,
            total_processed=result.total_processed,
            new_contacts=result.new_contacts,
            updated_contacts=result.updated_contacts,
            duplicates_skipped=result.duplicates_skipped,
            errors=result.errors,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/{tenant_id}", response_model=List[ContactResponse])
def list_contacts(
    tenant_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List contacts for a tenant.

    Query parameters:
    - limit: Maximum number of contacts to return (default: 100)
    """
    try:
        contact_repo = SQLAlchemyContactRepository(db)

        # For now, we'll use find_by_tags with no filters to get all contacts
        # TODO: Add proper list_all method to repository
        contacts = contact_repo.find_by_tags(tenant_id=tenant_id, limit=limit)

        return [
            ContactResponse(
                id=c.id,
                email=str(c.email),
                first_name=c.first_name,
                last_name=c.last_name,
                company=c.company,
                language=c.language.code,
                category=c.category,
                status=c.status.value,
                tags=[str(tag) for tag in c.tags],
            )
            for c in contacts
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list contacts: {str(e)}")


@router.get("/{tenant_id}/{contact_id}", response_model=ContactResponse)
def get_contact(
    tenant_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
):
    """Get a single contact by ID."""
    try:
        contact_repo = SQLAlchemyContactRepository(db)
        contact = contact_repo.find_by_id(contact_id)

        if not contact or contact.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Contact not found")

        return ContactResponse(
            id=contact.id,
            email=str(contact.email),
            first_name=contact.first_name,
            last_name=contact.last_name,
            company=contact.company,
            language=contact.language.code,
            category=contact.category,
            status=contact.status.value,
            tags=[str(tag) for tag in contact.tags],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contact: {str(e)}")
