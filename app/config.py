"""Application configuration — Multi-PMTA nodes (3 × Cloud VPS 10)."""

import json
import sys

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All settings loaded from .env file."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    # ─────────────────────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────────────────────
    API_KEY: str = "changeme"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    # ─────────────────────────────────────────────────────────────
    # JWT Authentication
    # ─────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "changeme-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─────────────────────────────────────────────────────────────
    # Database PostgreSQL (Docker)
    # ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./email_engine.db"
    POSTGRES_DB: str = "email_engine_v2"
    POSTGRES_USER: str = "email_engine"
    POSTGRES_PASSWORD: str = ""

    # ─────────────────────────────────────────────────────────────
    # Redis (Docker)
    # ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─────────────────────────────────────────────────────────────
    # PowerMTA — Multi-nœuds (jusqu'à 5 × Cloud VPS 10 Contabo)
    #
    # Architecture globale :
    #   VPS1 (Hetzner)  : MailWizz + Email-Engine API — sos-holidays.com
    #   VPS2 (Contabo)  : PowerMTA — hub-travelers.com + emilia-mullerd.com ← ACTIF
    #   VPS3 (Contabo)  : PowerMTA — plane-liberty.com + planevilain.com    ← ACTIF
    #   VPS4 (Contabo)  : PowerMTA — domaines futurs (ajouter via console admin)
    #   VPS5 (Contabo)  : PowerMTA — domaines futurs (ajouter via console admin)
    #   VPS6 (Contabo)  : PowerMTA — domaines futurs (ajouter via console admin)
    #
    # Chaque nœud = 1 Cloud VPS 10 Contabo avec 2 IPs (1 incluse + 1 additionnelle)
    # Ajout de nouveaux domaines sur VPS4/VPS5/VPS6 : console admin → POST /ips
    # ─────────────────────────────────────────────────────────────

    # Nœud VPS2 (hub-travelers + emilia-mullerd) — ACTIF
    PMTA_VPS2_HOST: str = ""
    PMTA_VPS2_DOMAINS: str = "hub-travelers.com,emilia-mullerd.com"

    # Nœud VPS3 (plane-liberty + planevilain) — ACTIF
    PMTA_VPS3_HOST: str = ""
    PMTA_VPS3_DOMAINS: str = "plane-liberty.com,planevilain.com"

    # Nœud VPS4 — Domaines futurs (laisser vide jusqu'à activation)
    PMTA_VPS4_HOST: str = ""
    PMTA_VPS4_DOMAINS: str = ""

    # Nœud VPS5 — Domaines futurs (laisser vide jusqu'à activation)
    PMTA_VPS5_HOST: str = ""
    PMTA_VPS5_DOMAINS: str = ""

    # Nœud VPS6 — Domaines futurs (laisser vide jusqu'à activation)
    PMTA_VPS6_HOST: str = ""
    PMTA_VPS6_DOMAINS: str = ""

    # Commun à tous les nœuds
    PMTA_SSH_USER: str = "root"
    PMTA_SSH_KEY_PATH: str = "/app/secrets/pmta_ssh_key"
    PMTA_SMTP_PORT: int = 2525         # Port SMTP PowerMTA (relay depuis MailWizz)

    # Rétrocompatibilité (1 seul nœud — déprécié, utiliser PMTA_VPS2_HOST)
    PMTA_SSH_HOST: str = ""

    # ─────────────────────────────────────────────────────────────
    # MailWizz — Accès MySQL direct (PAS d'API REST)
    # Communication : Docker container → Apache/MySQL via host.docker.internal
    # ─────────────────────────────────────────────────────────────
    MAILWIZZ_DB_HOST: str = "host.docker.internal"
    MAILWIZZ_DB_PORT: int = 3306
    MAILWIZZ_DB_USER: str = "mailwizz"
    MAILWIZZ_DB_PASSWORD: str = ""
    MAILWIZZ_DB_NAME: str = "mailwizz_v2"

    # Paramètres delivery servers (créés via MySQL direct)
    MAILWIZZ_FROM_NAME: str = "Hub Travelers"
    MAILWIZZ_DS_MAX_CONN_MESSAGES: int = 50   # Messages par connexion SMTP (conservateur)
    MAILWIZZ_DS_HOURLY_QUOTA: int = 10        # Quota horaire initial (warmup semaine 1)

    # ─────────────────────────────────────────────────────────────
    # Webhook Security
    # ─────────────────────────────────────────────────────────────
    # Secret HMAC partagé avec PowerMTA/MailWizz pour signer les payloads
    WEBHOOK_SECRET: str = ""
    # IPs autorisées à appeler les webhooks (comma-separated: "1.2.3.4,5.6.7.8")
    # Laisser vide = aucune restriction par IP (non recommandé en prod)
    PMTA_ALLOWED_IPS: str = ""

    # ─────────────────────────────────────────────────────────────
    # Telegram Alerts (obligatoire en production)
    # ─────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ─────────────────────────────────────────────────────────────
    # Warmup — Hyper-protecteur (10 semaines, progression lente)
    #
    # Principe : mieux vaut 3 mois pour atteindre 10k/jour
    # qu'une blacklist en 2 semaines qui coûte 6 mois de récupération.
    #
    # Quotas journaliers par semaine (target en fin de semaine)
    # ─────────────────────────────────────────────────────────────
    WARMUP_WEEK1_QUOTA: int = 20       # Semaine 1  : max 20/j
    WARMUP_WEEK2_QUOTA: int = 50       # Semaine 2  : max 50/j
    WARMUP_WEEK3_QUOTA: int = 110      # Semaine 3  : max 110/j
    WARMUP_WEEK4_QUOTA: int = 250      # Semaine 4  : max 250/j
    WARMUP_WEEK5_QUOTA: int = 550      # Semaine 5  : max 550/j
    WARMUP_WEEK6_QUOTA: int = 1200     # Semaine 6  : max 1200/j
    WARMUP_WEEK7_QUOTA: int = 2600     # Semaine 7  : max 2600/j
    WARMUP_WEEK8_QUOTA: int = 5500     # Semaine 8  : max 5500/j
    WARMUP_WEEK9_QUOTA: int = 10000    # Semaine 9  : max 10000/j
    WARMUP_WEEK10_QUOTA: int = 20000   # Semaine 10 : max 20000/j (IP mature)

    # Seuils de sécurité — TRÈS stricts (hyper-protecteur)
    WARMUP_MAX_BOUNCE_RATE: float = 2.0    # Pause si bounce > 2%  (vs 5% standard)
    WARMUP_MAX_SPAM_RATE: float = 0.03     # Pause si spam > 0.03% (vs 0.1% standard)
    WARMUP_EMERGENCY_BOUNCE_RATE: float = 5.0   # Arrêt d'urgence si > 5% sur 24h
    WARMUP_EMERGENCY_SPAM_RATE: float = 0.1     # Arrêt d'urgence si > 0.1% sur 24h

    # Durées de pause (en heures)
    WARMUP_PAUSE_BOUNCE_HOURS: int = 72    # 3 jours si bounce > seuil
    WARMUP_PAUSE_SPAM_HOURS: int = 96      # 4 jours si spam > seuil

    # ─────────────────────────────────────────────────────────────
    # Rotation des IPs — Rolling (1 IP/semaine, pas tout d'un coup)
    # ─────────────────────────────────────────────────────────────
    IP_QUARANTINE_DAYS: int = 30       # Quarantine après blacklist
    IP_REST_DAYS: int = 14             # Repos entre 2 rotations

    # ─────────────────────────────────────────────────────────────
    # Blacklist check
    # ─────────────────────────────────────────────────────────────
    BLACKLIST_CHECK_INTERVAL_HOURS: int = 4

    # ─────────────────────────────────────────────────────────────
    # Monitoring
    # ─────────────────────────────────────────────────────────────
    GRAFANA_USER: str = "admin"
    GRAFANA_PASSWORD: str = ""
    GRAFANA_ROOT_URL: str = "http://localhost:3000"

    # ─────────────────────────────────────────────────────────────
    # External Services — Scraper-Pro (optionnel)
    # ─────────────────────────────────────────────────────────────
    SCRAPER_PRO_BOUNCE_URL: str = ""
    SCRAPER_PRO_DELIVERY_URL: str = ""
    SCRAPER_PRO_HMAC_SECRET: str = ""

    # ─────────────────────────────────────────────────────────────
    # Domaines d'envoi (pour validation et référence)
    # ─────────────────────────────────────────────────────────────
    DOMAIN_COUNT: int = 4
    DOMAIN1: str = "hub-travelers.com"
    DOMAIN2: str = "emilia-mullerd.com"
    DOMAIN3: str = "plane-liberty.com"
    DOMAIN4: str = "planevilain.com"

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """Valider les secrets en production — bloquer les placeholders dangereux."""
        if self.API_KEY in ("changeme", "changeme-generate-a-strong-key"):
            print(
                "FATAL: API_KEY est le placeholder par défaut. "
                "Définir une API_KEY forte dans .env",
                file=sys.stderr,
            )
            sys.exit(1)
        if self.JWT_SECRET_KEY in ("changeme-jwt-secret", "changeme"):
            print(
                "FATAL: JWT_SECRET_KEY est le placeholder par défaut. "
                "Définir un JWT_SECRET_KEY fort dans .env",
                file=sys.stderr,
            )
            sys.exit(1)
        if not self.TELEGRAM_BOT_TOKEN:
            print(
                "WARNING: TELEGRAM_BOT_TOKEN non défini — alertes Telegram désactivées.",
                file=sys.stderr,
            )
        if not self.MAILWIZZ_DB_PASSWORD:
            print(
                "WARNING: MAILWIZZ_DB_PASSWORD non défini — gestion delivery servers désactivée.",
                file=sys.stderr,
            )
        if not self.PMTA_VPS2_HOST and not self.PMTA_SSH_HOST:
            print(
                "WARNING: PMTA_VPS2_HOST non défini — provisionnement PowerMTA VPS2 désactivé.",
                file=sys.stderr,
            )
        return self

    def get_pmta_nodes(self) -> list[dict]:
        """
        Retourne la liste des nœuds PowerMTA configurés.

        Format retourné :
        [
            {
                "node_id": "vps2",
                "host": "1.2.3.4",
                "user": "root",
                "key_path": "/app/secrets/pmta_ssh_key",
                "domains": ["hub-travelers.com", "emilia-mullerd.com"],
                "smtp_port": 2525,
            },
            ...
        ]
        """
        nodes = []
        for num, (host_attr, domains_attr) in enumerate([
            ("PMTA_VPS2_HOST", "PMTA_VPS2_DOMAINS"),
            ("PMTA_VPS3_HOST", "PMTA_VPS3_DOMAINS"),
            ("PMTA_VPS4_HOST", "PMTA_VPS4_DOMAINS"),
            ("PMTA_VPS5_HOST", "PMTA_VPS5_DOMAINS"),
            ("PMTA_VPS6_HOST", "PMTA_VPS6_DOMAINS"),
        ], start=2):
            host = getattr(self, host_attr, "")
            domains_str = getattr(self, domains_attr, "")
            if not host:
                continue
            domains = [d.strip() for d in domains_str.split(",") if d.strip()]
            nodes.append({
                "node_id": f"vps{num}",
                "host": host,
                "user": self.PMTA_SSH_USER,
                "key_path": self.PMTA_SSH_KEY_PATH,
                "domains": domains,
                "smtp_port": self.PMTA_SMTP_PORT,
            })

        # Rétrocompatibilité : si PMTA_SSH_HOST défini mais pas PMTA_VPS2_HOST
        if not nodes and self.PMTA_SSH_HOST:
            nodes.append({
                "node_id": "vps2",
                "host": self.PMTA_SSH_HOST,
                "user": self.PMTA_SSH_USER,
                "key_path": self.PMTA_SSH_KEY_PATH,
                "domains": [self.DOMAIN1, self.DOMAIN2, self.DOMAIN3, self.DOMAIN4],
                "smtp_port": self.PMTA_SMTP_PORT,
            })

        return nodes

    def get_node_for_domain(self, domain: str) -> dict | None:
        """
        Retourne le nœud PowerMTA responsable d'un domaine donné.

        Matching exact (pas de fuzzy) :
          "hub-travelers.com"      → VPS2
          "mail.hub-travelers.com" → VPS2  (en cherchant le domaine parent)

        Algorithme :
          1. Match exact du domaine dans la liste
          2. Si pas trouvé, découpe les sous-domaines et cherche le domaine racine
        """
        domain_lower = domain.lower().strip()
        for node in self.get_pmta_nodes():
            # Match exact
            if domain_lower in node["domains"]:
                return node
            # Match en remontant les sous-domaines
            # ex: mail.hub-travelers.com → hub-travelers.com → match !
            parts = domain_lower.split(".")
            for i in range(1, len(parts) - 1):
                candidate = ".".join(parts[i:])
                if candidate in node["domains"]:
                    return node
        # Fallback : premier nœud disponible
        nodes = self.get_pmta_nodes()
        return nodes[0] if nodes else None

    def get_node_by_id(self, node_id: str) -> dict | None:
        """Retourne un nœud par son ID (vps2, vps3, vps4)."""
        for node in self.get_pmta_nodes():
            if node["node_id"] == node_id:
                return node
        return None


settings = Settings()
