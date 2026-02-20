"""
MailWizz — Accès MySQL direct (PAS d'API REST).

Architecture : Docker container → MySQL sur hôte VPS1 via host.docker.internal
Toutes les opérations passent directement par la base de données MailWizz.
Avantages vs API REST :
  - Pas de dépendance à la configuration MailWizz API Keys
  - Plus rapide (pas de HTTP round-trip)
  - Accès complet à toutes les tables
  - Gestion fine des quotas warmup
"""

from datetime import datetime

import aiomysql
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class MailWizzDB:
    """
    Client MySQL direct pour MailWizz.

    Gère les delivery servers (création, suppression, quotas, statut).
    Toutes les requêtes utilisent des paramètres préparés pour éviter les injections SQL.
    """

    def __init__(self):
        self._pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        """
        Crée le pool de connexions MySQL.

        Stratégie de fallback :
          1. Tente avec MAILWIZZ_DB_HOST (host.docker.internal par défaut)
          2. Si échec sur Linux (host.docker.internal non résolu), tente 172.17.0.1
          3. Si toujours en échec, log warning et désactive MailWizz (non bloquant)
        """
        if self._pool:
            return
        if not settings.MAILWIZZ_DB_PASSWORD:
            logger.warning("mailwizz_db_not_configured", hint="Set MAILWIZZ_DB_PASSWORD in .env")
            return

        hosts_to_try = [settings.MAILWIZZ_DB_HOST]
        # Fallback Linux : docker bridge gateway (équivalent host.docker.internal)
        if settings.MAILWIZZ_DB_HOST == "host.docker.internal":
            hosts_to_try.append("172.17.0.1")

        last_error = None
        for host in hosts_to_try:
            try:
                self._pool = await aiomysql.create_pool(
                    host=host,
                    port=settings.MAILWIZZ_DB_PORT,
                    user=settings.MAILWIZZ_DB_USER,
                    password=settings.MAILWIZZ_DB_PASSWORD,
                    db=settings.MAILWIZZ_DB_NAME,
                    autocommit=True,
                    minsize=1,
                    maxsize=5,
                    charset="utf8mb4",
                    connect_timeout=5,
                )
                logger.info("mailwizz_db_connected", host=host, db=settings.MAILWIZZ_DB_NAME)
                return
            except Exception as exc:
                last_error = exc
                logger.warning("mailwizz_db_connect_failed", host=host, error=str(exc))
                self._pool = None

        logger.error(
            "mailwizz_db_unavailable",
            tried_hosts=hosts_to_try,
            error=str(last_error),
            hint="Vérifier MAILWIZZ_DB_HOST, MAILWIZZ_DB_PASSWORD et accès réseau",
        )

    async def close(self) -> None:
        """Ferme le pool de connexions."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def _ensure_connected(self) -> bool:
        """S'assure que le pool est connecté. Retourne False si non configuré."""
        if not self._pool:
            await self.connect()
        return self._pool is not None

    # ─────────────────────────────────────────────────────────────
    # DELIVERY SERVERS — CRUD complet
    # ─────────────────────────────────────────────────────────────

    async def create_delivery_server(
        self,
        name: str,
        hostname: str,
        port: int,
        from_email: str,
        from_name: str,
        hourly_quota: int = 10,
        max_connection_messages: int = 50,
        customer_id: int = 1,
    ) -> int | None:
        """
        Crée un delivery server SMTP dans MailWizz via MySQL direct.

        Ce delivery server correspond à une IP PowerMTA avec son email expéditeur.
        COHÉRENCE GARANTIE : from_email ici = sender_email dans PowerMTA pattern-list.

        Args:
            name:                    Nom descriptif (ex: "PowerMTA hub-travelers")
            hostname:                IP ou hostname du serveur PowerMTA (VPS2 ou VPS3)
            port:                    Port SMTP PowerMTA (2525)
            from_email:              Email expéditeur = pattern-list PowerMTA
            from_name:               Nom affiché dans les emails
            hourly_quota:            Quota horaire initial (faible pour warmup)
            max_connection_messages: Messages par connexion SMTP
            customer_id:             ID client MailWizz (1 = admin)

        Returns:
            server_id si créé, None si erreur
        """
        if not await self._ensure_connected():
            logger.warning("mailwizz_db_unavailable", operation="create_delivery_server")
            return None

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO mw_delivery_server (
                            customer_id, name, hostname, username, password,
                            port, protocol, type,
                            from_email, from_name, reply_to_email,
                            max_connection_messages, probability,
                            hourly_quota, daily_quota, monthly_quota,
                            hourly_usage, daily_usage, monthly_usage,
                            bounce_server_id, signing_enabled,
                            status, date_added, last_updated
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s
                        )
                        """,
                        (
                            customer_id, name, hostname, "", "",
                            port, "smtp", "smtp",
                            from_email, from_name, from_email,
                            max_connection_messages, 100,
                            hourly_quota, 0, 0,
                            0, 0, 0,
                            0, "yes",
                            "active", now, now,
                        ),
                    )
                    server_id = cur.lastrowid
                    logger.info(
                        "mailwizz_delivery_server_created",
                        server_id=server_id,
                        name=name,
                        from_email=from_email,
                        hourly_quota=hourly_quota,
                    )
                    return server_id

        except Exception as exc:
            logger.error("mailwizz_create_server_failed", name=name, error=str(exc))
            return None

    async def delete_delivery_server(self, server_id: int) -> bool:
        """
        Supprime un delivery server de MailWizz.
        Appelé lors de la suppression d'une IP (déprovision).
        """
        if not await self._ensure_connected():
            return False
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM mw_delivery_server WHERE server_id = %s",
                        (server_id,),
                    )
                    deleted = cur.rowcount > 0
                    if deleted:
                        logger.info("mailwizz_delivery_server_deleted", server_id=server_id)
                    else:
                        logger.warning("mailwizz_server_not_found", server_id=server_id)
                    return deleted
        except Exception as exc:
            logger.error("mailwizz_delete_server_failed", server_id=server_id, error=str(exc))
            return False

    async def set_server_status(self, server_id: int, status: str) -> bool:
        """
        Change le statut d'un delivery server.
        status: 'active' | 'inactive' | 'in-use'
        """
        if not await self._ensure_connected():
            return False
        if status not in ("active", "inactive", "in-use"):
            logger.error("mailwizz_invalid_status", status=status)
            return False
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    await cur.execute(
                        "UPDATE mw_delivery_server SET status = %s, last_updated = %s WHERE server_id = %s",
                        (status, now, server_id),
                    )
                    ok = cur.rowcount > 0
                    if ok:
                        logger.info("mailwizz_server_status_changed", server_id=server_id, status=status)
                    return ok
        except Exception as exc:
            logger.error("mailwizz_status_update_failed", server_id=server_id, error=str(exc))
            return False

    async def pause_delivery_server(self, server_id: int) -> bool:
        """Désactive temporairement un delivery server (warmup pause, blacklist)."""
        return await self.set_server_status(server_id, "inactive")

    async def resume_delivery_server(self, server_id: int) -> bool:
        """Réactive un delivery server."""
        return await self.set_server_status(server_id, "active")

    # ─────────────────────────────────────────────────────────────
    # GESTION DES QUOTAS (pour warmup progressif)
    # ─────────────────────────────────────────────────────────────

    async def set_server_quota(self, server_id: int, hourly_quota: int) -> bool:
        """
        Met à jour le quota horaire d'un delivery server.
        Appelé par le warmup engine à chaque avancement de phase.

        Le quota horaire = quota_journalier / 16h actives
        (envoi uniquement de 7h à 23h pour respecter les heures ouvrables)
        """
        if not await self._ensure_connected():
            return False
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    await cur.execute(
                        """UPDATE mw_delivery_server
                           SET hourly_quota = %s, last_updated = %s
                           WHERE server_id = %s""",
                        (hourly_quota, now, server_id),
                    )
                    ok = cur.rowcount > 0
                    if ok:
                        logger.info(
                            "mailwizz_quota_updated",
                            server_id=server_id,
                            hourly_quota=hourly_quota,
                        )
                    return ok
        except Exception as exc:
            logger.error("mailwizz_quota_update_failed", server_id=server_id, error=str(exc))
            return False

    async def get_server_quota(self, server_id: int) -> int | None:
        """Retourne le quota horaire actuel d'un delivery server."""
        if not await self._ensure_connected():
            return None
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT hourly_quota FROM mw_delivery_server WHERE server_id = %s",
                    (server_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def reset_daily_usage(self, server_id: int) -> bool:
        """
        Remet à zéro les compteurs d'utilisation journaliers.
        Appelé automatiquement par le cron quotidien minuit.
        """
        if not await self._ensure_connected():
            return False
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE mw_delivery_server SET daily_usage = 0, hourly_usage = 0 WHERE server_id = %s",
                        (server_id,),
                    )
                    return cur.rowcount > 0
        except Exception as exc:
            logger.error("mailwizz_reset_usage_failed", server_id=server_id, error=str(exc))
            return False

    async def reset_all_daily_usage(self) -> int:
        """Remet à zéro les compteurs pour TOUS les delivery servers actifs."""
        if not await self._ensure_connected():
            return 0
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE mw_delivery_server SET daily_usage = 0, hourly_usage = 0 WHERE status = 'active'"
                    )
                    count = cur.rowcount
                    logger.info("mailwizz_daily_usage_reset", servers_reset=count)
                    return count
        except Exception as exc:
            logger.error("mailwizz_reset_all_usage_failed", error=str(exc))
            return 0

    # ─────────────────────────────────────────────────────────────
    # LECTURE / LISTING
    # ─────────────────────────────────────────────────────────────

    async def get_server(self, server_id: int) -> dict | None:
        """Retourne les détails complets d'un delivery server."""
        if not await self._ensure_connected():
            return None
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT server_id, name, hostname, port, from_email, from_name,
                              status, hourly_quota, daily_quota, hourly_usage, daily_usage,
                              max_connection_messages, date_added, last_updated
                       FROM mw_delivery_server WHERE server_id = %s""",
                    (server_id,),
                )
                return await cur.fetchone()

    async def get_server_status(self, server_id: int) -> str | None:
        """Retourne le statut d'un delivery server."""
        if not await self._ensure_connected():
            return None
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT status FROM mw_delivery_server WHERE server_id = %s",
                    (server_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def list_servers(self) -> list[dict]:
        """Liste tous les delivery servers avec leurs infos clés."""
        if not await self._ensure_connected():
            return []
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT server_id, name, hostname, port, from_email, from_name,
                              status, hourly_quota, hourly_usage, daily_usage,
                              date_added
                       FROM mw_delivery_server
                       ORDER BY server_id"""
                )
                return await cur.fetchall()

    async def get_server_by_email(self, from_email: str) -> dict | None:
        """Trouve un delivery server par son email expéditeur."""
        if not await self._ensure_connected():
            return None
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM mw_delivery_server WHERE from_email = %s LIMIT 1",
                    (from_email,),
                )
                return await cur.fetchone()

    async def sync_warmup_quota(self, server_id: int, daily_quota: int) -> bool:
        """
        Synchronise le quota warmup vers MailWizz.

        Convertit le quota journalier en quota horaire en répartissant
        sur 16h d'envoi actif (7h-23h, hors nuit).

        Ex: 50/jour → 50/16 ≈ 4/heure (arrondi à 3 pour la sécurité)
        """
        # Répartir sur 16h actives avec marge de sécurité (×0.8)
        hourly = max(1, int(daily_quota / 16 * 0.8))
        return await self.set_server_quota(server_id, hourly)

    # ─────────────────────────────────────────────────────────────
    # STATS BOUNCE / DELIVERY (depuis les logs MailWizz)
    # ─────────────────────────────────────────────────────────────

    async def get_bounce_stats(self, server_id: int, days: int = 7) -> dict:
        """
        Récupère les statistiques de bounce pour un delivery server.
        Utilisé par le warmup engine pour vérifier les seuils de sécurité.

        Retourne : {sent, delivered, bounced, complaints, bounce_rate, spam_rate}
        """
        if not await self._ensure_connected():
            return {"sent": 0, "delivered": 0, "bounced": 0, "complaints": 0,
                    "bounce_rate": 0.0, "spam_rate": 0.0}
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Récupérer stats depuis la table de tracking MailWizz
                    # Table mw_campaign_delivery_log ou mw_campaign_bounce_log
                    await cur.execute(
                        """
                        SELECT
                            COUNT(*) as total_sent,
                            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as delivered,
                            SUM(CASE WHEN status = 'hard-bounce' OR status = 'soft-bounce' THEN 1 ELSE 0 END) as bounced,
                            SUM(CASE WHEN status = 'complaint' THEN 1 ELSE 0 END) as complaints
                        FROM mw_campaign_delivery_log
                        WHERE delivery_server_id = %s
                          AND date_added >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        """,
                        (server_id, days),
                    )
                    row = await cur.fetchone()
                    if not row or not row["total_sent"]:
                        return {"sent": 0, "delivered": 0, "bounced": 0, "complaints": 0,
                                "bounce_rate": 0.0, "spam_rate": 0.0}

                    total = row["total_sent"] or 0
                    bounced = row["bounced"] or 0
                    complaints = row["complaints"] or 0

                    return {
                        "sent": total,
                        "delivered": row["delivered"] or 0,
                        "bounced": bounced,
                        "complaints": complaints,
                        "bounce_rate": round(bounced / total * 100, 3) if total > 0 else 0.0,
                        "spam_rate": round(complaints / total * 100, 3) if total > 0 else 0.0,
                    }
        except Exception as exc:
            logger.warning("mailwizz_bounce_stats_failed", server_id=server_id, error=str(exc))
            return {"sent": 0, "delivered": 0, "bounced": 0, "complaints": 0,
                    "bounce_rate": 0.0, "spam_rate": 0.0}


    # ─────────────────────────────────────────────────────
    # Options MailWizz (table mw_option)
    # ─────────────────────────────────────────────────────

    async def get_option(self, key: str) -> str | None:
        """Lit une option depuis la table mw_option."""
        pool = await self._get_pool()
        if not pool:
            return None
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT option_value FROM mw_option WHERE option_name = %s LIMIT 1",
                        (key,)
                    )
                    row = await cur.fetchone()
                    return row[0] if row else None
        except Exception as exc:
            logger.warning("mailwizz_get_option_failed", key=key, error=str(exc))
            return None

    async def set_option(self, key: str, value: str) -> bool:
        """Écrit une option dans la table mw_option (INSERT ON DUPLICATE KEY UPDATE)."""
        pool = await self._get_pool()
        if not pool:
            return False
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO mw_option (option_name, option_value)
                           VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE option_value = VALUES(option_value)""",
                        (key, value)
                    )
                    await conn.commit()
                    return True
        except Exception as exc:
            logger.warning("mailwizz_set_option_failed", key=key, error=str(exc))
            return False

    # ─────────────────────────────────────────────────────
    # Clients MailWizz + isolation delivery servers
    # ─────────────────────────────────────────────────────

    async def list_customers_with_servers(self) -> list[dict]:
        """
        Liste les clients MailWizz avec leurs delivery servers assignés.

        Retourne pour chaque client :
          - customer_id, email, status
          - server_ids : IDs des delivery servers utilisables par ce client
          - servers    : Détails (nom, from_email, hostname)
        """
        pool = await self._get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Liste des clients
                    await cur.execute(
                        """SELECT customer_id, email, status, date_added
                           FROM mw_customer
                           ORDER BY customer_id"""
                    )
                    customers_raw = await cur.fetchall()

                    results = []
                    for (cid, email, status, date_added) in customers_raw:
                        # Delivery servers assignés à ce client
                        await cur.execute(
                            """SELECT ds.server_id, ds.name, ds.from_email, ds.hostname,
                                      ds.status, ds.hourly_quota
                               FROM mw_delivery_server ds
                               LEFT JOIN mw_delivery_server_to_customer dsc
                                   ON ds.server_id = dsc.server_id AND dsc.customer_id = %s
                               WHERE dsc.customer_id IS NOT NULL
                                  OR ds.customer_id = %s
                               ORDER BY ds.server_id""",
                            (cid, cid)
                        )
                        servers_raw = await cur.fetchall()
                        servers = [
                            {
                                "server_id": s[0],
                                "name": s[1],
                                "from_email": s[2],
                                "hostname": s[3],
                                "status": s[4],
                                "hourly_quota": s[5],
                            }
                            for s in servers_raw
                        ]

                        results.append({
                            "customer_id": cid,
                            "email": email,
                            "status": status,
                            "date_added": str(date_added),
                            "server_count": len(servers),
                            "server_ids": [s["server_id"] for s in servers],
                            "servers": servers,
                        })
                    return results
        except Exception as exc:
            logger.warning("mailwizz_list_customers_failed", error=str(exc))
            return []

    async def assign_servers_to_customer(
        self, customer_id: int, server_ids: list[int]
    ) -> bool:
        """
        Assigne des delivery servers à un client MailWizz.

        Isole les clients : chaque client n'utilise que ses propres IPs d'envoi.
        Remplace l'assignation existante (DELETE + INSERT).

        Table : mw_delivery_server_to_customer
        """
        pool = await self._get_pool()
        if not pool:
            return False
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Supprimer anciennes assignations
                    await cur.execute(
                        "DELETE FROM mw_delivery_server_to_customer WHERE customer_id = %s",
                        (customer_id,)
                    )
                    # Insérer nouvelles assignations
                    for server_id in server_ids:
                        await cur.execute(
                            """INSERT IGNORE INTO mw_delivery_server_to_customer
                               (server_id, customer_id) VALUES (%s, %s)""",
                            (server_id, customer_id)
                        )
                    await conn.commit()
                    logger.info(
                        "mailwizz_servers_assigned",
                        customer_id=customer_id,
                        server_ids=server_ids,
                    )
                    return True
        except Exception as exc:
            logger.warning(
                "mailwizz_assign_servers_failed",
                customer_id=customer_id,
                error=str(exc),
            )
            return False


# Instance singleton réutilisée sur toute l'application
mailwizz_db = MailWizzDB()
