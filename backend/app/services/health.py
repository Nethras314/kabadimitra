"""Health business logic."""

from ..core.config import settings
from ..core.errors import ServiceUnavailableError
from ..repositories.health import HealthRepository


class HealthService:
    def __init__(self, repository: HealthRepository | None = None) -> None:
        self._repository = repository

    def liveness(self) -> dict:
        return {"status": "ok", "service": settings.app_name}

    async def readiness(self) -> dict:
        if self._repository is None:
            raise ServiceUnavailableError("Database is not configured")
        await self._repository.ping()
        return {"status": "ok", "service": settings.app_name}
