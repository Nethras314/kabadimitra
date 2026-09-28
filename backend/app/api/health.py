"""Health endpoints (thin routes — no business logic here)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services.health import HealthService
from .deps import get_health_service

router = APIRouter()


class HealthOut(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthOut)
async def health(service: Annotated[HealthService, Depends(get_health_service)]) -> HealthOut:
    return HealthOut(**service.liveness())


@router.get("/health/ready", response_model=HealthOut)
async def ready(service: Annotated[HealthService, Depends(get_health_service)]) -> HealthOut:
    return HealthOut(**await service.readiness())
