"""Cloudinary integration (media metadata + signed direct uploads).

Images are never stored in PostgreSQL. The collector uploads directly to
Cloudinary (signed upload) and the backend persists only the public ID / URL.
"""

import hashlib
import time

from fastapi import HTTPException

from .config import settings


def build_upload_signature(params: dict) -> str:
    """Cloudinary signed-upload signature (SHA-1 of sorted params + secret)."""
    secret = settings.cloudinary_api_secret
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Cloudinary is not configured (CLOUDINARY_API_SECRET missing)",
        )
    to_sign = "&".join(f"{k}={params[k]}" for k in sorted(params))
    to_sign += secret
    return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()


def upload_params() -> dict:
    """Parameters the client needs for a signed direct upload."""
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key:
        raise HTTPException(
            status_code=503,
            detail="Cloudinary is not configured",
        )
    timestamp = int(time.time())
    params = {"timestamp": str(timestamp)}
    return {
        "cloud_name": settings.cloudinary_cloud_name,
        "api_key": settings.cloudinary_api_key,
        "timestamp": timestamp,
        "signature": build_upload_signature(params),
    }
