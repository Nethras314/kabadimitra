"""Transaction lifecycle (state machine), weights, and payments."""

from fastapi import APIRouter, Depends, HTTPException

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..db import get_db
from ..schemas import (
    PaymentCreate,
    PaymentOut,
    TransactionCreate,
    TransactionEventOut,
    TransactionOut,
    TransitionRequest,
    WeightCreate,
    WeightOut,
)
from .lots import _owned_lot_id

router = APIRouter()

TRANSITIONS: dict[str, set[str]] = {
    "LOT_CREATED": {"CLASSIFIED"},
    "CLASSIFIED": {"QUOTED"},
    "QUOTED": {"QUOTE_ACCEPTED"},
    "QUOTE_ACCEPTED": {"PICKUP_OR_DELIVERY"},
    "PICKUP_OR_DELIVERY": {"WEIGHT_VERIFIED"},
    "WEIGHT_VERIFIED": {"HANDOVER_CONFIRMED"},
    "HANDOVER_CONFIRMED": {"PAYMENT_RECORDED"},
    "PAYMENT_RECORDED": {"COMPLETED"},
    "COMPLETED": set(),
}

_TXN_COLS = (
    "id::text, lot_id::text, collector_id::text, recycler_organization_id::text, "
    "match_id::text, status, currency, final_weight_kg, net_earnings, created_at"
)


def _txn_out(r) -> TransactionOut:
    return TransactionOut(
        id=r[0],
        lot_id=r[1],
        collector_id=r[2],
        recycler_organization_id=r[3],
        match_id=r[4],
        status=r[5],
        currency=r[6],
        final_weight_kg=float(r[7]) if r[7] is not None else None,
        net_earnings=float(r[8]) if r[8] is not None else None,
        created_at=r[9],
    )


async def _owned_txn(conn, txn_id: str, collector_id: str) -> str:
    cur = await conn.execute(
        "SELECT id::text, collector_id::text FROM transactions WHERE id = %s::uuid",
        (txn_id,),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if row[1] != collector_id:
        raise HTTPException(status_code=403, detail="Not your transaction")
    return row[0]


@router.post(
    "/lots/{lot_id}/transactions",
    response_model=TransactionOut,
    status_code=201,
)
async def create_transaction(
    lot_id: str,
    body: TransactionCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> TransactionOut:
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    cur = await conn.execute(
        "INSERT INTO transactions (lot_id, collector_id, recycler_organization_id, "
        "match_id, status) VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, 'LOT_CREATED') "
        f"RETURNING {_TXN_COLS}",
        (lot_id, collector_id, body.recycler_organization_id, body.match_id),
    )
    row = await cur.fetchone()
    await conn.execute(
        "INSERT INTO transaction_events (transaction_id, event_type, to_status) "
        "VALUES (%s::uuid, 'LOT_CREATED', 'LOT_CREATED')",
        (row[0],),
    )
    await record_audit(
        conn,
        action="transaction.created",
        actor_user_id=principal.user_id,
        entity_type="transaction",
        entity_id=row[0],
    )
    return _txn_out(row)


@router.get("/transactions/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> TransactionOut:
    collector_id = await require_collector(conn, principal)
    await _owned_txn(conn, transaction_id, collector_id)
    cur = await conn.execute(
        f"SELECT {_TXN_COLS} FROM transactions WHERE id = %s::uuid", (transaction_id,)
    )
    return _txn_out(await cur.fetchone())


@router.get(
    "/transactions/{transaction_id}/events",
    response_model=list[TransactionEventOut],
)
async def list_events(
    transaction_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[TransactionEventOut]:
    collector_id = await require_collector(conn, principal)
    await _owned_txn(conn, transaction_id, collector_id)
    cur = await conn.execute(
        "SELECT id::text, event_type, from_status, to_status, created_at "
        "FROM transaction_events WHERE transaction_id = %s::uuid ORDER BY created_at",
        (transaction_id,),
    )
    return [
        TransactionEventOut(id=r[0], event_type=r[1], from_status=r[2], to_status=r[3], created_at=r[4])
        for r in await cur.fetchall()
    ]


@router.post("/transactions/{transaction_id}/transition", response_model=TransactionOut)
async def transition(
    transaction_id: str,
    body: TransitionRequest,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> TransactionOut:
    collector_id = await require_collector(conn, principal)
    await _owned_txn(conn, transaction_id, collector_id)

    cur = await conn.execute(
        "SELECT status FROM transactions WHERE id = %s::uuid", (transaction_id,)
    )
    current = (await cur.fetchone())[0]
    if body.to_status not in TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from {current} to {body.to_status}",
        )

    cur = await conn.execute(
        "UPDATE transactions SET status = %s WHERE id = %s::uuid "
        f"RETURNING {_TXN_COLS}",
        (body.to_status, transaction_id),
    )
    row = await cur.fetchone()
    await conn.execute(
        "INSERT INTO transaction_events (transaction_id, event_type, from_status, to_status) "
        "VALUES (%s::uuid, 'STATUS_CHANGED', %s, %s)",
        (transaction_id, current, body.to_status),
    )
    await record_audit(
        conn,
        action="transaction.status_changed",
        actor_user_id=principal.user_id,
        entity_type="transaction",
        entity_id=transaction_id,
        before={"status": current},
        after={"status": body.to_status},
    )
    return _txn_out(row)


@router.post(
    "/transactions/{transaction_id}/weights",
    response_model=WeightOut,
    status_code=201,
)
async def add_weight(
    transaction_id: str,
    body: WeightCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> WeightOut:
    collector_id = await require_collector(conn, principal)
    await _owned_txn(conn, transaction_id, collector_id)

    cur = await conn.execute(
        "INSERT INTO weights (transaction_id, weight_type, weight_kg, source, measured_by_user_id) "
        "VALUES (%s::uuid, %s, %s, %s, %s::uuid) "
        "RETURNING id::text, transaction_id::text, weight_type, weight_kg, source, measured_at",
        (transaction_id, body.weight_type, body.weight_kg, body.source, principal.user_id),
    )
    row = await cur.fetchone()
    if body.weight_type == "final":
        await conn.execute(
            "UPDATE transactions SET final_weight_kg = %s WHERE id = %s::uuid",
            (body.weight_kg, transaction_id),
        )
    await record_audit(
        conn,
        action="weight.recorded",
        actor_user_id=principal.user_id,
        entity_type="weight",
        entity_id=row[0],
    )
    return WeightOut(
        id=row[0],
        transaction_id=row[1],
        weight_type=row[2],
        weight_kg=float(row[3]),
        source=row[4],
        measured_at=row[5],
    )


@router.post(
    "/transactions/{transaction_id}/payments",
    response_model=PaymentOut,
    status_code=201,
)
async def record_payment(
    transaction_id: str,
    body: PaymentCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> PaymentOut:
    collector_id = await require_collector(conn, principal)
    await _owned_txn(conn, transaction_id, collector_id)

    cur = await conn.execute(
        "INSERT INTO payments (transaction_id, amount, currency, method, status, payee_user_id, reference) "
        "VALUES (%s::uuid, %s, 'INR', %s, 'recorded', %s::uuid, %s) "
        "RETURNING id::text, transaction_id::text, amount, currency, method, status, reference, recorded_at",
        (transaction_id, body.amount, body.method, principal.user_id, body.reference),
    )
    row = await cur.fetchone()
    await record_audit(
        conn,
        action="payment.recorded",
        actor_user_id=principal.user_id,
        entity_type="payment",
        entity_id=row[0],
    )
    return PaymentOut(
        id=row[0],
        transaction_id=row[1],
        amount=float(row[2]),
        currency=row[3],
        method=row[4],
        status=row[5],
        reference=row[6],
        recorded_at=row[7],
    )


@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(
    payment_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    collector_id = await require_collector(conn, principal)
    cur = await conn.execute(
        "SELECT p.id::text, t.collector_id::text FROM payments p "
        "JOIN transactions t ON t.id = p.transaction_id WHERE p.id = %s::uuid",
        (payment_id,),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if row[1] != collector_id:
        raise HTTPException(status_code=403, detail="Not your payment")

    await conn.execute(
        "INSERT INTO payment_confirmations (payment_id, confirmed_by_user_id, confirmation_source) "
        "VALUES (%s::uuid, %s::uuid, 'app')",
        (payment_id, principal.user_id),
    )
    await conn.execute(
        "UPDATE payments SET status = 'confirmed' WHERE id = %s::uuid", (payment_id,)
    )
    return {"status": "confirmed"}
