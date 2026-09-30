"""Collector earnings ledger.

The spec asks for an "easy-to-understand earnings ledger showing transactions,
payments, and pending dues". This is that: a plain-language summary plus the
per-transaction list, with pending dues derived from the lifecycle (a
transaction that reached HANDOVER_CONFIRMED but has no payment is due).
"""

from fastapi import APIRouter, Depends, Query

from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..db import get_db

router = APIRouter()

# Lifecycle states where the recycler owes the collector money.
_DUE_STATES = ("HANDOVER_CONFIRMED", "PAYMENT_RECORDED")


@router.get("/collectors/me/earnings")
async def earnings(
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Total earned, paid, and pending, plus a per-transaction list."""
    collector_id = await require_collector(conn, principal)

    cur = await conn.execute(
        """
        SELECT
            COALESCE(SUM(t.net_earnings) FILTER (WHERE t.status = ANY(%s)), 0),
            COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'confirmed'), 0),
            COALESCE(SUM(t.net_earnings) FILTER (
                WHERE t.status = 'HANDOVER_CONFIRMED'
            ), 0),
            COUNT(*) FILTER (WHERE t.status = ANY(%s)),
            COUNT(*) FILTER (WHERE t.status = 'COMPLETED')
        FROM transactions t
        LEFT JOIN payments p ON p.transaction_id = t.id
        WHERE t.collector_id = %s::uuid
        """,
        (list(_DUE_STATES), list(_DUE_STATES), collector_id),
    )
    totals = await cur.fetchone()

    cur = await conn.execute(
        """
        SELECT t.id::text,
               t.status,
               t.created_at,
               t.final_weight_kg,
               t.net_earnings,
               COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'confirmed'), 0) AS paid,
               ro.organization_id IS NOT NULL AS has_recycler,
               o.name AS recycler_name
        FROM transactions t
        LEFT JOIN recycler_organizations ro ON ro.id = t.recycler_organization_id
        LEFT JOIN organizations o ON o.id = ro.organization_id
        LEFT JOIN payments p ON p.transaction_id = t.id
        WHERE t.collector_id = %s::uuid
        GROUP BY t.id, ro.organization_id, o.name
        ORDER BY t.created_at DESC
        LIMIT 100
        """,
        (collector_id,),
    )
    items = list(await cur.fetchall())

    rows = []
    for r in items:
        earned = float(r[4]) if r[4] is not None else 0.0
        paid = float(r[5]) if r[5] is not None else 0.0
        pending = max(0.0, earned - paid)
        rows.append(
            {
                "transaction_id": r[0],
                "status": r[1],
                "date": r[2],
                "weight_kg": float(r[3]) if r[3] is not None else None,
                "recycler_name": r[7],
                "earned": round(earned, 2),
                "paid": round(paid, 2),
                "pending": round(pending, 2),
                "state": "paid" if pending == 0 else "due",
            }
        )

    total_earned = float(totals[0] or 0)
    total_paid = float(totals[1] or 0)
    total_pending = float(totals[2] or 0)

    return {
        "currency": "INR",
        "summary": {
            "total_earned": round(total_earned, 2),
            "total_paid": round(total_paid, 2),
            "total_pending_due": round(total_pending, 2),
            "transaction_count": int(totals[3] or 0),
            "completed_count": int(totals[4] or 0),
        },
        "items": rows,
    }


@router.get("/collectors/me/earnings/summary-text")
async def earnings_summary_text(
    locale: str = Query("en"),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Plain-language summary for voice playback / large-text display."""
    data = await earnings(principal, conn)
    s = data["summary"]
    t = {
        "en": (
            f"You have earned {s['total_earned']} rupees in total. "
            f"{s['total_paid']} rupees have been paid. "
            f"{s['total_pending_due']} rupees are still due."
        ),
        "hi": (
            f"आपने कुल {s['total_earned']} रुपये कमाए हैं। "
            f"{s['total_paid']} रुपये मिल चुके हैं। "
            f"{s['total_pending_due']} रुपये अभी बाकी हैं।"
        ),
        "mr": (
            f"तुम्ही एकूण {s['total_earned']} रुपये कमावले आहेत. "
            f"{s['total_paid']} रुपये मिळाले आहेत. "
            f"{s['total_pending_due']} रुपये अद्याप बाकी आहेत."
        ),
    }
    return {
        "locale": locale,
        "text": t.get(locale, t["en"]),
        "summary": s,
    }
