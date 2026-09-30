"""Recycler onboarding + verification status."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..db import get_db
from ..dependencies import require_role
from ..recyclers import effective_verification
from ..schemas import (
    MaterialAcceptanceCreate,
    RecyclerOrganizationCreate,
    RecyclerOrganizationOut,
)

router = APIRouter()


@router.post(
    "/recycler/organizations",
    response_model=RecyclerOrganizationOut,
    status_code=201,
)
async def create_recycler(
    body: RecyclerOrganizationCreate,
    principal: Principal = Depends(require_role("super_admin", "platform_admin", "recycler")),
    conn=Depends(get_db),
) -> RecyclerOrganizationOut:
    org_cur = await conn.execute(
        "INSERT INTO organizations (name, organization_type) VALUES (%s, 'recycler') "
        "RETURNING id::text",
        (body.name,),
    )
    org_id = (await org_cur.fetchone())[0]

    ro_cur = await conn.execute(
        "INSERT INTO recycler_organizations (organization_id, gstin, registration_number) "
        "VALUES (%s::uuid, %s, %s) RETURNING id::text",
        (org_id, body.gstin, body.registration_number),
    )
    ro_id = (await ro_cur.fetchone())[0]

    if body.facility_name:
        location = None
        if body.facility_latitude is not None and body.facility_longitude is not None:
            location = f"SRID=4326;POINT({body.facility_longitude} {body.facility_latitude})"
        await conn.execute(
            "INSERT INTO recycler_facilities (recycler_organization_id, name, location) "
            "VALUES (%s::uuid, %s, %s::geography)",
            (ro_id, body.facility_name, location),
        )

    if body.authorization_number:
        verification_date = (
            datetime.now(timezone.utc) if body.status == "verified" else None
        )
        await conn.execute(
            "INSERT INTO recycler_authorizations (recycler_organization_id, "
            "authorization_number, issuing_authority, authorization_type, issue_date, "
            "expiry_date, verification_source, verification_date, status) "
            "VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                ro_id,
                body.authorization_number,
                body.issuing_authority,
                body.authorization_type,
                body.issue_date,
                body.expiry_date,
                body.verification_source,
                verification_date,
                body.status,
            ),
        )

    eff = await effective_verification(conn, ro_id)
    await record_audit(
        conn,
        action="recycler.created",
        actor_user_id=principal.user_id,
        entity_type="recycler_organization",
        entity_id=ro_id,
    )
    return RecyclerOrganizationOut(
        id=ro_id,
        organization_id=org_id,
        name=body.name,
        gstin=body.gstin,
        registration_number=body.registration_number,
        status=eff["status"],
        verified=eff["verified"],
        authorization=eff["authorization"],
    )


@router.get("/recycler/organizations", response_model=list[RecyclerOrganizationOut])
async def list_recyclers(
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> list[RecyclerOrganizationOut]:
    # Organization isolation: a non-admin only ever sees their own organization's
    # record. Admins (who have no organization_id) see all.
    cur = await conn.execute(
        "SELECT ro.id::text, ro.organization_id::text, o.name, ro.gstin, ro.registration_number "
        "FROM recycler_organizations ro JOIN organizations o ON o.id = ro.organization_id "
        "WHERE (%s::uuid IS NULL OR ro.organization_id = %s::uuid) "
        "ORDER BY o.name",
        (principal.organization_id, principal.organization_id),
    )
    rows = await cur.fetchall()
    out = []
    for r in rows:
        eff = await effective_verification(conn, r[0])
        out.append(
            RecyclerOrganizationOut(
                id=r[0],
                organization_id=r[1],
                name=r[2],
                gstin=r[3],
                registration_number=r[4],
                status=eff["status"],
                verified=eff["verified"],
                authorization=eff["authorization"],
            )
        )
    return out


@router.post("/recycler/organizations/{recycler_id}/acceptance", status_code=201)
async def add_acceptance(
    recycler_id: str,
    body: MaterialAcceptanceCreate,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> dict:
    await conn.execute(
        "INSERT INTO recycler_material_acceptance (recycler_organization_id, material_category_id, is_accepted) "
        "VALUES (%s::uuid, %s::uuid, %s) "
        "ON CONFLICT (recycler_organization_id, material_category_id, material_subcategory_id) "
        "DO UPDATE SET is_accepted = EXCLUDED.is_accepted",
        (recycler_id, body.material_category_id, body.is_accepted),
    )
    return {"status": "ok"}


# ------------------------------------------------------- admin: recycler ops


@router.post("/admin/recyclers/{recycler_id}/pickup")
async def set_pickup(
    recycler_id: str,
    body: dict,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> dict:
    """Update operational flags that matching depends on (pickup, transport)."""
    allowed = {
        "pickup_available", "provides_pickup", "accepts_walkins", "transport_rate_per_km",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(
            status_code=422,
            detail=f"no updatable fields; expected any of {sorted(allowed)}",
        )
    if "transport_rate_per_km" in updates:
        rate = updates["transport_rate_per_km"]
        if rate is not None and (float(rate) < 0 or float(rate) > 1000):
            raise HTTPException(status_code=422, detail="transport_rate_per_km must be 0..1000")

    sets = ", ".join(f"{k} = %s" for k in updates)
    cur = await conn.execute(
        f"UPDATE recycler_organizations SET {sets} WHERE id = %s::uuid RETURNING id::text",
        (*updates.values(), recycler_id),
    )
    if await cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Recycler not found")

    await record_audit(
        conn,
        action="recycler.updated",
        actor_user_id=principal.user_id,
        entity_type="recycler_organization",
        entity_id=recycler_id,
        after=updates,
    )
    return {"id": recycler_id, "updated": list(updates)}


@router.get("/admin/material-categories")
async def list_material_categories(
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[dict]:
    """Flat category list for admin pickers (review queues, acceptance)."""
    cur = await conn.execute(
        "SELECT id::text, code, name, kind FROM material_categories "
        "WHERE is_active ORDER BY kind, sort_order"
    )
    return [
        {"id": r[0], "code": r[1], "name": r[2], "kind": r[3]} for r in await cur.fetchall()
    ]


@router.get("/recycler/organizations/{recycler_id}", response_model=RecyclerOrganizationOut)
async def get_recycler(
    recycler_id: str,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> RecyclerOrganizationOut:
    cur = await conn.execute(
        "SELECT ro.id::text, ro.organization_id::text, o.name, ro.gstin, ro.registration_number "
        "FROM recycler_organizations ro JOIN organizations o ON o.id = ro.organization_id "
        "WHERE ro.id = %s::uuid",
        (recycler_id,),
    )
    r = await cur.fetchone()
    if r is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Recycler not found")
    eff = await effective_verification(conn, r[0])
    return RecyclerOrganizationOut(
        id=r[0],
        organization_id=r[1],
        name=r[2],
        gstin=r[3],
        registration_number=r[4],
        status=eff["status"],
        verified=eff["verified"],
        authorization=eff["authorization"],
    )


@router.get("/recycler/verified", response_model=list[RecyclerOrganizationOut])
async def verified_recyclers(
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[RecyclerOrganizationOut]:
    """Recyclers with a non-expired `verified` authorization (used by matching)."""
    today = date.today()
    cur = await conn.execute(
        "SELECT DISTINCT ro.id::text, ro.organization_id::text, o.name, ro.gstin, "
        "ro.registration_number "
        "FROM recycler_organizations ro "
        "JOIN organizations o ON o.id = ro.organization_id "
        "JOIN recycler_authorizations a ON a.recycler_organization_id = ro.id "
        "WHERE a.status = 'verified' AND (a.expiry_date IS NULL OR a.expiry_date >= %s) "
        "ORDER BY o.name",
        (today,),
    )
    rows = await cur.fetchall()
    return [
        RecyclerOrganizationOut(
            id=r[0],
            organization_id=r[1],
            name=r[2],
            gstin=r[3],
            registration_number=r[4],
            status="verified",
            verified=True,
            authorization=None,
        )
        for r in rows
    ]
