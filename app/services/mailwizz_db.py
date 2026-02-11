"""MailWizz MySQL client for managing delivery server quotas."""

import aiomysql
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class MailWizzDB:
    """Direct MySQL access to MailWizz DB for quota management."""

    def __init__(self):
        self._pool: aiomysql.Pool | None = None

    async def connect(self) -> None:
        """Create the connection pool."""
        if self._pool:
            return
        self._pool = await aiomysql.create_pool(
            host=settings.MAILWIZZ_DB_HOST,
            port=settings.MAILWIZZ_DB_PORT,
            user=settings.MAILWIZZ_DB_USER,
            password=settings.MAILWIZZ_DB_PASSWORD,
            db=settings.MAILWIZZ_DB_NAME,
            autocommit=True,
            minsize=1,
            maxsize=3,
        )
        logger.info("mailwizz_db_connected")

    async def close(self) -> None:
        """Close the pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def get_server_quota(self, server_id: int) -> int | None:
        """Get current hourly quota for a delivery server."""
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT hourly_quota FROM mw_delivery_server WHERE server_id = %s",
                    (server_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def set_server_quota(self, server_id: int, hourly_quota: int) -> bool:
        """Update the hourly quota for a delivery server."""
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE mw_delivery_server SET hourly_quota = %s WHERE server_id = %s",
                        (hourly_quota, server_id),
                    )
                    affected = cur.rowcount
                    if affected > 0:
                        logger.info(
                            "mailwizz_quota_updated",
                            server_id=server_id,
                            hourly_quota=hourly_quota,
                        )
                        return True
                    logger.warning("mailwizz_server_not_found", server_id=server_id)
                    return False
        except Exception as exc:
            logger.error("mailwizz_quota_update_failed", server_id=server_id, error=str(exc))
            return False

    async def get_server_status(self, server_id: int) -> str | None:
        """Get the status of a delivery server (active/inactive/disabled)."""
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT status FROM mw_delivery_server WHERE server_id = %s",
                    (server_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def set_server_status(self, server_id: int, status: str) -> bool:
        """Enable or disable a delivery server."""
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE mw_delivery_server SET status = %s WHERE server_id = %s",
                        (status, server_id),
                    )
                    return cur.rowcount > 0
        except Exception as exc:
            logger.error("mailwizz_status_update_failed", server_id=server_id, error=str(exc))
            return False

    async def list_servers(self) -> list[dict]:
        """List all delivery servers with key info."""
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT server_id, name, hostname, from_email, status, hourly_quota "
                    "FROM mw_delivery_server ORDER BY server_id"
                )
                return await cur.fetchall()


mailwizz_db = MailWizzDB()
