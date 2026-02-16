"""Tags API v2 - CRUD operations for contact tags."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tag
from .auth import no_auth  # Simple auth for internal tool

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CreateTagRequest(BaseModel):
    """Request schema for creating a tag."""

    tenant_id: int
    slug: str
    name: str
    description: Optional[str] = None


class UpdateTagRequest(BaseModel):
    """Request schema for updating a tag."""

    name: Optional[str] = None
    description: Optional[str] = None


class TagResponse(BaseModel):
    """Response schema for a tag."""

    id: int
    tenant_id: int
    slug: str
    name: str
    description: Optional[str]
    contact_count: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/", dependencies=[Depends(no_auth)])
def create_tag(
    request: CreateTagRequest,
    db: Session = Depends(get_db),
):
    """Create a new tag."""
    try:
        # Check if slug already exists for tenant
        existing = (
            db.query(Tag)
            .filter(Tag.tenant_id == request.tenant_id, Tag.slug == request.slug)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Tag with slug '{request.slug}' already exists for this tenant",
            )

        tag = Tag(
            tenant_id=request.tenant_id,
            slug=request.slug,
            name=request.name,
            description=request.description,
        )

        db.add(tag)
        db.commit()
        db.refresh(tag)

        return {
            "success": True,
            "tag": {
                "id": tag.id,
                "slug": tag.slug,
                "name": tag.name,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create tag: {str(e)}")


@router.get("/{tenant_id}", response_model=List[TagResponse], dependencies=[Depends(no_auth)])
def list_tags(
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """List all tags for a tenant."""
    try:
        from sqlalchemy import func
        from app.models import ContactTag

        # Get tags with contact counts
        tags_with_counts = (
            db.query(
                Tag,
                func.count(ContactTag.contact_id).label("contact_count"),
            )
            .outerjoin(ContactTag, Tag.id == ContactTag.tag_id)
            .filter(Tag.tenant_id == tenant_id)
            .group_by(Tag.id)
            .all()
        )

        return [
            TagResponse(
                id=tag.id,
                tenant_id=tag.tenant_id,
                slug=tag.slug,
                name=tag.name,
                description=tag.description,
                contact_count=count,
            )
            for tag, count in tags_with_counts
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tags: {str(e)}")


@router.get("/{tenant_id}/{tag_id}", response_model=TagResponse, dependencies=[Depends(no_auth)])
def get_tag(
    tenant_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
):
    """Get a single tag with contact count."""
    try:
        from sqlalchemy import func
        from app.models import ContactTag

        result = (
            db.query(
                Tag,
                func.count(ContactTag.contact_id).label("contact_count"),
            )
            .outerjoin(ContactTag, Tag.id == ContactTag.tag_id)
            .filter(Tag.id == tag_id, Tag.tenant_id == tenant_id)
            .group_by(Tag.id)
            .first()
        )

        if not result:
            raise HTTPException(status_code=404, detail="Tag not found")

        tag, count = result

        return TagResponse(
            id=tag.id,
            tenant_id=tag.tenant_id,
            slug=tag.slug,
            name=tag.name,
            description=tag.description,
            contact_count=count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tag: {str(e)}")


@router.put("/{tenant_id}/{tag_id}", dependencies=[Depends(no_auth)])
def update_tag(
    tenant_id: int,
    tag_id: int,
    request: UpdateTagRequest,
    db: Session = Depends(get_db),
):
    """Update a tag."""
    try:
        tag = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id).first()

        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Update fields
        if request.name is not None:
            tag.name = request.name
        if request.description is not None:
            tag.description = request.description

        db.commit()
        db.refresh(tag)

        return {
            "success": True,
            "tag": {
                "id": tag.id,
                "slug": tag.slug,
                "name": tag.name,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update tag: {str(e)}")


@router.delete("/{tenant_id}/{tag_id}", dependencies=[Depends(no_auth)])
def delete_tag(
    tenant_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
):
    """Delete a tag (also removes all contact associations)."""
    try:
        from app.models import ContactTag

        tag = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id).first()

        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Delete contact associations first
        db.query(ContactTag).filter(ContactTag.tag_id == tag_id).delete()

        # Delete tag
        db.delete(tag)
        db.commit()

        return {"success": True, "message": "Tag deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete tag: {str(e)}")
