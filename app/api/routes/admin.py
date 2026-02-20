"""
Console d'administration — Licences PowerMTA, MailWizz, isolation clients.

Endpoints :
  GET  /admin/pmta/nodes                   → État des nœuds + licence active
  PUT  /admin/pmta/{node_id}/license       → Upload licence PowerMTA sur un VPS
  PUT  /admin/pmta/all/license             → Même licence sur tous les VPS actifs
  GET  /admin/mailwizz/license             → Affiche licence MailWizz enregistrée
  PUT  /admin/mailwizz/license             → Met à jour la clé de licence MailWizz
  GET  /admin/mailwizz/customers           → Liste les clients MailWizz
  POST /admin/mailwizz/customers/{id}/assign-servers  → Assigner delivery servers à un client
  GET  /admin/mailwizz/isolation           → Vérifier l'isolation par client
"""

import os
import subprocess
import tempfile

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import verify_api_key
from app.config import settings
from app.database import get_db
from app.services.mailwizz_db import mailwizz_db
from app.services.powermta_config import get_pmta_manager

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_api_key)],
)

PMTA_LICENSE_PATH = "/etc/pmta/license"


# ═══════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════

class MailwizzLicenseUpdate(BaseModel):
    license_key: str


class ServerAssignment(BaseModel):
    customer_id: int
    server_ids: list[int]


# ═══════════════════════════════════════════════════════════
# POWERMTA — Licences
# ═══════════════════════════════════════════════════════════

@router.get("/pmta/nodes")
def get_pmta_nodes_status():
    """
    Liste tous les nœuds PowerMTA avec leur statut SSH + licence active.

    Retourne pour chaque nœud :
      - node_id     : vps2, vps3, vps4...
      - host        : IP du VPS
      - reachable   : SSH accessible ?
      - pmta_running: PowerMTA actif ?
      - queue_size  : Emails en attente
      - domains     : Domaines gérés
      - license_info: Infos licence lues sur le VPS (licensee, expires)
    """
    mgr = get_pmta_manager()
    nodes_status = []

    for node_id, node in mgr._nodes.items():
        status = {
            "node_id": node_id,
            "host": node.host,
            "domains": node.domains,
            "reachable": False,
            "pmta_running": False,
            "queue_size": -1,
            "license_info": None,
        }

        try:
            status["reachable"] = node.is_reachable()
            if status["reachable"]:
                status["pmta_running"] = node.is_running()
                status["queue_size"] = node.get_queue_size()
                # Lire les infos de licence directement sur le VPS
                rc, stdout, _ = node._ssh(
                    f"grep -E 'licensee|expires|serial|options' {PMTA_LICENSE_PATH} 2>/dev/null"
                )
                if rc == 0 and stdout.strip():
                    license_lines = {}
                    for line in stdout.strip().splitlines():
                        if ":" in line:
                            key, _, val = line.partition(":")
                            license_lines[key.strip()] = val.strip()
                    status["license_info"] = license_lines
        except Exception as exc:
            logger.warning("admin_node_status_error", node=node_id, error=str(exc))

        nodes_status.append(status)

    return {"nodes": nodes_status, "total": len(nodes_status)}


@router.put("/pmta/{node_id}/license")
async def upload_pmta_license(
    node_id: str,
    license_file: UploadFile = File(..., description="Fichier licence PowerMTA"),
):
    """
    Upload une nouvelle licence PowerMTA sur un nœud spécifique.

    Processus :
      1. Lit le fichier uploadé
      2. SCP vers /etc/pmta/license sur le VPS ciblé
      3. Redémarre PowerMTA (pmta restart)
      4. Vérifie que PowerMTA redémarre correctement

    Args:
        node_id: Identifiant du nœud (vps2, vps3, vps4, vps5, vps6)
        license_file: Fichier de licence PowerMTA (format texte)
    """
    mgr = get_pmta_manager()
    node = mgr.get_node(node_id)

    if not node:
        raise HTTPException(
            status_code=404,
            detail=f"Nœud '{node_id}' non trouvé. Nœuds disponibles : {list(mgr._nodes.keys())}",
        )

    if not node.is_reachable():
        raise HTTPException(
            status_code=503,
            detail=f"Nœud '{node_id}' ({node.host}) inaccessible via SSH.",
        )

    # Lire le contenu du fichier uploadé
    license_content = await license_file.read()
    if not license_content:
        raise HTTPException(status_code=400, detail="Fichier licence vide.")

    # Écrire dans un fichier temporaire local
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".license", delete=False, prefix=f"pmta_{node_id}_"
        ) as tmp:
            tmp.write(license_content)
            tmp_path = tmp.name

        # SCP vers le VPS
        ok = node._scp_push(tmp_path, PMTA_LICENSE_PATH)
        if not ok:
            raise HTTPException(
                status_code=503,
                detail=f"Échec SCP vers {node.host}:{PMTA_LICENSE_PATH}",
            )

        # Permissions correctes sur la licence
        node._ssh(f"chmod 644 {PMTA_LICENSE_PATH}")

        # Redémarrer PowerMTA
        rc, stdout, stderr = node._ssh("systemctl restart pmta 2>&1 || pmta restart 2>&1")
        if rc != 0:
            logger.warning(
                "pmta_restart_after_license_failed",
                node=node_id,
                stdout=stdout,
                stderr=stderr,
            )
            # Pas d'erreur fatale — la licence est installée mais pmta peut prendre du temps
            return {
                "success": True,
                "node_id": node_id,
                "host": node.host,
                "license_installed": True,
                "pmta_restarted": False,
                "warning": "Licence installée mais restart PowerMTA a échoué. Vérifier manuellement.",
                "hint": f"ssh root@{node.host} 'systemctl status pmta'",
            }

        import asyncio
        await asyncio.sleep(3)
        running = node.is_running()

        logger.info("pmta_license_updated", node=node_id, host=node.host)
        return {
            "success": True,
            "node_id": node_id,
            "host": node.host,
            "license_installed": True,
            "pmta_restarted": True,
            "pmta_running": running,
        }

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.put("/pmta/all/license")
async def upload_pmta_license_all_nodes(
    license_file: UploadFile = File(..., description="Fichier licence PowerMTA (même pour tous)"),
):
    """
    Déploie la même licence PowerMTA sur TOUS les nœuds actifs.

    Utile quand tu utilises une licence unique pour tous les VPS temporairement.
    Chaque nœud accessible recevra la licence et redémarrera.

    Retourne un rapport par nœud (succès / échec / injoignable).
    """
    mgr = get_pmta_manager()

    # Lire le contenu une seule fois
    license_content = await license_file.read()
    if not license_content:
        raise HTTPException(status_code=400, detail="Fichier licence vide.")

    results = []

    for node_id, node in mgr._nodes.items():
        result = {"node_id": node_id, "host": node.host, "success": False, "detail": ""}

        try:
            if not node.is_reachable():
                result["detail"] = "Inaccessible via SSH — ignoré"
                results.append(result)
                continue

            # Écrire fichier temporaire
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".license", delete=False, prefix=f"pmta_{node_id}_"
                ) as tmp:
                    tmp.write(license_content)
                    tmp_path = tmp.name

                ok = node._scp_push(tmp_path, PMTA_LICENSE_PATH)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            if not ok:
                result["detail"] = f"SCP échoué vers {node.host}"
                results.append(result)
                continue

            node._ssh(f"chmod 644 {PMTA_LICENSE_PATH}")
            rc, _, _ = node._ssh("systemctl restart pmta 2>&1 || pmta restart 2>&1")

            result["success"] = True
            result["pmta_restarted"] = rc == 0
            result["detail"] = "Licence installée" + (" + PowerMTA redémarré" if rc == 0 else " (restart manuel nécessaire)")

        except Exception as exc:
            result["detail"] = f"Erreur : {exc}"

        results.append(result)

    success_count = sum(1 for r in results if r["success"])
    logger.info("pmta_license_all_updated", success=success_count, total=len(results))

    return {
        "total_nodes": len(results),
        "success_count": success_count,
        "results": results,
    }


# ═══════════════════════════════════════════════════════════
# MAILWIZZ — Licence + isolation clients
# ═══════════════════════════════════════════════════════════

@router.get("/mailwizz/license")
async def get_mailwizz_license():
    """
    Affiche la clé de licence MailWizz enregistrée dans la base.

    Note : La licence MailWizz est gérée dans l'interface admin MailWizz
    (System Settings > License). Cet endpoint permet de la consulter/stocker
    comme référence dans notre système.
    """
    license_key = await mailwizz_db.get_option("system.license_key")
    return {
        "license_key": license_key or "(non configurée)",
        "mailwizz_admin_url": "http://sos-holidays.com/backend/index.php/settings/index",
        "note": "La licence MailWizz s'active dans l'interface admin MailWizz. "
                "Cet endpoint stocke la référence dans notre base pour suivi.",
    }


@router.put("/mailwizz/license")
async def update_mailwizz_license(payload: MailwizzLicenseUpdate):
    """
    Met à jour la clé de licence MailWizz.

    Stocke la clé dans la table mw_option pour référence.
    L'activation réelle se fait dans l'interface MailWizz admin.
    """
    if not payload.license_key.strip():
        raise HTTPException(status_code=400, detail="Clé de licence vide.")

    ok = await mailwizz_db.set_option("system.license_key", payload.license_key.strip())
    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Impossible d'écrire dans la base MailWizz. Vérifier MAILWIZZ_DB_PASSWORD.",
        )

    return {
        "success": True,
        "license_key": payload.license_key.strip(),
        "note": "Clé enregistrée. Pour activation complète : interface admin MailWizz.",
    }


@router.get("/mailwizz/customers")
async def list_mailwizz_customers():
    """
    Liste les clients MailWizz avec leurs delivery servers assignés.

    Permet de vérifier l'isolation :
      - Client 1 (customer_id=1) → delivery servers VPS2 uniquement
      - Client 2 (customer_id=2) → delivery servers VPS3 uniquement

    Si les clients partagent les mêmes servers → risque de contamination réputation.
    """
    customers = await mailwizz_db.list_customers_with_servers()
    return {"customers": customers}


@router.post("/mailwizz/customers/{customer_id}/assign-servers")
async def assign_delivery_servers(customer_id: int, payload: ServerAssignment):
    """
    Assigne des delivery servers spécifiques à un client MailWizz.

    ISOLATION RECOMMANDÉE :
      - Client 1 (customer_id=1) → servers VPS2 uniquement (hub-travelers + emilia-mullerd)
      - Client 2 (customer_id=2) → servers VPS3 uniquement (plane-liberty + planevilain)

    Garantit qu'un problème de réputation sur un client n'affecte pas l'autre.

    Args:
        customer_id: ID du client MailWizz
        server_ids:  IDs des delivery servers à assigner
    """
    if not payload.server_ids:
        raise HTTPException(status_code=400, detail="Au moins un server_id requis.")

    ok = await mailwizz_db.assign_servers_to_customer(customer_id, payload.server_ids)
    if not ok:
        raise HTTPException(
            status_code=503,
            detail=f"Impossible d'assigner les servers au client {customer_id}.",
        )

    return {
        "success": True,
        "customer_id": customer_id,
        "assigned_server_ids": payload.server_ids,
        "isolation": "Les campagnes de ce client passeront uniquement par ces IPs.",
    }


@router.get("/mailwizz/isolation")
async def check_mailwizz_isolation():
    """
    Vérifie et rapporte l'état d'isolation entre les clients MailWizz.

    Rapport :
      - Quels delivery servers chaque client utilise
      - Y a-t-il des servers partagés entre clients ? (risque !)
      - Recommandations d'isolation si problème détecté
    """
    customers = await mailwizz_db.list_customers_with_servers()

    # Construire map customer → servers
    customer_servers: dict[int, set[int]] = {}
    for c in customers:
        customer_servers[c["customer_id"]] = set(c.get("server_ids", []))

    # Chercher les servers partagés entre clients
    all_customer_ids = list(customer_servers.keys())
    shared_servers = []

    for i in range(len(all_customer_ids)):
        for j in range(i + 1, len(all_customer_ids)):
            cid1, cid2 = all_customer_ids[i], all_customer_ids[j]
            intersection = customer_servers[cid1] & customer_servers[cid2]
            if intersection:
                shared_servers.append({
                    "customers": [cid1, cid2],
                    "shared_server_ids": list(intersection),
                    "risk": "ÉLEVÉ — Un problème de réputation sur l'un affecte l'autre",
                })

    return {
        "customers": customers,
        "isolation_ok": len(shared_servers) == 0,
        "shared_servers": shared_servers,
        "recommendation": (
            "✅ Isolation correcte — chaque client a ses propres IPs d'envoi."
            if not shared_servers else
            "⚠️ Servers partagés détectés ! Utiliser POST /admin/mailwizz/customers/{id}/assign-servers "
            "pour séparer les delivery servers par client."
        ),
    }
