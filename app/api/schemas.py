"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import AlertSeverity, BounceType, IPPurpose, IPStatus


# --- IP ---
class IPCreate(BaseModel):
    address: str
    hostname: str
    purpose: IPPurpose = IPPurpose.MARKETING
    vmta_name: str | None = None
    pool_name: str | None = None
    mailwizz_server_id: int | None = None

    # Champs pour le provisionnement automatique PowerMTA + MailWizz
    # Si sender_email est fourni, l'API crée automatiquement :
    #   1. Le virtual-mta PowerMTA sur le bon nœud VPS (via SSH)
    #   2. Le delivery server MailWizz correspondant (même FROM email)
    # CRITIQUE : sender_email doit être unique par IP (isolation 1 IP / 1 email)
    sender_email: str | None = None    # ex: contact@mail.hub-travelers.com
    from_name: str | None = None       # ex: "Hub Travelers" (affiché dans l'email)
    dkim_key_path: str | None = None   # Chemin DKIM sur VPS (auto-déduit si None)
    pmta_node_id: str | None = None    # vps2 | vps3 | vps4 (None = auto-routing)


class IPUpdate(BaseModel):
    purpose: IPPurpose | None = None
    status: IPStatus | None = None
    weight: int | None = Field(None, ge=0, le=100)
    vmta_name: str | None = None
    pool_name: str | None = None
    mailwizz_server_id: int | None = None


class IPResponse(BaseModel):
    id: int
    address: str
    hostname: str
    purpose: str
    status: str
    weight: int
    vmta_name: str | None
    pool_name: str | None
    mailwizz_server_id: int | None
    sender_email: str | None          # Email expéditeur unique (1 IP = 1 email)
    pmta_node_id: str | None          # vps2 | vps3 | vps4
    quarantine_until: datetime | None
    status_changed_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


# --- Domain ---
class DomainCreate(BaseModel):
    name: str
    purpose: IPPurpose = IPPurpose.MARKETING
    ip_id: int | None = None
    dkim_selector: str = "default"
    dkim_key_path: str | None = None


class DomainUpdate(BaseModel):
    purpose: IPPurpose | None = None
    ip_id: int | None = None
    dkim_selector: str | None = None
    dkim_key_path: str | None = None


class DomainResponse(BaseModel):
    id: int
    name: str
    purpose: str
    ip_id: int | None
    dkim_selector: str | None
    spf_valid: bool
    dkim_valid: bool
    dmarc_valid: bool
    ptr_valid: bool
    last_dns_check: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class DNSValidationResult(BaseModel):
    domain: str
    spf: bool
    dkim: bool
    dmarc: bool
    ptr: bool
    mx: bool


# --- Warmup ---
class WarmupPlanResponse(BaseModel):
    id: int
    ip_id: int
    phase: str
    started_at: datetime | None
    current_daily_quota: int
    target_daily_quota: int
    bounce_rate_7d: float
    spam_rate_7d: float
    paused: bool
    pause_until: datetime | None

    model_config = {"from_attributes": True}


class WarmupStatsRecord(BaseModel):
    sent: int
    delivered: int
    bounced: int
    complaints: int
    opens: int = 0
    clicks: int = 0


# --- Blacklist ---
class BlacklistEventResponse(BaseModel):
    id: int
    ip_id: int
    blacklist_name: str
    listed_at: datetime | None
    delisted_at: datetime | None
    auto_recovered: bool

    model_config = {"from_attributes": True}


class BlacklistCheckResult(BaseModel):
    ip: str
    listed_on: list[str]


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    issues: list[str] = []
    pmta_running: bool | None = None
    pmta_queue_size: int | None = None
    disk_usage_pct: float | None = None
    ram_usage_pct: float | None = None
    last_check: str | None = None


# --- Webhook ---
class PMTABouncePayload(BaseModel):
    email: str
    bounce_type: BounceType = BounceType.HARD
    reason: str = ""
    source_ip: str = ""
    vmta: str = ""


class PMTADeliveryPayload(BaseModel):
    domain: str
    count: int = Field(default=1, ge=1)


# --- Validation ---
class EmailValidationRequest(BaseModel):
    emails: list[str] = Field(..., min_length=1, max_length=10000)


class EmailValidationResult(BaseModel):
    email: str
    valid: bool
    reason: str | None = None


class EmailValidationResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    results: list[EmailValidationResult]


# --- Alert ---
class AlertLogResponse(BaseModel):
    id: int
    timestamp: datetime
    severity: str
    category: str
    message: str
    telegram_sent: bool

    model_config = {"from_attributes": True}
