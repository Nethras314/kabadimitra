"""Recycler reliability scoring and quote submission.

Reliability is derived from completed transactions (never hand-entered), so a
recycler's score reflects actual behaviour: did they complete handovers, were
there disputes, how fast did they pay.
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..db import get_db
from ..dependencies import require_role

router = APIRouter()


@router.post("/recycler/reliability/refresh")
async def refresh_reliability(
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> dict:
    """Recompute the reliability snapshot for every recycler.

    score = 60% completion + 25% on-time confirmation + 15% dispute-free,
    each component clamped to 0..100. Recyclers with no history are left NULL
    so scoring can treat them as neutral rather than bad.
    """
    cur = await conn.execute(
        """
        WITH stats AS (
            SELECT t.recycler_organization_id AS rid,
                   COUNT(*) FILTER (WHERE t.status = 'COMPLETED')::int AS completed,
                   COUNT(*) FILTER (WHERE t.status IN
                       ('HANDOVER_CONFIRMED','PAYMENT_RECORDED','COMPLETED'))::int AS reached_handover,
                   COUNT(*) FILTER (WHERE d.id IS NOT NULL)::int AS disputed,
                   AVG(EXTRACT(EPOCH FROM (pc.confirmed_at - h.handed_over_at)) / 3600.0)
                       FILTER (WHERE pc.confirmed_at IS NOT NULL) AS avg_hours_to_confirm,
                   COUNT(*) FILTER (WHERE pc.confirmed_at IS NOT NULL
                                      AND pc.confirmed_at <= h.handed_over_at
                                      + INTERVAL '24 hours')::int AS on_time
            FROM transactions t
            LEFT JOIN handover_records h ON h.transaction_id = t.id
            LEFT JOIN payment_confirmations pc ON pc.payment_id IN
                (SELECT id FROM payments WHERE transaction_id = t.id)
            LEFT JOIN disputes d ON d.transaction_id = t.id
            WHERE t.recycler_organization_id IS NOT NULL
            GROUP BY t.recycler_organization_id
        )
        INSERT INTO recycler_reliability
            (recycler_organization_id, completed_transactions, disputed_transactions,
             avg_days_to_payment, on_time_rate, score, computed_at)
        SELECT s.rid,
               s.completed,
               s.disputed,
               ROUND((s.avg_hours_to_confirm / 24.0)::numeric, 2),
               CASE WHEN s.reached_handover > 0
                    THEN ROUND((s.on_time::numeric / s.reached_handover), 3) END,
               CASE WHEN s.reached_handover = 0 THEN NULL ELSE ROUND(LEAST(100,
                   60.0 * (s.completed::numeric / s.reached_handover)
                 + 25.0 * COALESCE(s.on_time::numeric / s.reached_handover, 0)
                 + 15.0 * (1.0 - LEAST(1.0, s.disputed::numeric / GREATEST(1, s.completed)))
               ), 2) END,
               now()
        FROM stats s
        ON CONFLICT (recycler_organization_id) DO UPDATE SET
            completed_transactions = EXCLUDED.completed_transactions,
            disputed_transactions = EXCLUDED.disputed_transactions,
            avg_days_to_payment = EXCLUDED.avg_days_to_payment,
            on_time_rate = EXCLUDED.on_time_rate,
            score = EXCLUDED.score,
            computed_at = EXCLUDED.computed_at
        RETURNING recycler_organization_id::text, score, completed_transactions
        """,
    )
    rows = await cur.fetchall()
    return {
        "refreshed": len(rows),
        "entries": [
            {"recycler_organization_id": r[0], "score": r[1], "completed": r[2]}
            for r in rows
        ],
    }


# ------------------------------------------------------------------- quotes


@router.post("/recycler/quotes", status_code=201)
async def submit_quote(
    lot_id: str,
    body: dict,
    principal: Principal = Depends(require_role("recycler", "super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> dict:
    """Recycler submits a price quote against a lot.

    `body`: { price_per_kg: number, total_price?: number, terms?: string,
              valid_until?: ISO datetime }
    """
    price_per_kg = body.get("price_per_kg")
    if price_per_kg is None or float(price_per_kg) <= 0:
        raise HTTPException(status_code=422, detail="price_per_kg must be positive")

    # Resolve the caller's recycler org, enforcing organization isolation: a
    # recycler may only ever act as the organization it belongs to.
    cur = await conn.execute(
        """
        SELECT ro.id::text
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        JOIN recycler_organizations ro ON ro.organization_id = u.organization_id
        WHERE u.id = %s::uuid AND r.code = 'recycler'
          AND (u.organization_id IS NULL
               OR ur.organization_id IS NULL
               OR ur.organization_id = u.organization_id)
        LIMIT 1
        """,
        (principal.user_id,),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=403, detail="No recycler organization linked to this user"
        )
    recycler_id = row[0]

    # The lot must actually be offered to this recycler.
    cur = await conn.execute(
        "SELECT 1 FROM matches WHERE lot_id = %s::uuid AND recycler_organization_id = %s::uuid",
        (lot_id, recycler_id),
    )
    if await cur.fetchone() is None:
        raise HTTPException(
            status_code=403, detail="This lot was not matched to your organization"
        )

    cur = await conn.execute(
        "INSERT INTO recycler_quotes (recycler_organization_id, lot_id, price_per_kg, "
        "total_price, terms, status, valid_until) "
        "VALUES (%s::uuid, %s::uuid, %s, %s, %s, 'submitted', %s) "
        "RETURNING id::text",
        (
            recycler_id, lot_id, price_per_kg, body.get("total_price"),
            body.get("terms"), body.get("valid_until"),
        ),
    )
    quote_id = (await cur.fetchone())[0]
    await record_audit(
        conn,
        action="quote.submitted",
        actor_user_id=principal.user_id,
        entity_type="recycler_quote",
        entity_id=quote_id,
    )
    return {"id": quote_id, "lot_id": lot_id, "status": "submitted"}


@router.get("/lots/{lot_id}/quotes")
async def list_quotes(
    lot_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[dict]:
    """Quotes for a lot, for the collector to compare."""
    from .lots import _owned_lot_id
    from ..collectors import require_collector

    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    cur = await conn.execute(
        "SELECT q.id::text, q.price_per_kg, q.total_price, q.terms, q.status, "
        "q.valid_until, q.created_at, o.name "
        "FROM recycler_quotes q "
        "JOIN recycler_organizations ro ON ro.id = q.recycler_organization_id "
        "JOIN organizations o ON o.id = ro.organization_id "
        "WHERE q.lot_id = %s::uuid ORDER BY q.price_per_kg DESC",
        (lot_id,),
    )
    rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "recycler_name": r[7],
            "price_per_kg": float(r[1]) if r[1] is not None else None,
            "total_price": float(r[2]) if r[2] is not None else None,
            "terms": r[3],
            "status": r[4],
            "valid_until": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]


@router.post("/quotes/{quote_id}/accept")
async def accept_quote(
    quote_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Collector accepts a quote, which advances the transaction to QUOTE_ACCEPTED."""
    from ..collectors import require_collector
    from .transactions import TRANSITIONS, _owned_txn

    collector_id = await require_collector(conn, principal)

    cur = await conn.execute(
        "SELECT q.lot_id::text, t.id::text, t.status "
        "FROM recycler_quotes q JOIN transactions t ON t.lot_id = q.lot_id "
        "WHERE q.id = %s::uuid",
        (quote_id,),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    await _owned_txn(conn, row[1], collector_id)

    if row[2] != "QUOTED":
        raise HTTPException(
            status_code=409,
            detail=f"Quote can only be accepted when the transaction is QUOTED (is {row[2]})",
        )

    await conn.execute(
        "UPDATE recycler_quotes SET status = 'accepted' WHERE id = %s::uuid", (quote_id,)
    )
    # Accepting a quote fixes the agreed price, and pulls in the matched
    # recycler's transport cost so net earnings is meaningful immediately.
    await conn.execute(
        """
        UPDATE transactions t SET
            status = 'QUOTE_ACCEPTED',
            recycler_organization_id = q.recycler_organization_id,
            agreed_price_per_kg = q.price_per_kg,
            transport_cost = COALESCE(m.transport_cost, t.transport_cost, 0)
        FROM recycler_quotes q
        LEFT JOIN matches m
               ON m.lot_id = q.lot_id
              AND m.recycler_organization_id = q.recycler_organization_id
        WHERE q.id = %s::uuid AND t.id = %s::uuid
        """,
        (quote_id, row[1]),
    )
    await conn.execute(
        "INSERT INTO transaction_events (transaction_id, event_type, from_status, to_status) "
        "VALUES (%s::uuid, 'QUOTE_ACCEPTED', %s, 'QUOTE_ACCEPTED')",
        (row[1], row[2]),
    )
    await record_audit(
        conn,
        action="quote.accepted",
        actor_user_id=principal.user_id,
        entity_type="recycler_quote",
        entity_id=quote_id,
    )
    return {"status": "accepted", "transaction_id": row[1]}
