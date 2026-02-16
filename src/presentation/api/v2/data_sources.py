"""Data Sources API v2 - CRUD operations for contact data sources."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DataSource
from app.enums import DataSourceType
from .auth import no_auth  # Simple auth for internal tool

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CreateDataSourceRequest(BaseModel):
    """Request schema for creating a data source."""

    tenant_id: int
    name: str
    type: str  # scraper-pro, backlink-engine, csv-import, manual
    config: Optional[dict] = None


class UpdateDataSourceRequest(BaseModel):
    """Request schema for updating a data source."""

    name: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None


class DataSourceResponse(BaseModel):
    """Response schema for a data source."""

    id: int
    tenant_id: int
    name: str
    type: str
    is_active: bool
    contact_count: int
    last_sync_at: Optional[datetime]
    created_at: datetime


class SyncDataSourceRequest(BaseModel):
    """Request to trigger data source sync."""

    force: bool = False


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/", dependencies=[Depends(no_auth)])
def create_data_source(
    request: CreateDataSourceRequest,
    db: Session = Depends(get_db),
):
    """Create a new data source."""
    try:
        # Validate type
        try:
            source_type = DataSourceType(request.type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data source type. Must be one of: {[t.value for t in DataSourceType]}",
            )

        data_source = DataSource(
            tenant_id=request.tenant_id,
            name=request.name,
            type=source_type,
            config=request.config or {},
            is_active=True,
        )

        db.add(data_source)
        db.commit()
        db.refresh(data_source)

        return {
            "success": True,
            "data_source": {
                "id": data_source.id,
                "name": data_source.name,
                "type": data_source.type.value,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create data source: {str(e)}")


@router.get("/{tenant_id}", response_model=List[DataSourceResponse], dependencies=[Depends(no_auth)])
def list_data_sources(
    tenant_id: int,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    """List all data sources for a tenant."""
    try:
        from sqlalchemy import func
        from app.models import Contact

        # Get data sources with contact counts
        query = (
            db.query(
                DataSource,
                func.count(Contact.id).label("contact_count"),
            )
            .outerjoin(Contact, DataSource.id == Contact.data_source_id)
            .filter(DataSource.tenant_id == tenant_id)
        )

        if active_only:
            query = query.filter(DataSource.is_active == True)

        sources_with_counts = query.group_by(DataSource.id).all()

        return [
            DataSourceResponse(
                id=source.id,
                tenant_id=source.tenant_id,
                name=source.name,
                type=source.type.value,
                is_active=source.is_active,
                contact_count=count,
                last_sync_at=source.last_sync_at,
                created_at=source.created_at,
            )
            for source, count in sources_with_counts
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list data sources: {str(e)}")


@router.get("/{tenant_id}/{source_id}", response_model=DataSourceResponse, dependencies=[Depends(no_auth)])
def get_data_source(
    tenant_id: int,
    source_id: int,
    db: Session = Depends(get_db),
):
    """Get a single data source with contact count."""
    try:
        from sqlalchemy import func
        from app.models import Contact

        result = (
            db.query(
                DataSource,
                func.count(Contact.id).label("contact_count"),
            )
            .outerjoin(Contact, DataSource.id == Contact.data_source_id)
            .filter(DataSource.id == source_id, DataSource.tenant_id == tenant_id)
            .group_by(DataSource.id)
            .first()
        )

        if not result:
            raise HTTPException(status_code=404, detail="Data source not found")

        source, count = result

        return DataSourceResponse(
            id=source.id,
            tenant_id=source.tenant_id,
            name=source.name,
            type=source.type.value,
            is_active=source.is_active,
            contact_count=count,
            last_sync_at=source.last_sync_at,
            created_at=source.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data source: {str(e)}")


@router.put("/{tenant_id}/{source_id}", dependencies=[Depends(no_auth)])
def update_data_source(
    tenant_id: int,
    source_id: int,
    request: UpdateDataSourceRequest,
    db: Session = Depends(get_db),
):
    """Update a data source."""
    try:
        source = (
            db.query(DataSource)
            .filter(DataSource.id == source_id, DataSource.tenant_id == tenant_id)
            .first()
        )

        if not source:
            raise HTTPException(status_code=404, detail="Data source not found")

        # Update fields
        if request.name is not None:
            source.name = request.name
        if request.is_active is not None:
            source.is_active = request.is_active
        if request.config is not None:
            source.config = request.config

        db.commit()
        db.refresh(source)

        return {
            "success": True,
            "data_source": {
                "id": source.id,
                "name": source.name,
                "type": source.type.value,
                "is_active": source.is_active,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update data source: {str(e)}")


@router.post("/{tenant_id}/{source_id}/sync", dependencies=[Depends(no_auth)])
def sync_data_source(
    tenant_id: int,
    source_id: int,
    request: SyncDataSourceRequest,
    db: Session = Depends(get_db),
):
    """
    Trigger a sync for a data source.

    This would typically trigger a background job to fetch new contacts
    from Scraper-Pro, Backlink Engine, etc.
    """
    try:
        source = (
            db.query(DataSource)
            .filter(DataSource.id == source_id, DataSource.tenant_id == tenant_id)
            .first()
        )

        if not source:
            raise HTTPException(status_code=404, detail="Data source not found")

        if not source.is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot sync inactive data source. Activate it first.",
            )

        # Update last sync timestamp
        from datetime import datetime

        source.last_sync_at = datetime.utcnow()
        db.commit()

        # TODO: Trigger background job based on source type
        # if source.type == DataSourceType.SCRAPER_PRO:
        #     from src.infrastructure.background.tasks import sync_scraper_pro_task
        #     sync_scraper_pro_task.delay(source_id)
        # elif source.type == DataSourceType.BACKLINK_ENGINE:
        #     from src.infrastructure.background.tasks import sync_backlink_engine_task
        #     sync_backlink_engine_task.delay(source_id)

        return {
            "success": True,
            "message": f"Sync triggered for {source.name}",
            "source_id": source.id,
            "type": source.type.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync data source: {str(e)}")


@router.delete("/{tenant_id}/{source_id}", dependencies=[Depends(no_auth)])
def delete_data_source(
    tenant_id: int,
    source_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a data source.

    WARNING: This will orphan all contacts from this source.
    Consider soft-delete or reassigning contacts first.
    """
    try:
        source = (
            db.query(DataSource)
            .filter(DataSource.id == source_id, DataSource.tenant_id == tenant_id)
            .first()
        )

        if not source:
            raise HTTPException(status_code=404, detail="Data source not found")

        # Check if it has contacts
        from app.models import Contact

        contact_count = db.query(Contact).filter(Contact.data_source_id == source_id).count()

        if contact_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete data source with {contact_count} contacts. Deactivate it instead or reassign contacts first.",
            )

        db.delete(source)
        db.commit()

        return {"success": True, "message": "Data source deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete data source: {str(e)}")
