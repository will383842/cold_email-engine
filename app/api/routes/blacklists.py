"""Blacklist status and manual check endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import BlacklistCheckResult, BlacklistEventResponse
from app.database import get_db
from app.models import IP, BlacklistEvent
from app.services.blacklist_checker import BlacklistChecker

router = APIRouter(
    prefix="/blacklists", tags=["Blacklists"], dependencies=[Depends(verify_api_key)]
)


@router.get("/events", response_model=list[BlacklistEventResponse])
def list_events(
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    """List blacklist events, optionally only active (not yet delisted)."""
    q = db.query(BlacklistEvent)
    if active_only:
        q = q.filter(BlacklistEvent.delisted_at.is_(None))
    return q.order_by(BlacklistEvent.listed_at.desc()).all()


@router.get("/events/{ip_id}", response_model=list[BlacklistEventResponse])
def list_events_for_ip(ip_id: int, db: Session = Depends(get_db)):
    """List blacklist events for a specific IP."""
    return (
        db.query(BlacklistEvent)
        .filter(BlacklistEvent.ip_id == ip_id)
        .order_by(BlacklistEvent.listed_at.desc())
        .all()
    )


@router.post("/check/{ip_id}", response_model=BlacklistCheckResult)
def check_ip(ip_id: int, db: Session = Depends(get_db)):
    """Manually trigger a blacklist check for a specific IP."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP not found")

    checker = BlacklistChecker(db)
    listed_on = checker.check_ip(ip.address)
    if listed_on:
        checker._record_listing(ip, listed_on)

    return BlacklistCheckResult(ip=ip.address, listed_on=listed_on)


@router.post("/check-all")
async def check_all_ips(db: Session = Depends(get_db)):
    """Manually trigger blacklist check for all active IPs."""
    checker = BlacklistChecker(db)
    results = await checker.check_all_ips()
    return {
        "checked": True,
        "listings": [
            {"ip": ip, "listed_on": bls} for ip, bls in results.items()
        ],
    }
