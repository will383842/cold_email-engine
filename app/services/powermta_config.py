"""
PowerMTA — Gestionnaire multi-nœuds (3 × Cloud VPS 10 Contabo).

Architecture :
  VPS1 (Hetzner) : MailWizz + Email-Engine API (ce code)
  VPS2 (Contabo) : PowerMTA → hub-travelers.com + emilia-mullerd.com
  VPS3 (Contabo) : PowerMTA → plane-liberty.com + planevilain.com
  VPS4 (Contabo) : PowerMTA → domaines futurs

Toutes les opérations PowerMTA passent par SSH + manipulation directe
du fichier /etc/pmta/config. PAS d'API HTTP PowerMTA (port 1983).
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

PMTA_CONFIG = "/etc/pmta/config"
PMTA_BIN = "/usr/sbin/pmta"


class PmtaNode:
    """
    Gestionnaire SSH pour un nœud PowerMTA (1 VPS Contabo).

    Toutes les opérations modifient directement /etc/pmta/config via SSH.
    Pas d'API intermédiaire — contrôle total et fiabilité maximale.
    """

    def __init__(self, node: dict):
        """
        Args:
            node: dict avec node_id, host, user, key_path, domains, smtp_port
        """
        self.node_id = node["node_id"]
        self.host = node["host"]
        self.user = node.get("user", "root")
        self.key_path = node.get("key_path", settings.PMTA_SSH_KEY_PATH)
        self.domains = node.get("domains", [])
        self.smtp_port = node.get("smtp_port", 2525)

    # ─────────────────────────────────────────────────────
    # Utilitaires SSH / SCP
    # ─────────────────────────────────────────────────────

    def _ssh(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """Exécute une commande sur ce nœud via SSH."""
        result = subprocess.run(
            [
                "ssh",
                "-i", self.key_path,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                "-o", "BatchMode=yes",
                f"{self.user}@{self.host}",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    def _scp_push(self, local_path: str, remote_path: str, timeout: int = 30) -> bool:
        """Pousse un fichier local vers ce nœud via SCP."""
        result = subprocess.run(
            [
                "scp",
                "-i", self.key_path,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                local_path,
                f"{self.user}@{self.host}:{remote_path}",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0

    def is_reachable(self) -> bool:
        """Vérifie que le nœud est accessible via SSH."""
        rc, _, _ = self._ssh("echo ok", timeout=10)
        return rc == 0

    # ─────────────────────────────────────────────────────
    # Statut PowerMTA
    # ─────────────────────────────────────────────────────

    def is_running(self) -> bool:
        """Vérifie que PowerMTA tourne sur ce nœud."""
        rc, stdout, _ = self._ssh(f"systemctl is-active pmta 2>/dev/null || {PMTA_BIN} show status 2>/dev/null")
        return rc == 0 or "running" in stdout.lower()

    def get_queue_size(self) -> int:
        """Retourne la taille de la file d'attente PowerMTA."""
        rc, stdout, _ = self._ssh(
            f"{PMTA_BIN} show topqueues --count=999 2>/dev/null | awk 'NR>1 {{sum+=$2}} END {{print sum+0}}'"
        )
        if rc != 0:
            return -1
        try:
            return int(stdout.strip())
        except ValueError:
            return -1

    def get_dkim_public_key(self, domain: str) -> str | None:
        """Lit la clé DKIM publique pour un domaine depuis le nœud."""
        slug = _domain_slug(domain)
        rc, stdout, _ = self._ssh(f"cat /etc/pmta/dkim/{slug}.pub.txt 2>/dev/null")
        if rc == 0 and stdout.strip():
            return stdout.strip()
        return None

    # ─────────────────────────────────────────────────────
    # Provisionnement virtual-mta + pattern-list
    # ─────────────────────────────────────────────────────

    def add_vmta_with_pattern(
        self,
        vmta_name: str,
        ip_address: str,
        hostname: str,
        sender_email: str,
        dkim_key_path: str | None = None,
    ) -> bool:
        """
        Ajoute un virtual-mta + entrée pattern-list dans PowerMTA sur ce nœud.

        ATOMIQUE : rollback automatique si l'ajout du pattern-list échoue.

        Architecture pour 2 domaines par VPS :
            vmta-hub-travelers  →  mail.hub-travelers.com  →  IP1
            vmta-emilia-mullerd →  mail.emilia-mullerd.com →  IP2

        Args:
            vmta_name:     Nom du virtual-mta (ex: vmta-hub-travelers)
            ip_address:    IP dédiée (ex: 178.12.34.56)
            hostname:      mail.domain.com (ex: mail.hub-travelers.com)
            sender_email:  Email expéditeur (ex: contact@mail.hub-travelers.com)
            dkim_key_path: Chemin clé DKIM sur VPS (auto-déduit si None)

        Returns:
            True si succès, False sinon
        """
        if not self.host:
            logger.warning("pmta_node_not_configured", node=self.node_id)
            return False

        # Déduire le domaine de base et le chemin DKIM
        parts = hostname.split(".")
        base_domain = ".".join(parts[-2:]) if len(parts) >= 2 else hostname
        slug = _domain_slug(base_domain)
        dkim_path = dkim_key_path or f"/etc/pmta/dkim/{slug}.pem"

        # Bloc virtual-mta complet
        vmta_block = (
            f"\n"
            f"# Domaine : {base_domain} — ajouté par Email-Engine API\n"
            f"<virtual-mta {vmta_name}>\n"
            f"    smtp-source-host {hostname} {ip_address}\n"
            f"    domain-key {base_domain},{hostname},*,{dkim_path}\n"
            f"    <domain *>\n"
            f"        max-cold-virtual-mta-msg 5/day\n"
            f"        max-msg-rate 3/h\n"
            f"        require-starttls yes\n"
            f"        retry-after 30m\n"
            f"        max-smtp-out 2\n"
            f"    </domain>\n"
            f"    <domain gmail.com>\n"
            f"        max-msg-rate 2/h\n"
            f"        max-smtp-out 1\n"
            f"    </domain>\n"
            f"    <domain outlook.com hotmail.com live.com>\n"
            f"        max-msg-rate 1/h\n"
            f"        max-smtp-out 1\n"
            f"        retry-after 60m\n"
            f"    </domain>\n"
            f"</virtual-mta>\n"
        )

        tmp_path = None
        vmta_added = False

        try:
            # Étape 1 : SCP le bloc vmta vers le nœud
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".conf", delete=False, prefix=f"vmta_{vmta_name}_"
            ) as tmp:
                tmp.write(vmta_block)
                tmp_path = tmp.name

            remote_tmp = f"/tmp/vmta_{vmta_name}.conf"
            if not self._scp_push(tmp_path, remote_tmp):
                logger.error("pmta_scp_failed", node=self.node_id, vmta=vmta_name)
                return False

            # Étape 2 : Appendre le bloc au config
            rc, _, err = self._ssh(
                f"cat {remote_tmp} >> {PMTA_CONFIG} && rm -f {remote_tmp}"
            )
            if rc != 0:
                logger.error("pmta_append_vmta_failed", node=self.node_id, vmta=vmta_name, error=err)
                return False
            vmta_added = True

            # Étape 3 : Insérer dans pattern-list (avant </pattern-list>)
            # On passe par un fichier temporaire pour éviter toute injection shell
            # (les emails peuvent contenir @, +, tirets, etc. qui brisent sed inline)
            pattern_entry = f"    {sender_email}   {vmta_name}"
            remote_pattern = f"/tmp/pattern_{vmta_name}.txt"

            # Créer le fichier de remplacement sur le nœud (sans passer le contenu par shell)
            pattern_tmp_local = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, prefix=f"pattern_{vmta_name}_"
                ) as ptmp:
                    # Le fichier contient exactement la ligne à insérer
                    ptmp.write(pattern_entry + "\n")
                    pattern_tmp_local = ptmp.name

                if not self._scp_push(pattern_tmp_local, remote_pattern):
                    logger.error("pmta_scp_pattern_failed", node=self.node_id, vmta=vmta_name)
                    self._remove_vmta_block_only(vmta_name)
                    return False
            finally:
                if pattern_tmp_local and os.path.exists(pattern_tmp_local):
                    os.unlink(pattern_tmp_local)

            # Python script distant pour insérer avant </pattern-list>
            insert_cmd = (
                f"python3 -c \""
                f"import sys; "
                f"c = open('{PMTA_CONFIG}').read(); "
                f"entry = open('{remote_pattern}').read().rstrip(); "
                f"c = c.replace('</pattern-list>', entry + chr(10) + '</pattern-list>', 1); "
                f"open('{PMTA_CONFIG}','w').write(c); "
                f"\" && rm -f {remote_pattern}"
            )
            rc, _, err = self._ssh(insert_cmd)
            if rc != 0:
                logger.error(
                    "pmta_add_pattern_failed",
                    node=self.node_id,
                    vmta=vmta_name,
                    sender=sender_email,
                    error=err,
                )
                # ROLLBACK : supprimer le bloc vmta ajouté
                self._remove_vmta_block_only(vmta_name)
                return False

            # Étape 4 : Reload PowerMTA (graceful — attend la fin des envois en cours)
            self._graceful_reload()

            logger.info(
                "pmta_vmta_provisioned",
                node=self.node_id,
                vmta=vmta_name,
                ip=ip_address,
                sender=sender_email,
            )
            return True

        except Exception as exc:
            logger.error("pmta_provision_error", node=self.node_id, vmta=vmta_name, error=str(exc))
            if vmta_added:
                self._remove_vmta_block_only(vmta_name)
            return False

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def remove_vmta_with_pattern(self, vmta_name: str, sender_email: str) -> bool:
        """
        Supprime un virtual-mta et son entrée pattern-list.

        Args:
            vmta_name:    Nom du virtual-mta
            sender_email: Email à supprimer du pattern-list
        """
        if not self.host:
            return False

        errors = 0

        # 1. Supprimer l'entrée pattern-list
        safe_email = re.escape(sender_email).replace("/", "\\/").replace("@", "\\@")
        rc, _, err = self._ssh(f"sed -i '/{safe_email}/d' {PMTA_CONFIG}")
        if rc != 0:
            logger.error("pmta_remove_pattern_failed", node=self.node_id, sender=sender_email, error=err)
            errors += 1

        # 2. Supprimer le bloc virtual-mta
        if not self._remove_vmta_block_only(vmta_name):
            errors += 1

        if errors == 0:
            self._graceful_reload()
            logger.info("pmta_vmta_removed", node=self.node_id, vmta=vmta_name)

        return errors == 0

    def pause_vmta(self, vmta_name: str) -> bool:
        """Suspend l'envoi pour un virtual-mta (ajoute max-msg-rate 0/h)."""
        if not self.host:
            return False
        # Modifier le max-msg-rate du vmta spécifique à 0
        rc, _, err = self._ssh(
            f"sed -i '/<virtual-mta {vmta_name}>/,/<\\/virtual-mta>/s/max-msg-rate .*/max-msg-rate 0\\/h/' {PMTA_CONFIG}"
        )
        if rc == 0:
            self._graceful_reload()
            logger.info("pmta_vmta_paused", node=self.node_id, vmta=vmta_name)
        return rc == 0

    def resume_vmta(self, vmta_name: str, max_rate: str = "100/h") -> bool:
        """Reprend l'envoi pour un virtual-mta."""
        if not self.host:
            return False
        rc, _, _ = self._ssh(
            f"sed -i '/<virtual-mta {vmta_name}>/,/<\\/virtual-mta>/s/max-msg-rate 0\\/h/max-msg-rate {max_rate}/' {PMTA_CONFIG}"
        )
        if rc == 0:
            self._graceful_reload()
            logger.info("pmta_vmta_resumed", node=self.node_id, vmta=vmta_name, rate=max_rate)
        return rc == 0

    def update_vmta_rate(self, vmta_name: str, max_msg_rate: str) -> bool:
        """Met à jour le max-msg-rate d'un virtual-mta (ex: '50/h', '500/day')."""
        if not self.host:
            return False
        rc, _, _ = self._ssh(
            f"sed -i '/<virtual-mta {vmta_name}>/,/<\\/virtual-mta>/s|max-msg-rate .*|max-msg-rate {max_msg_rate}|' {PMTA_CONFIG}"
        )
        if rc == 0:
            self._graceful_reload()
        return rc == 0

    def list_vmtas(self) -> list[str]:
        """Liste les noms de virtual-mta configurés sur ce nœud."""
        rc, stdout, _ = self._ssh(
            f"grep -E '^<virtual-mta ' {PMTA_CONFIG} 2>/dev/null | sed 's/<virtual-mta //;s/>//' | tr -d ' '"
        )
        if rc != 0:
            return []
        return [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    def get_sender_for_vmta(self, vmta_name: str) -> str | None:
        """Lit l'email expéditeur associé à un vmta dans le pattern-list."""
        rc, stdout, _ = self._ssh(
            f"grep '{vmta_name}' {PMTA_CONFIG} | grep '@' | awk '{{print $1}}' | head -1"
        )
        if rc == 0 and stdout.strip():
            return stdout.strip()
        return None

    # ─────────────────────────────────────────────────────
    # Helpers internes
    # ─────────────────────────────────────────────────────

    def _remove_vmta_block_only(self, vmta_name: str) -> bool:
        """Supprime uniquement le bloc virtual-mta (sans pattern-list)."""
        vmta_escaped = re.escape(vmta_name).replace("/", "\\/")
        # Supprimer le commentaire précédent + le bloc
        rc, _, err = self._ssh(
            f"sed -i '/# Domaine.*— ajouté par Email-Engine API/d; "
            f"/<virtual-mta {vmta_escaped}>/,/<\\/virtual-mta>/d' {PMTA_CONFIG}"
        )
        if rc != 0:
            logger.error("pmta_remove_vmta_block_failed", node=self.node_id, vmta=vmta_name, error=err)
            return False
        return True

    def _graceful_reload(self) -> bool:
        """
        Recharge PowerMTA de façon gracieuse.
        Attend que la queue soit suffisamment basse avant de recharger.
        """
        # Vérifier la taille de la queue
        queue_size = self.get_queue_size()
        if queue_size > 1000:
            logger.warning(
                "pmta_reload_deferred",
                node=self.node_id,
                queue_size=queue_size,
                reason="Queue trop grande — reload différé",
            )
            # Le reload sera fait au prochain cycle APScheduler
            return False

        rc, _, err = self._ssh(f"{PMTA_BIN} reload", timeout=15)
        if rc != 0:
            logger.warning("pmta_reload_failed", node=self.node_id, error=err)
            return False

        logger.info("pmta_reloaded", node=self.node_id)
        return True


class MultiPmtaManager:
    """
    Gestionnaire centralisé pour plusieurs nœuds PowerMTA.

    Routing automatique : domaine/hostname → nœud responsable.
    Toutes les opérations passent par ce gestionnaire.
    """

    def __init__(self):
        self._nodes: dict[str, PmtaNode] = {}
        self._load_nodes()

    def _load_nodes(self) -> None:
        """Charge les nœuds depuis la config."""
        for node_conf in settings.get_pmta_nodes():
            self._nodes[node_conf["node_id"]] = PmtaNode(node_conf)

    def get_node(self, node_id: str) -> PmtaNode | None:
        """Retourne un nœud par son ID."""
        return self._nodes.get(node_id)

    def get_node_for_domain(self, domain: str) -> PmtaNode | None:
        """Retourne le nœud responsable d'un domaine donné."""
        node_conf = settings.get_node_for_domain(domain)
        if node_conf:
            return self._nodes.get(node_conf["node_id"])
        # Fallback : premier nœud disponible
        if self._nodes:
            return next(iter(self._nodes.values()))
        return None

    def get_node_for_hostname(self, hostname: str) -> PmtaNode | None:
        """
        Retourne le nœud responsable d'un hostname (ex: mail.hub-travelers.com).
        Extrait le domaine de base et fait le routing.
        """
        parts = hostname.split(".")
        # mail.hub-travelers.com → hub-travelers.com
        if len(parts) >= 3 and parts[0] in ("mail", "smtp", "send", "out"):
            domain = ".".join(parts[1:])
        else:
            domain = ".".join(parts[-2:]) if len(parts) >= 2 else hostname
        return self.get_node_for_domain(domain)

    def all_nodes(self) -> list[PmtaNode]:
        """Retourne tous les nœuds configurés."""
        return list(self._nodes.values())

    def add_vmta_with_pattern(
        self,
        vmta_name: str,
        ip_address: str,
        hostname: str,
        sender_email: str,
        dkim_key_path: str | None = None,
        node_id: str | None = None,
    ) -> tuple[bool, str]:
        """
        Provisionne un virtual-mta sur le nœud approprié.

        Args:
            vmta_name:    Nom du vmta
            ip_address:   IP dédiée
            hostname:     mail.domain.com
            sender_email: Email expéditeur
            dkim_key_path: Chemin clé DKIM (optionnel)
            node_id:      Forcer un nœud spécifique (optionnel, sinon auto-routing)

        Returns:
            (success: bool, node_id_used: str)
        """
        if node_id:
            node = self._nodes.get(node_id)
        else:
            node = self.get_node_for_hostname(hostname)

        if not node:
            logger.error("pmta_no_node_found", hostname=hostname, node_id=node_id)
            return False, ""

        ok = node.add_vmta_with_pattern(
            vmta_name=vmta_name,
            ip_address=ip_address,
            hostname=hostname,
            sender_email=sender_email,
            dkim_key_path=dkim_key_path,
        )
        return ok, node.node_id

    def remove_vmta_with_pattern(
        self, vmta_name: str, sender_email: str, node_id: str
    ) -> bool:
        """Supprime un vmta d'un nœud spécifique (node_id requis)."""
        node = self._nodes.get(node_id)
        if not node:
            logger.error("pmta_node_not_found", node_id=node_id)
            return False
        return node.remove_vmta_with_pattern(vmta_name, sender_email)

    def health_check_all(self) -> list[dict]:
        """Vérifie la santé de tous les nœuds."""
        results = []
        for node in self.all_nodes():
            reachable = node.is_reachable()
            results.append({
                "node_id": node.node_id,
                "host": node.host,
                "reachable": reachable,
                "pmta_running": node.is_running() if reachable else False,
                "queue_size": node.get_queue_size() if reachable else -1,
                "domains": node.domains,
            })
        return results


def _domain_slug(domain: str) -> str:
    """
    Convertit un domaine en slug pour nommer les fichiers DKIM et vmta.
    Exemple : hub-travelers.com → hub-travelers
    """
    # Supprimer TLD
    parts = domain.split(".")
    without_tld = ".".join(parts[:-1]) if len(parts) > 1 else domain
    # Remplacer les points par des tirets
    return without_tld.replace(".", "-")


def domain_to_vmta(domain: str) -> str:
    """
    Convertit un domaine en nom de vmta.
    Exemple : hub-travelers.com → vmta-hub-travelers
    """
    return f"vmta-{_domain_slug(domain)}"


# Instance globale (lazy-loaded, recréée à chaque utilisation pour prendre en compte
# les changements de config sans redémarrage)
def get_pmta_manager() -> MultiPmtaManager:
    """Retourne le gestionnaire PowerMTA multi-nœuds."""
    return MultiPmtaManager()


# Alias de compatibilité avec l'ancienne architecture (1 seul nœud)
class RemotePowerMTAManager:
    """
    Alias de compatibilité — délègue au premier nœud disponible.
    Utiliser MultiPmtaManager pour le support multi-nœuds complet.
    """

    def __init__(self):
        self._manager = MultiPmtaManager()

    def is_configured(self) -> bool:
        return len(self._manager.all_nodes()) > 0

    def add_vmta_with_pattern(self, vmta_name, ip_address, hostname, sender_email, dkim_key_path=None):
        ok, _ = self._manager.add_vmta_with_pattern(
            vmta_name, ip_address, hostname, sender_email, dkim_key_path
        )
        return ok

    def remove_vmta_with_pattern(self, vmta_name, sender_email, node_id="vps2"):
        return self._manager.remove_vmta_with_pattern(vmta_name, sender_email, node_id)

    def is_reachable(self) -> bool:
        nodes = self._manager.all_nodes()
        return any(n.is_reachable() for n in nodes)
