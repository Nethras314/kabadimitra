"""Cloudinary signed-upload parameters for direct client uploads."""

from fastapi import APIRouter, Depends

from ..auth import Principal, get_principal
from ..media import upload_params

router = APIRouter()


@router.get("/media/upload-params")
async def media_upload_params(principal: Principal = Depends(get_principal)) -> dict:
    return upload_params()
