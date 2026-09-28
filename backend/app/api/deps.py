"""FastAPI dependency wiring."""

from fastapi import Request

from ..repositories.health import HealthRepository
from ..services.health import HealthService


def get_health_service(request: Request) -> HealthService:
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        return HealthService()
    return HealthService(HealthRepository(pool))
