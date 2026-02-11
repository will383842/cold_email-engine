"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import HealthResponse
from app.database import get_db
from app.services.health_monitor import HealthMonitor

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    """System health status (no API key required)."""
    monitor = HealthMonitor(db)
    return monitor.get_status_summary()
