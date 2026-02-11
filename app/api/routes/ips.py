"""IP management CRUD + rotation trigger."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import IPCreate, IPResponse, IPUpdate
from app.database import get_db
from app.enums import IPStatus
from app.models import IP
from app.services.ip_manager import IPManager

router = APIRouter(prefix="/ips", tags=["IPs"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[IPResponse])
def list_ips(
    status: str | None = None,
    purpose: str | None = None,
    db: Session = Depends(get_db),
):
    """List all IPs, optionally filtered by status or purpose."""
    q = db.query(IP)
    if status:
        q = q.filter(IP.status == status)
    if purpose:
        q = q.filter(IP.purpose == purpose)
    return q.order_by(IP.id).all()


@router.post("", response_model=IPResponse, status_code=201)
def create_ip(payload: IPCreate, db: Session = Depends(get_db)):
    """Register a new IP."""
    existing = db.query(IP).filter(IP.address == payload.address).first()
    if existing:
        raise HTTPException(status_code=409, detail="IP already registered")

    ip = IP(
        address=payload.address,
        hostname=payload.hostname,
        purpose=payload.purpose.value,
        status=IPStatus.STANDBY.value,
        vmta_name=payload.vmta_name,
        pool_name=payload.pool_name,
        mailwizz_server_id=payload.mailwizz_server_id,
    )
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return ip


@router.get("/{ip_id}", response_model=IPResponse)
def get_ip(ip_id: int, db: Session = Depends(get_db)):
    """Get a single IP by ID."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP not found")
    return ip


@router.patch("/{ip_id}", response_model=IPResponse)
def update_ip(ip_id: int, payload: IPUpdate, db: Session = Depends(get_db)):
    """Update IP fields. For status changes use the transition endpoint."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data:
        # Status changes go through the state machine
        mgr = IPManager(db)
        new_status = IPStatus(update_data.pop("status"))
        if not mgr.transition(ip, new_status, reason="api_update"):
            raise HTTPException(status_code=400, detail="Invalid status transition")

    if "purpose" in update_data:
        update_data["purpose"] = update_data["purpose"].value

    for key, val in update_data.items():
        setattr(ip, key, val)
    db.commit()
    db.refresh(ip)
    return ip


@router.delete("/{ip_id}", status_code=204)
def delete_ip(ip_id: int, db: Session = Depends(get_db)):
    """Delete an IP record."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP not found")
    db.delete(ip)
    db.commit()


@router.post("/rotation", status_code=200)
async def trigger_rotation(db: Session = Depends(get_db)):
    """Manually trigger monthly rotation."""
    mgr = IPManager(db)
    result = mgr.monthly_rotation()
    return {"message": "Rotation complete", **result}
