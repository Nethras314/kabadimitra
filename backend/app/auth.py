"""Authentication: verify Supabase JWTs and resolve the request principal.

Supabase Auth is the identity provider. The backend verifies the access token
against the project's JWKS, then maps `sub` to our own `users` table (creating
a minimal row on first login).
"""

import time
from dataclasses import dataclass, field

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .db import get_db

_JWKS: dict | None = None
_JWKS_FETCHED_AT: float = 0.0
_JWKS_TTL_SECONDS: float = 3600.0

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    sub: str
    user_id: str | None = None
    roles: list[str] = field(default_factory=list)
    organization_id: str | None = None
    preferred_locale: str = "en"

    def has_role(self, *codes: str) -> bool:
        return bool(set(codes) & set(self.roles))


def _fetch_jwks() -> dict:
    global _JWKS, _JWKS_FETCHED_AT
    now = time.time()
    if _JWKS is None or (now - _JWKS_FETCHED_AT) > _JWKS_TTL_SECONDS:
        resp = httpx.get(settings.supabase_jwks_url, timeout=10.0)
        resp.raise_for_status()
        _JWKS = resp.json()
        _JWKS_FETCHED_AT = now
    return _JWKS


def verify_token(token: str) -> dict:
    jwks = _fetch_jwks()
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    key = None
    for jwk in jwks.get("keys", []):
        if jwk.get("kid") == kid:
            key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            break
    if key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key")

    issuer = f"{settings.supabase_url}{settings.jwt_issuer_suffix}"
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=issuer,
            options={"verify_exp": True},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return verify_token(creds.credentials)


async def get_or_create_user(conn, sub: str, email: str | None, phone: str | None) -> dict:
    cur = await conn.execute(
        "SELECT id::text, organization_id::text, preferred_locale FROM users WHERE id = %s::uuid",
        (sub,),
    )
    row = await cur.fetchone()
    if row is None:
        await conn.execute(
            "INSERT INTO users (id, email, phone) VALUES (%s::uuid, %s, %s) "
            "ON CONFLICT (id) DO NOTHING",
            (sub, email, phone),
        )
        cur = await conn.execute(
            "SELECT id::text, organization_id::text, preferred_locale FROM users WHERE id = %s::uuid",
            (sub,),
        )
        row = await cur.fetchone()
    return {"id": row[0], "organization_id": row[1], "preferred_locale": row[2]}


async def _load_roles(conn, sub: str) -> list[str]:
    cur = await conn.execute(
        "SELECT r.code FROM user_roles ur "
        "JOIN roles r ON r.id = ur.role_id "
        "WHERE ur.user_id = %s::uuid",
        (sub,),
    )
    rows = await cur.fetchall()
    return [r[0] for r in rows]


async def get_principal(
    claims: dict = Depends(get_current_user),
    conn=Depends(get_db),
) -> Principal:
    sub = claims["sub"]
    user = await get_or_create_user(conn, sub, claims.get("email"), claims.get("phone"))
    roles = await _load_roles(conn, sub)
    return Principal(
        sub=sub,
        user_id=user["id"],
        roles=roles,
        organization_id=user["organization_id"],
        preferred_locale=user["preferred_locale"],
    )
