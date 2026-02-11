"""Domain management CRUD + DNS validation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import DNSValidationResult, DomainCreate, DomainResponse, DomainUpdate
from app.database import get_db
from app.models import Domain
from app.services.dns_validator import DNSValidator

router = APIRouter(prefix="/domains", tags=["Domains"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[DomainResponse])
def list_domains(db: Session = Depends(get_db)):
    """List all domains."""
    return db.query(Domain).order_by(Domain.id).all()


@router.post("", response_model=DomainResponse, status_code=201)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    """Register a new domain."""
    existing = db.query(Domain).filter(Domain.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Domain already registered")

    domain = Domain(
        name=payload.name,
        purpose=payload.purpose.value,
        ip_id=payload.ip_id,
        dkim_selector=payload.dkim_selector,
        dkim_key_path=payload.dkim_key_path,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    """Get a single domain by ID."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.patch("/{domain_id}", response_model=DomainResponse)
def update_domain(domain_id: int, payload: DomainUpdate, db: Session = Depends(get_db)):
    """Update domain fields."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "purpose" in update_data:
        update_data["purpose"] = update_data["purpose"].value

    for key, val in update_data.items():
        setattr(domain, key, val)
    db.commit()
    db.refresh(domain)
    return domain


@router.delete("/{domain_id}", status_code=204)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    """Delete a domain record."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.delete(domain)
    db.commit()


@router.post("/{domain_id}/validate", response_model=DNSValidationResult)
def validate_domain_dns(domain_id: int, db: Session = Depends(get_db)):
    """Run DNS validation for a domain (SPF, DKIM, DMARC, PTR, MX)."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    validator = DNSValidator(db)
    results = validator.validate_domain(domain)
    return DNSValidationResult(domain=domain.name, **results)


@router.post("/validate-all")
def validate_all_dns(db: Session = Depends(get_db)):
    """Run DNS validation for all domains."""
    validator = DNSValidator(db)
    return validator.validate_all()
