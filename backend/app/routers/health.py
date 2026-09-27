"""Health / readiness endpoints (unauthenticated)."""

from fastapi import APIRouter, Depends

from ..db import get_db
from ..schemas import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(status="ok", service="kabadi-mitra-api")


@router.get("/health/ready", response_model=HealthOut)
async def ready(conn=Depends(get_db)) -> HealthOut:
    await conn.execute("SELECT 1")
    return HealthOut(status="ok", service="kabadi-mitra-api")
