"""Health data access."""

from .base import BaseRepository


class HealthRepository(BaseRepository):
    """Answers readiness by confirming database connectivity."""

    async def ping(self) -> bool:
        async with self.pool.connection() as conn:
            await conn.execute("SELECT 1")
        return True
