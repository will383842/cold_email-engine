"""Warmup plan management and progress tracking."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import WarmupPlanResponse, WarmupStatsRecord
from app.database import get_db
from app.enums import IPStatus
from app.models import IP, WarmupDailyStat, WarmupPlan
from app.services.warmup_engine import WarmupEngine

router = APIRouter(prefix="/warmup", tags=["Warmup"], dependencies=[Depends(verify_api_key)])


@router.get("/plans", response_model=list[WarmupPlanResponse])
def list_plans(db: Session = Depends(get_db)):
    """List all warmup plans."""
    return db.query(WarmupPlan).order_by(WarmupPlan.id).all()


@router.get("/plans/{plan_id}", response_model=WarmupPlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a specific warmup plan."""
    plan = db.query(WarmupPlan).filter(WarmupPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Warmup plan not found")
    return plan


@router.post("/plans/{ip_id}", response_model=WarmupPlanResponse, status_code=201)
def create_plan(ip_id: int, db: Session = Depends(get_db)):
    """Create a warmup plan for an IP (sets IP to WARMING state)."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP not found")
    if ip.status not in (IPStatus.STANDBY.value, IPStatus.RESTING.value):
        raise HTTPException(
            status_code=400,
            detail=f"IP must be in standby or resting state, currently: {ip.status}",
        )

    existing = db.query(WarmupPlan).filter(WarmupPlan.ip_id == ip_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Warmup plan already exists for this IP")

    ip.status = IPStatus.WARMING.value
    engine = WarmupEngine(db)
    plan = engine.create_plan(ip)
    return plan


@router.post("/plans/{plan_id}/stats")
def record_stats(plan_id: int, payload: WarmupStatsRecord, db: Session = Depends(get_db)):
    """Record daily sending stats for a warmup plan."""
    plan = db.query(WarmupPlan).filter(WarmupPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    engine = WarmupEngine(db)
    stat = engine.record_daily_stats(
        plan,
        sent=payload.sent,
        delivered=payload.delivered,
        bounced=payload.bounced,
        complaints=payload.complaints,
        opens=payload.opens,
        clicks=payload.clicks,
    )
    return {"id": stat.id, "date": stat.date.isoformat()}


@router.get("/plans/{plan_id}/stats")
def get_plan_stats(plan_id: int, db: Session = Depends(get_db)):
    """Get daily stats for a warmup plan."""
    plan = db.query(WarmupPlan).filter(WarmupPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    stats = (
        db.query(WarmupDailyStat)
        .filter(WarmupDailyStat.plan_id == plan_id)
        .order_by(WarmupDailyStat.date.desc())
        .all()
    )
    return [
        {
            "date": s.date.isoformat(),
            "sent": s.sent,
            "delivered": s.delivered,
            "bounced": s.bounced,
            "complaints": s.complaints,
            "opens": s.opens,
            "clicks": s.clicks,
        }
        for s in stats
    ]


@router.post("/plans/{plan_id}/pause")
def pause_plan(plan_id: int, db: Session = Depends(get_db)):
    """Pause a warmup plan."""
    plan = db.query(WarmupPlan).filter(WarmupPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.paused = True
    db.commit()
    return {"message": "Plan paused", "plan_id": plan_id}


@router.post("/plans/{plan_id}/resume")
def resume_plan(plan_id: int, db: Session = Depends(get_db)):
    """Resume a paused warmup plan."""
    plan = db.query(WarmupPlan).filter(WarmupPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.paused = False
    plan.pause_until = None
    db.commit()
    return {"message": "Plan resumed", "plan_id": plan_id}
