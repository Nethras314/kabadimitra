"""Authenticated identity endpoints."""

from fastapi import APIRouter, Depends

from ..auth import Principal, get_principal
from ..schemas import MeOut

router = APIRouter()


@router.get("/me", response_model=MeOut)
async def me(principal: Principal = Depends(get_principal)) -> MeOut:
    return MeOut(
        user_id=principal.user_id,
        sub=principal.sub,
        roles=principal.roles,
        organization_id=principal.organization_id,
        preferred_locale=principal.preferred_locale,
    )
