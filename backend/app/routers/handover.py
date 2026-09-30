"""Digital handover records with recycler confirmation.

The spec requires a "digital and verifiable handover/transfer record containing
photographs, weight, timestamp, GPS/location details, and a unique reference
that can be confirmed by the recycler."

The collector creates the record at the point of delivery; the recycler
independently confirms it. That second, independent step is what makes the
record verifiable rather than merely self-reported.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..db import get_db
from ..dependencies import require_role

router = APIRouter()


def _reference() -> str:
    """Human-readable handover reference, e.g. HO-7F3A21C9."""
    return "HO-" + uuid.uuid4().hex[:8].upper()


@router.post("/transactions/{transaction_id}/handover", status_code=201)
async def create_handover(
    transaction_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Collector creates the handover record for a delivered transaction."""
    collector_id = await require_collector(conn, principal)

    cur = await conn.execute(
        "SELECT collector_id::text, status FROM transactions WHERE id = %s::uuid",
        (transaction_id,),
    )
    txn = await cur.fetchone()
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn[0] != collector_id:
        raise HTTPException(status_code=403, detail="Not your transaction")
    if txn[1] not in ("WEIGHT_VERIFIED", "HANDOVER_CONFIRMED"):
        raise HTTPException(
            status_code=409,
            detail="Handover requires the weight to be verified first",
        )

    ref = _reference()
    cur = await conn.execute(
        """
        INSERT INTO handover_records
            (transaction_id, handed_over_by_user_id, reference_code,
             weight_kg, latitude, longitude, photo_count)
        SELECT t.id, %s::uuid, %s, t.final_weight_kg,
               ST_Y(l.pickup_location::geometry), ST_X(l.pickup_location::geometry),
               (SELECT count(*)::int FROM material_images mi WHERE mi.lot_id = l.id)
        FROM transactions t
        JOIN lots l ON l.id = t.lot_id
        WHERE t.id = %s::uuid
        RETURNING id::text, handed_over_at
        """,
        (principal.user_id, ref, transaction_id),
    )
    row = await cur.fetchone()

    await record_audit(
        conn,
        action="handover.created",
        actor_user_id=principal.user_id,
        entity_type="handover",
        entity_id=row[0],
        after={"reference": ref, "transaction_id": transaction_id},
    )
    return {
        "id": row[0],
        "reference": ref,
        "transaction_id": transaction_id,
        "handed_over_at": row[1],
        "status": "pending_recycler_confirmation",
    }


@router.get("/handover/{reference}")
async def get_handover(
    reference: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Verification lookup by reference. Any authenticated user may check one."""
    cur = await conn.execute(
        """
        SELECT h.id::text, h.transaction_id::text, h.handed_over_at,
               h.confirmed_at, h.weight_kg, h.latitude, h.longitude,
               h.photo_count,
               t.status AS transaction_status,
               (SELECT count(*)::int FROM payment_confirmations pc
                JOIN payments p ON p.id = pc.payment_id
                WHERE p.transaction_id = t.id) AS payment_confirmations
        FROM handover_records h
        JOIN transactions t ON t.id = h.transaction_id
        WHERE h.reference_code = %s
        """,
        (reference,),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Handover reference not found")

    return {
        "reference": reference,
        "transaction_id": r[1],
        "handed_over_at": r[2],
        "confirmed_at": r[3],
        "recycler_confirmed": r[3] is not None,
        "weight_kg": float(r[4]) if r[4] is not None else None,
        "location": (
            {"lat": float(r[5]), "lng": float(r[6])}
            if r[5] is not None and r[6] is not None
            else None
        ),
        "photo_count": r[7],
        "transaction_status": r[8],
        "payment_confirmations": r[9],
    }


@router.post("/handover/{reference}/confirm")
async def confirm_handover(
    reference: str,
    principal: Principal = Depends(
        require_role("recycler", "super_admin", "platform_admin")
    ),
    conn=Depends(get_db),
) -> dict:
    """Recycler independently confirms receipt."""
    cur = await conn.execute(
        "SELECT id::text FROM handover_records WHERE reference_code = %s", (reference,)
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Handover reference not found")

    cur = await conn.execute(
        "UPDATE handover_records SET confirmed_at = now(), confirmed_by_user_id = %s::uuid "
        "WHERE id = %s::uuid AND confirmed_at IS NULL RETURNING id::text",
        (principal.user_id, row[0]),
    )
    if (await cur.fetchone()) is None:
        raise HTTPException(status_code=409, detail="Handover already confirmed")

    await record_audit(
        conn,
        action="handover.confirmed",
        actor_user_id=principal.user_id,
        entity_type="handover",
        entity_id=row[0],
        after={"reference": reference},
    )
    return {"reference": reference, "status": "confirmed_by_recycler"}


# ---------------------------------------------------------------- recycler side


@router.get("/recycler/incoming-transactions")
async def incoming_transactions(
    principal: Principal = Depends(
        require_role("recycler", "super_admin", "platform_admin")
    ),
    conn=Depends(get_db),
) -> dict:
    """Recycler-side queue: transactions matched to this recycler."""
    cur = await conn.execute(
        """
        SELECT ro.id::text AS recycler_id
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        JOIN recycler_organizations ro ON ro.organization_id = u.organization_id
        WHERE u.id = %s::uuid AND r.code = 'recycler'
        LIMIT 1
        """,
        (principal.user_id,),
    )
    row = await cur.fetchone()
    if row is None:
        return {
            "count": 0,
            "items": [],
            "note": "No recycler organization linked to this user",
        }

    cur = await conn.execute(
        """
        SELECT t.id::text, t.status, t.created_at, t.final_weight_kg, t.net_earnings,
               (SELECT count(*)::int FROM lot_items li WHERE li.lot_id = t.lot_id) AS item_count,
               h.reference_code
        FROM transactions t
        JOIN lots l ON l.id = t.lot_id
        LEFT JOIN handover_records h ON h.transaction_id = t.id
        WHERE t.recycler_organization_id = %s::uuid
        ORDER BY t.created_at DESC
        LIMIT 100
        """,
        (row[0],),
    )
    items = await cur.fetchall()
    return {
        "count": len(items),
        "items": [
            {
                "transaction_id": i[0],
                "reference": i[6],
                "status": i[1],
                "date": i[2],
                "weight_kg": float(i[3]) if i[3] is not None else None,
                "value": float(i[4]) if i[4] is not None else None,
                "item_count": i[5],
            }
            for i in items
        ],
    }
