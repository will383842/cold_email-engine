"""
IP Management — CRUD + provisionnement atomique multi-nœuds PowerMTA + MailWizz MySQL.

Architecture :
  POST /ips → auto-routing vers VPS2 ou VPS3 selon le domaine du hostname
  Provisionnement : PowerMTA (SSH) + MailWizz (MySQL direct) en une seule opération
  Rollback : si MailWizz échoue → suppression du vmta PowerMTA automatique
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.api.schemas import IPCreate, IPResponse, IPUpdate
from app.config import settings
from app.database import get_db
from app.enums import IPStatus
from app.models import IP
from app.services.ip_manager import IPManager
from app.services.mailwizz_db import mailwizz_db
from app.services.powermta_config import MultiPmtaManager, domain_to_vmta, get_pmta_manager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ips", tags=["IPs"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[IPResponse])
def list_ips(
    status: str | None = None,
    purpose: str | None = None,
    pmta_node_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Liste les IPs avec filtres optionnels par statut, purpose, nœud PowerMTA."""
    q = db.query(IP)
    if status:
        q = q.filter(IP.status == status)
    if purpose:
        q = q.filter(IP.purpose == purpose)
    if pmta_node_id:
        q = q.filter(IP.pmta_node_id == pmta_node_id)
    return q.order_by(IP.id).all()


@router.post("", response_model=IPResponse, status_code=201)
async def create_ip(payload: IPCreate, db: Session = Depends(get_db)):
    """
    Enregistre une nouvelle IP et provisionne PowerMTA + MailWizz atomiquement.

    Flux complet :
    1. Auto-routing : hostname → nœud PowerMTA responsable (vps2 ou vps3)
    2. PowerMTA : ajout virtual-mta + pattern-list via SSH sur le bon nœud
    3. MailWizz : création delivery server via MySQL direct (même FROM email)
    4. Rollback complet si étape 2 ou 3 échoue

    COHÉRENCE GARANTIE :
      sender_email PowerMTA (pattern-list) = from_email MailWizz (delivery server)
      1 IP → 1 email unique → isolation parfaite de réputation
    """
    # Vérifier doublon
    existing = db.query(IP).filter(IP.address == payload.address).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"IP {payload.address} déjà enregistrée")

    # Déduire le vmta_name depuis le hostname si non fourni
    vmta_name = payload.vmta_name
    if not vmta_name and payload.hostname:
        # mail.hub-travelers.com → hub-travelers.com → vmta-hub-travelers
        parts = payload.hostname.split(".")
        if len(parts) >= 3 and parts[0] in ("mail", "smtp", "send", "out"):
            base_domain = ".".join(parts[1:])
        else:
            base_domain = payload.hostname
        vmta_name = domain_to_vmta(base_domain)

    if not vmta_name:
        vmta_name = f"vmta-{payload.address.replace('.', '-')}"

    pmta_provisioned = False
    mw_server_id: int | None = payload.mailwizz_server_id
    used_node_id: str = "vps2"

    # ─────────────────────────────────────────────────────────
    # PROVISIONNEMENT ATOMIQUE (si sender_email fourni)
    # ─────────────────────────────────────────────────────────
    if payload.sender_email:
        pmta_mgr = get_pmta_manager()

        # Étape 1 : PowerMTA → virtual-mta + pattern-list (sur le bon nœud)
        pmta_ok, used_node_id = pmta_mgr.add_vmta_with_pattern(
            vmta_name=vmta_name,
            ip_address=payload.address,
            hostname=payload.hostname,
            sender_email=payload.sender_email,
            dkim_key_path=payload.dkim_key_path,
            node_id=payload.pmta_node_id,  # None = auto-routing par domaine
        )

        if not pmta_ok:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Échec provisionnement PowerMTA pour {payload.address}. "
                    f"Nœud cible : {used_node_id or 'auto'}. "
                    "Vérifier PMTA_VPS2_HOST/PMTA_VPS3_HOST et la clé SSH."
                ),
            )
        pmta_provisioned = True
        logger.info("ip_pmta_provisioned", ip=payload.address, node=used_node_id, vmta=vmta_name)

        # Étape 2 : MailWizz → delivery server via MySQL direct
        # hostname MailWizz = IP du nœud PowerMTA (pour le relay SMTP)
        node_conf = settings.get_node_by_id(used_node_id)
        pmta_smtp_host = node_conf["host"] if node_conf else settings.PMTA_VPS2_HOST
        smtp_port = node_conf["smtp_port"] if node_conf else settings.PMTA_SMTP_PORT

        ds_name = f"PowerMTA {vmta_name} [{used_node_id}]"
        mw_server_id = await mailwizz_db.create_delivery_server(
            name=ds_name,
            hostname=pmta_smtp_host,
            port=smtp_port,
            from_email=payload.sender_email,
            from_name=payload.from_name or settings.MAILWIZZ_FROM_NAME,
            hourly_quota=settings.MAILWIZZ_DS_HOURLY_QUOTA,
            max_connection_messages=settings.MAILWIZZ_DS_MAX_CONN_MESSAGES,
        )

        if mw_server_id is None:
            # ROLLBACK PowerMTA
            logger.warning(
                "ip_provision_rollback",
                reason="mailwizz_create_failed",
                ip=payload.address,
                sender=payload.sender_email,
                node=used_node_id,
            )
            pmta_mgr.remove_vmta_with_pattern(
                vmta_name=vmta_name,
                sender_email=payload.sender_email,
                node_id=used_node_id,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Échec création delivery server MailWizz pour {payload.sender_email}. "
                    "PowerMTA rollback effectué. "
                    "Vérifier MAILWIZZ_DB_HOST et MAILWIZZ_DB_PASSWORD."
                ),
            )

        logger.info(
            "ip_fully_provisioned",
            ip=payload.address,
            vmta=vmta_name,
            node=used_node_id,
            sender=payload.sender_email,
            mw_server_id=mw_server_id,
        )

    # ─────────────────────────────────────────────────────────
    # ENREGISTREMENT EN BASE
    # ─────────────────────────────────────────────────────────
    ip = IP(
        address=payload.address,
        hostname=payload.hostname,
        purpose=payload.purpose.value,
        status=IPStatus.STANDBY.value,
        vmta_name=vmta_name,
        pool_name=payload.pool_name,
        mailwizz_server_id=mw_server_id,
        sender_email=payload.sender_email,
        pmta_node_id=used_node_id,
    )
    db.add(ip)
    db.commit()
    db.refresh(ip)
    return ip


@router.get("/nodes", tags=["IPs"])
def list_pmta_nodes():
    """Liste les nœuds PowerMTA configurés et leur statut."""
    pmta_mgr = get_pmta_manager()
    return pmta_mgr.health_check_all()


@router.get("/{ip_id}", response_model=IPResponse)
def get_ip(ip_id: int, db: Session = Depends(get_db)):
    """Retourne une IP par son ID."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP non trouvée")
    return ip


@router.patch("/{ip_id}", response_model=IPResponse)
def update_ip(ip_id: int, payload: IPUpdate, db: Session = Depends(get_db)):
    """Met à jour les champs d'une IP. Les changements de statut passent par la state machine."""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP non trouvée")

    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data:
        mgr = IPManager(db)
        new_status = IPStatus(update_data.pop("status"))
        if not mgr.transition(ip, new_status, reason="api_update"):
            raise HTTPException(status_code=400, detail="Transition de statut invalide")

    if "purpose" in update_data:
        update_data["purpose"] = update_data["purpose"].value

    for key, val in update_data.items():
        setattr(ip, key, val)
    db.commit()
    db.refresh(ip)
    return ip


@router.delete("/{ip_id}", status_code=204)
async def delete_ip(
    ip_id: int,
    deprovision: bool = True,
    db: Session = Depends(get_db),
):
    """
    Supprime une IP et déprovisionne PowerMTA + MailWizz automatiquement.

    Args:
        deprovision: Si True (défaut), supprime le vmta PowerMTA et le delivery server MailWizz.
    """
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP non trouvée")

    if deprovision:
        # Supprimer delivery server MailWizz via MySQL
        if ip.mailwizz_server_id:
            deleted_mw = await mailwizz_db.delete_delivery_server(ip.mailwizz_server_id)
            if not deleted_mw:
                logger.warning(
                    "ip_deprovision_mw_failed",
                    ip=ip.address,
                    server_id=ip.mailwizz_server_id,
                )

        # Supprimer virtual-mta + pattern-list PowerMTA sur le bon nœud
        if ip.vmta_name:
            pmta_mgr = get_pmta_manager()
            node_id = ip.pmta_node_id or "vps2"

            # Récupérer l'email depuis la base ou le nœud PowerMTA
            sender_email = ip.sender_email
            if not sender_email:
                node = pmta_mgr.get_node(node_id)
                if node:
                    sender_email = node.get_sender_for_vmta(ip.vmta_name)

            if sender_email:
                pmta_mgr.remove_vmta_with_pattern(
                    vmta_name=ip.vmta_name,
                    sender_email=sender_email,
                    node_id=node_id,
                )
            else:
                # Supprimer juste le bloc vmta si pas d'email trouvé
                node = pmta_mgr.get_node(node_id)
                if node:
                    node._remove_vmta_block_only(ip.vmta_name)

    db.delete(ip)
    db.commit()
    logger.info("ip_deleted", ip=ip.address, deprovision=deprovision)


@router.post("/rotation", status_code=200)
async def trigger_rotation(db: Session = Depends(get_db)):
    """Déclenche une rotation manuelle des IPs."""
    mgr = IPManager(db)
    result = mgr.monthly_rotation()
    return {"message": "Rotation effectuée", **result}
