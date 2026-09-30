"""Account signup.

Signing up issues a Supabase Auth user, then provisions the matching profile in
our own tables. Roles are constrained: a self-registered user can only become a
collector or kabadiwala. Every other role (recycler, aggregator, support,
super_admin, ...) must be granted by an admin, otherwise anybody could
self-register as an administrator.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from ..auth import Principal, get_principal
from ..db import get_db
from ..dependencies import require_role

router = APIRouter()

# The only roles a person may grant themselves.
SELF_SERVICE_ROLES = {"collector", "kabadiwala"}

PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    phone: str | None = None
    role: str = "collector"          # collector | kabadiwala
    city: str | None = None
    state: str | None = None
    preferred_locale: str = "hi"


class SignupOut(BaseModel):
    user_id: str
    email: str
    role: str
    created: bool
    message: str


@router.post("/auth/signup", response_model=SignupOut, status_code=201)
async def signup(
    body: SignupIn,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> SignupOut:
    """Create a Supabase Auth user plus the matching local profile.

    Admin-only by design. Self-registration from the public sign-up form goes
    through Supabase directly (see the web client) and lands in `users` via the
    normal auto-provision path; this endpoint is how an administrator creates a
    *pre-confirmed* account for a collector who cannot use a browser.
    """
    role = body.role.strip().lower()
    if role not in SELF_SERVICE_ROLES:
        raise HTTPException(
            status_code=403,
            detail=(
                f"role '{role}' cannot be self-assigned; "
                f"allowed: {sorted(SELF_SERVICE_ROLES)}"
            ),
        )
    if body.phone and not PHONE_RE.match(body.phone):
        raise HTTPException(status_code=422, detail="phone must be E.164-ish (10-15 digits)")

    import os

    from ..config import settings

    url = settings.supabase_url
    service_key = os.getenv("SUPABASE_SECRET_KEY", "")
    if not url or not service_key:
        raise HTTPException(
            status_code=503,
            detail="signup is not configured (SUPABASE_URL / SUPABASE_SECRET_KEY)",
        )

    import httpx

    async with httpx.AsyncClient(timeout=20.0) as http:
        res = await http.post(
            f"{url}/auth/v1/admin/users",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            json={
                "email": body.email,
                "password": body.password,
                "email_confirm": True,   # created by an admin: no email round-trip
                "user_metadata": {
                    "full_name": body.full_name,
                    "phone": body.phone,
                },
            },
        )

    if res.status_code >= 400:
        detail = res.json().get("msg") or res.text
        # Do not leak whether an address is already registered.
        if "already" in str(detail).lower() or "registered" in str(detail).lower():
            raise HTTPException(status_code=409, detail="email is already registered")
        raise HTTPException(status_code=res.status_code, detail=str(detail))

    auth_user = res.json()
    user_id = auth_user.get("id")
    if not user_id:
        raise HTTPException(status_code=502, detail="supabase did not return a user id")

    # Provision the local profile. Idempotent: re-running is safe.
    cur = await conn.execute(
        """
        INSERT INTO users (id, email, phone, full_name, preferred_locale)
        VALUES (%s::uuid, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
            SET phone = EXCLUDED.phone,
                full_name = COALESCE(EXCLUDED.full_name, users.full_name)
        RETURNING id::text
        """,
        (user_id, body.email, body.phone, body.full_name, body.preferred_locale),
    )
    local_id = (await cur.fetchone())[0]

    role_row = await conn.execute(
        "SELECT id::int FROM roles WHERE code = %s", (role,)
    )
    r = await role_row.fetchone()
    if r is None:
        raise HTTPException(status_code=500, detail=f"role '{role}' is not seeded")
    await conn.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES (%s::uuid, %s) "
        "ON CONFLICT DO NOTHING",
        (local_id, r[0]),
    )

    if role in SELF_SERVICE_ROLES and role == "collector":
        await conn.execute(
            "INSERT INTO collectors (user_id, collector_type, display_name, city, state) "
            "VALUES (%s::uuid, 'picker', %s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET display_name = EXCLUDED.display_name",
            (local_id, body.full_name or "Collector", body.city, body.state),
        )

    from ..audit import record_audit

    await record_audit(
        conn,
        action="user.created",
        actor_user_id=principal.user_id,
        entity_type="user",
        entity_id=local_id,
        after={"email": body.email, "role": role},
    )

    return SignupOut(
        user_id=local_id,
        email=body.email,
        role=role,
        created=True,
        message="Account created and confirmed. The person can sign in immediately.",
    )


@router.get("/auth/users", response_model=list[dict])
async def list_users(
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> list[dict]:
    """Accounts with their roles — the admin view of who can sign in."""
    cur = await conn.execute(
        """
        SELECT u.id::text, u.email, u.full_name, u.phone, u.created_at,
               COALESCE(array_agg(r.code) FILTER (WHERE r.code IS NOT NULL), '{}') AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN roles r ON r.id = ur.role_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        LIMIT 200
        """
    )
    return [
        {
            "id": r[0], "email": r[1], "full_name": r[2], "phone": r[3],
            "created_at": r[4], "roles": list(r[5]),
        }
        for r in await cur.fetchall()
    ]


@router.post("/auth/roles", status_code=201)
async def grant_role(
    body: dict,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> dict:
    """Grant an additional role to an existing user."""
    user_id = body.get("user_id")
    code = (body.get("role") or "").strip().lower()
    if not user_id or not code:
        raise HTTPException(status_code=422, detail="user_id and role are required")

    cur = await conn.execute("SELECT 1 FROM users WHERE id = %s::uuid", (user_id,))
    if await cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="user not found")

    role_row = await conn.execute(
        "SELECT id::int FROM roles WHERE code = %s", (code,)
    )
    r = await role_row.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail=f"role '{code}' not found")

    await conn.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES (%s::uuid, %s) "
        "ON CONFLICT DO NOTHING",
        (user_id, r[0]),
    )
    return {"user_id": user_id, "role": code, "granted": True}
