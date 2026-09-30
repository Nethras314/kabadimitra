"""Operations: disputes, notifications, AI escalation, analytics, QR payloads.

These are the workflow surfaces the spec asks for but that had no API.
"""

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.types.json import Jsonb

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..db import get_db
from ..dependencies import require_role

router = APIRouter()

REASON_CODES = ("price", "weight", "quality", "payment", "damage", "other")


# ==================================================================== disputes


async def _txn_collector(conn, txn_id: str, user_id: str) -> str:
    cur = await conn.execute(
        "SELECT t.collector_id::text, c.user_id::text FROM transactions t "
        "JOIN lots l ON l.id = t.lot_id "
        "JOIN collectors c ON c.id = l.collector_id "
        "WHERE t.id = %s::uuid",
        (txn_id,),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return r[0]


@router.post("/transactions/{txn_id}/disputes", status_code=201)
async def raise_dispute(
    txn_id: str,
    body: dict,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Either side may raise a dispute against a transaction."""
    reason = (body.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="reason is required")
    reason_code = body.get("reason_code", "other")
    if reason_code not in REASON_CODES:
        raise HTTPException(status_code=422, detail=f"reason_code must be one of {REASON_CODES}")

    # Authorization: the raiser must be the collector or the matched recycler.
    cur = await conn.execute(
        "SELECT collector_id::text, recycler_organization_id::text FROM transactions "
        "WHERE id = %s::uuid",
        (txn_id,),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    is_collector = False
    cur = await conn.execute(
        "SELECT c.user_id::text FROM lots l JOIN collectors c ON c.id = l.collector_id "
        "WHERE l.id = (SELECT lot_id FROM transactions WHERE id = %s::uuid)",
        (txn_id,),
    )
    owner = await cur.fetchone()
    is_collector = owner is not None and owner[0] == principal.user_id

    is_recycler = False
    if r[1]:
        cur = await conn.execute(
            "SELECT 1 FROM users WHERE id = %s::uuid AND organization_id = "
            "(SELECT organization_id FROM recycler_organizations WHERE id = %s::uuid)",
            (principal.user_id, r[1]),
        )
        is_recycler = await cur.fetchone() is not None

    is_admin = principal.has_role("super_admin", "platform_admin", "support", "operations_admin")
    if not (is_collector or is_recycler or is_admin):
        raise HTTPException(status_code=403, detail="Not a party to this transaction")

    cur = await conn.execute(
        "INSERT INTO disputes (transaction_id, raised_by_user_id, reason, reason_code, "
        "category, status) VALUES (%s::uuid, %s::uuid, %s, %s, %s, 'open') RETURNING id::text",
        (txn_id, principal.user_id, reason, reason_code, reason_code),
    )
    dispute_id = (await cur.fetchone())[0]
    await conn.execute(
        "INSERT INTO dispute_events (dispute_id, event_type, actor_user_id, note) "
        "VALUES (%s::uuid, 'RAISED', %s::uuid, %s)",
        (dispute_id, principal.user_id, reason),
    )
    await record_audit(
        conn,
        action="dispute.raised",
        actor_user_id=principal.user_id,
        entity_type="dispute",
        entity_id=dispute_id,
        after={"reason_code": reason_code, "transaction_id": txn_id},
    )
    return {"id": dispute_id, "transaction_id": txn_id, "status": "open"}


@router.get("/disputes", response_model=list[dict])
async def list_disputes(
    status: str | None = None,
    transaction_id: str | None = None,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[dict]:
    """Open disputes for review, or the ones a collector raised."""
    if principal.has_role("super_admin", "platform_admin", "support", "operations_admin"):
        where, params = "TRUE", []
    else:
        where = (
            "d.raised_by_user_id = %s::uuid OR d.transaction_id IN ("
            "  SELECT t.id FROM transactions t JOIN lots l ON l.id = t.lot_id"
            "  JOIN collectors c ON c.id = l.collector_id WHERE c.user_id = %s::uuid)"
        )
        params = [principal.user_id, principal.user_id]

    if status:
        where += " AND d.status = %s"
        params.append(status)
    if transaction_id:
        where += " AND d.transaction_id = %s::uuid"
        params.append(transaction_id)

    cur = await conn.execute(
        f"""
        SELECT d.id::text, d.transaction_id::text, d.reason, d.reason_code, d.status,
               d.resolution, d.created_at, o.name AS recycler_name
        FROM disputes d
        JOIN transactions t ON t.id = d.transaction_id
        LEFT JOIN recycler_organizations ro ON ro.id = t.recycler_organization_id
        LEFT JOIN organizations o ON o.id = ro.organization_id
        WHERE {where}
        ORDER BY
            CASE d.status WHEN 'open' THEN 0 WHEN 'under_review' THEN 1 ELSE 2 END,
            d.created_at DESC
        LIMIT 200
        """,
        params,
    )
    return [
        {
            "id": r[0], "transaction_id": r[1], "reason": r[2], "reason_code": r[3],
            "status": r[4], "resolution": r[5], "created_at": r[6],
            "recycler_name": r[7],
        }
        for r in await cur.fetchall()
    ]


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    body: dict,
    principal: Principal = Depends(
        require_role("super_admin", "platform_admin", "operations_admin")
    ),
    conn=Depends(get_db),
) -> dict:
    resolution = (body.get("resolution") or "").strip()
    if not resolution:
        raise HTTPException(status_code=422, detail="resolution is required")
    status = body.get("status", "resolved")
    if status not in ("under_review", "resolved", "closed"):
        raise HTTPException(status_code=422, detail="invalid status")

    cur = await conn.execute(
        "UPDATE disputes SET status = %s, resolution = %s, assigned_to_user_id = %s::uuid, "
        "resolved_at = CASE WHEN %s = 'closed' THEN now() ELSE resolved_at END "
        "WHERE id = %s::uuid RETURNING transaction_id::text",
        (status, resolution, principal.user_id, status, dispute_id),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Dispute not found")

    await conn.execute(
        "INSERT INTO dispute_events (dispute_id, event_type, actor_user_id, note) "
        "VALUES (%s::uuid, %s, %s::uuid, %s)",
        (dispute_id, status.upper(), principal.user_id, resolution),
    )
    await record_audit(
        conn,
        action=f"dispute.{status}",
        actor_user_id=principal.user_id,
        entity_type="dispute",
        entity_id=dispute_id,
    )
    return {"id": dispute_id, "status": status}


# =============================================================== notifications


async def _notify(
    conn,
    *,
    user_id: str,
    type_: str,
    title: str,
    body_: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> None:
    """Write an in-app notification. Always succeeds; push is a later step."""
    await conn.execute(
        "INSERT INTO notifications (user_id, type, title, body, channel, entity_type, entity_id) "
        "VALUES (%s::uuid, %s, %s, %s, 'in_app', %s, %s::uuid)",
        (user_id, type_, title, body_, entity_type, entity_id),
    )


@router.get("/notifications", response_model=list[dict])
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[dict]:
    cur = await conn.execute(
        "SELECT id::text, type, title, body, is_read, entity_type, entity_id::text, created_at "
        "FROM notifications WHERE user_id = %s::uuid "
        + ("AND is_read = false " if unread_only else "")
        + "ORDER BY created_at DESC LIMIT %s",
        (principal.user_id, limit),
    )
    return [
        {
            "id": r[0], "type": r[1], "title": r[2], "body": r[3], "is_read": r[4],
            "entity_type": r[5], "entity_id": r[6], "created_at": r[7],
        }
        for r in await cur.fetchall()
    ]


@router.get("/notifications/unread-count")
async def unread_count(
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    cur = await conn.execute(
        "SELECT count(*)::int FROM notifications WHERE user_id = %s::uuid AND is_read = false",
        (principal.user_id,),
    )
    return {"unread": (await cur.fetchone())[0]}


@router.post("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    cur = await conn.execute(
        "UPDATE notifications SET is_read = true, read_at = now() "
        "WHERE id = %s::uuid AND user_id = %s::uuid RETURNING id::text",
        (notification_id, principal.user_id),
    )
    if await cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"id": notification_id, "is_read": True}


# ================================================================= escalation


@router.post("/ai-decisions/{decision_id}/escalate", status_code=201)
async def escalate_decision(
    decision_id: str,
    body: dict | None = None,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Send an uncertain classification for human review (recycler, then admin)."""
    cur = await conn.execute(
        "SELECT d.id::text, d.lot_item_id::text, d.status, d.confidence "
        "FROM ai_decisions d WHERE d.id = %s::uuid",
        (decision_id,),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if r[2] != "suggested":
        raise HTTPException(status_code=409, detail="Decision already processed")

    stage = (body or {}).get("stage", "recycler")
    if stage not in ("recycler", "admin"):
        raise HTTPException(status_code=422, detail="stage must be recycler or admin")

    cur = await conn.execute(
        "INSERT INTO ai_escalations (decision_id, lot_item_id, stage, reason, raised_by_user_id) "
        "VALUES (%s::uuid, %s::uuid, %s, %s, %s::uuid) RETURNING id::text",
        (decision_id, r[1], stage, (body or {}).get("reason"), principal.user_id),
    )
    esc_id = (await cur.fetchone())[0]
    await record_audit(
        conn,
        action="ai.escalated",
        actor_user_id=principal.user_id,
        entity_type="ai_escalation",
        entity_id=esc_id,
        after={"stage": stage, "confidence": float(r[3]) if r[3] is not None else None},
    )
    return {"id": esc_id, "decision_id": decision_id, "stage": stage}


@router.get("/ai-escalations", response_model=list[dict])
async def list_escalations(
    stage: str | None = None,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[dict]:
    """Review queue. Recyclers and admins see it; collectors see their own."""
    if principal.has_role("super_admin", "platform_admin", "data_ai_admin", "recycler"):
        where, params = "TRUE", []
    else:
        where = "e.raised_by_user_id = %s::uuid"
        params = [principal.user_id]
    if stage:
        where += " AND e.stage = %s"
        params.append(stage)

    cur = await conn.execute(
        f"""
        SELECT e.id::text, e.decision_id::text, e.lot_item_id::text, e.stage, e.reason,
               e.resolution, e.created_at, li.description, li.declared_weight_kg
        FROM ai_escalations e
        LEFT JOIN lot_items li ON li.id = e.lot_item_id
        WHERE {where}
        ORDER BY e.created_at DESC LIMIT 200
        """,
        params,
    )
    return [
        {
            "id": r[0], "decision_id": r[1], "lot_item_id": r[2], "stage": r[3],
            "reason": r[4], "resolution": r[5], "created_at": r[6],
            "item_description": r[7], "weight_kg": r[8],
        }
        for r in await cur.fetchall()
    ]


@router.post("/ai-escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    body: dict,
    principal: Principal = Depends(
        require_role("super_admin", "platform_admin", "data_ai_admin", "recycler")
    ),
    conn=Depends(get_db),
) -> dict:
    """Reviewer supplies the correct category; it is recorded as training data."""
    category_id = body.get("category_id")
    if not category_id:
        raise HTTPException(status_code=422, detail="category_id is required")

    cur = await conn.execute(
        "SELECT decision_id::text, lot_item_id::text, stage FROM ai_escalations WHERE id = %s::uuid",
        (escalation_id,),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Escalation not found")

    # Apply the human decision to the item and the AI decision.
    if r[1]:
        await conn.execute(
            "UPDATE lot_items SET material_category_id = %s::uuid, "
            "kind = (SELECT kind FROM material_categories WHERE id = %s::uuid), "
            "classification_source = 'recycler' WHERE id = %s::uuid",
            (category_id, category_id, r[1]),
        )
    await conn.execute(
        "UPDATE ai_decisions SET status = 'corrected', predicted_category_id = %s::uuid "
        "WHERE id = %s::uuid",
        (category_id, r[0]),
    )
    # Corrections are feedback candidates, never automatic ground truth.
    await conn.execute(
        "INSERT INTO ai_corrections (ai_decision_id, corrected_category_id, "
        "corrected_by_user_id, correction_type, is_training_candidate, note) "
        "VALUES (%s::uuid, %s::uuid, %s::uuid, 'category', true, %s)",
        (r[0], category_id, principal.user_id, body.get("note", "human review")),
    )
    await conn.execute(
        "UPDATE ai_escalations SET stage = 'resolved', resolved_at = now(), "
        "reviewed_by_user_id = %s::uuid, resolved_category_id = %s::uuid, resolution = %s "
        "WHERE id = %s::uuid",
        (principal.user_id, category_id, body.get("note", "resolved"), escalation_id),
    )
    await record_audit(
        conn,
        action="ai.escalation.resolved",
        actor_user_id=principal.user_id,
        entity_type="ai_escalation",
        entity_id=escalation_id,
    )
    return {"id": escalation_id, "stage": "resolved", "category_id": category_id}


@router.post("/ai-escalations/{escalation_id}/escalate-to-admin")
async def escalate_to_admin(
    escalation_id: str,
    body: dict | None = None,
    principal: Principal = Depends(
        require_role("super_admin", "platform_admin", "data_ai_admin", "recycler")
    ),
    conn=Depends(get_db),
) -> dict:
    """Recycler could not decide — hand to platform admin."""
    cur = await conn.execute(
        "UPDATE ai_escalations SET stage = 'admin' WHERE id = %s::uuid AND stage = 'recycler' "
        "RETURNING id::text",
        (escalation_id,),
    )
    if await cur.fetchone() is None:
        raise HTTPException(status_code=409, detail="Escalation is not awaiting recycler review")
    await record_audit(
        conn,
        action="ai.escalation.escalated_to_admin",
        actor_user_id=principal.user_id,
        entity_type="ai_escalation",
        entity_id=escalation_id,
    )
    return {"id": escalation_id, "stage": "admin"}


# ================================================================== analytics


@router.get("/admin/analytics/overview")
async def analytics_overview(
    principal: Principal = Depends(require_role("super_admin", "platform_admin", "data_ai_admin")),
    conn=Depends(get_db),
) -> dict:
    cur = await conn.execute(
        """
        SELECT
          (SELECT count(*)::int FROM lots),
          (SELECT count(*)::int FROM lot_items),
          (SELECT count(*)::int FROM transactions),
          (SELECT count(*)::int FROM transactions WHERE status = 'COMPLETED'),
          (SELECT COALESCE(SUM(net_earnings), 0) FROM transactions),
          (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'confirmed'),
          (SELECT count(*)::int FROM recycler_organizations),
          (SELECT count(*)::int FROM recycler_authorizations
             WHERE status = 'verified' AND (expiry_date IS NULL OR expiry_date >= current_date)),
          (SELECT count(*)::int FROM price_observations WHERE verification_status = 'verified'),
          (SELECT count(*)::int FROM disputes WHERE status = 'open'),
          (SELECT count(*)::int FROM ai_escalations WHERE stage IN ('recycler','admin')),
          (SELECT count(*)::int FROM notifications WHERE is_read = false)
        """
    )
    r = await cur.fetchone()

    cur = await conn.execute(
        "SELECT status, count(*)::int FROM transactions GROUP BY status ORDER BY status"
    )
    by_status = {x[0]: x[1] for x in await cur.fetchall()}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "lots": r[0],
            "lot_items": r[1],
            "transactions": r[2],
            "transactions_completed": r[3],
            "recyclers": r[6],
            "recyclers_verified": r[7],
            "price_observations_verified": r[8],
            "open_disputes": r[9],
            "pending_escalations": r[10],
            "unread_notifications": r[11],
        },
        "money": {
            "net_earnings_total": float(r[4] or 0),
            "payments_confirmed_total": float(r[5] or 0),
            "outstanding": round(float(r[4] or 0) - float(r[5] or 0), 2),
        },
        "transactions_by_status": by_status,
        "completion_rate": (
            round(r[3] / r[2] * 100, 2) if r[2] else 0.0
        ),
    }


@router.get("/admin/analytics/earnings", response_model=list[dict])
async def analytics_earnings(
    principal: Principal = Depends(require_role("super_admin", "platform_admin", "data_ai_admin")),
    conn=Depends(get_db),
) -> list[dict]:
    """Per-collector earnings, for support and dispute triage."""
    cur = await conn.execute(
        """
        SELECT c.display_name, COUNT(t.id)::int,
               COALESCE(SUM(t.net_earnings), 0),
               COALESCE(SUM(t.net_earnings), 0) - COALESCE((
                   SELECT SUM(p.amount) FROM payments p
                   WHERE p.transaction_id IN (SELECT id FROM transactions t2 WHERE t2.collector_id = c.id)
                     AND p.status = 'confirmed'), 0)
        FROM collectors c
        LEFT JOIN transactions t ON t.collector_id = c.id
        GROUP BY c.id, c.display_name
        ORDER BY 3 DESC NULLS LAST
        LIMIT 100
        """
    )
    return [
        {
            "collector": r[0], "transactions": r[1], "net_earnings": float(r[2] or 0),
            "outstanding": round(float(r[3] or 0), 2),
        }
        for r in await cur.fetchall()
    ]


# ======================================================================== QR


@router.get("/qr/{kind}/{reference}")
async def qr_payload(
    kind: Literal["handover", "dispute"],
    reference: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Verification payload for a handover/dispute reference.

    Deliberately returns a *payload*, not an image: the client renders the QR so
    it works offline and without a server-side image library. The payload is
    the public verification URL plus a checksum, so a printed code can be
    checked without trusting the label itself.
    """
    record = await _lookup_reference(conn, kind, reference)
    if record is None:
        raise HTTPException(status_code=404, detail="Reference not found")

    import hashlib

    checksum = hashlib.sha256(f"{kind}:{reference}".encode()).hexdigest()[:12]
    base = "https://kabadimitra-tau.vercel.app"
    return {
        "kind": kind,
        "reference": reference,
        "checksum": checksum,
        "verify_url": f"{base}/verify/{kind}/{reference}",
        "state": "confirmed" if record["confirmed"] else "pending",
        "weight_kg": record["weight_kg"],
        "status": record["status"],
        "note": "Scan to verify this record. The checksum is derived from the "
                "reference and cannot be altered by relabelling a printed code.",
    }


# ------------------------------------------------------------ public verify API
# The QR code points a scanner (often a phone with no session) at /verify/...,
# which must therefore work unauthenticated. Only non-identifying, verification
# fields are exposed — no collector names, user ids, or coordinates.

VERIFY_FIELDS = (
    "reference, kind, checksum, state, status, weight_kg, "
    "recycler_name, authorization_status, raised_at, resolved_at"
)


async def _lookup_reference(conn, kind: str, reference: str) -> dict | None:
    """Fetch the minimum record needed to verify a reference."""
    if kind == "handover":
        cur = await conn.execute(
            """
            SELECT h.reference_code, h.confirmed_at, h.weight_kg, h.photo_count,
                   t.status, o.name AS recycler_name,
                   a.status AS authorization_status
            FROM handover_records h
            JOIN transactions t ON t.id = h.transaction_id
            LEFT JOIN recycler_organizations ro ON ro.id = t.recycler_organization_id
            LEFT JOIN organizations o ON o.id = ro.organization_id
            LEFT JOIN LATERAL (
                SELECT status FROM recycler_authorizations a2
                WHERE a2.recycler_organization_id = ro.id
                ORDER BY a2.expiry_date DESC NULLS LAST LIMIT 1
            ) a ON TRUE
            WHERE h.reference_code = %s
            """,
            (reference,),
        )
    else:
        cur = await conn.execute(
            "SELECT id::text, resolved_at, reason_code, status, created_at "
            "FROM disputes WHERE id::text = %s OR reason LIKE %s",
            (reference, f"%{reference}%"),
        )
    row = await cur.fetchone()
    if row is None:
        return None

    if kind == "handover":
        return {
            "reference": row[0],
            "confirmed": row[1] is not None,
            "weight_kg": float(row[2]) if row[2] is not None else None,
            "photo_count": row[3],
            "status": row[4],
            "recycler_name": row[5],
            "authorization_status": row[6],
            "raised_at": row[1],
            "resolved_at": row[1],
        }
    return {
        "reference": row[0],
        "confirmed": row[1] is not None,
        "weight_kg": None,
        "status": row[3],
        "recycler_name": None,
        "authorization_status": None,
        "raised_at": row[4],
        "resolved_at": row[1],
        "reason_code": row[2],
    }


@router.get("/verify/{kind}/{reference}")
async def verify_public(
    kind: Literal["handover", "dispute"],
    reference: str,
    conn=Depends(get_db),
) -> dict:
    """Public, unauthenticated verification of a handover/dispute reference.

    Intentionally narrow: enough to answer 'is this record genuine and complete',
    and nothing that would identify a collector or expose their location.
    """
    import hashlib

    record = await _lookup_reference(conn, kind, reference)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")

    return {
        "valid": True,
        "kind": kind,
        "reference": reference,
        "checksum": hashlib.sha256(f"{kind}:{reference}".encode()).hexdigest()[:12],
        "state": "confirmed" if record["confirmed"] else "pending",
        "status": record["status"],
        "weight_kg": record["weight_kg"],
        "photo_count": record.get("photo_count"),
        "recycler_name": record["recycler_name"],
        "authorization_status": record["authorization_status"],
        "raised_at": record["raised_at"],
        "resolved_at": record["resolved_at"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
