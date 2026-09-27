"""Offline sync: idempotent application of batched client changes.

The backend is authoritative. Each operation carries an idempotency key; the key
is recorded in `sync_operations` with the created entity id, so a retried batch
replays the result instead of creating duplicates.
"""

from .schemas import (
    LotItemSyncPayload,
    LotSyncPayload,
    PaymentSyncPayload,
    SyncOperation,
    SyncResult,
    TransactionSyncPayload,
    WeightSyncPayload,
)
from .routers.lots import _owned_lot_id
from .routers.transactions import _owned_txn


async def _create_entity(conn, principal, collector_id: str, op: SyncOperation) -> str:
    if op.entity_type == "lot":
        p = LotSyncPayload(**op.payload)
        pickup = None
        if p.latitude is not None and p.longitude is not None:
            pickup = f"SRID=4326;POINT({p.longitude} {p.latitude})"
        await conn.execute(
            "INSERT INTO lots (id, collector_id, status, title, notes, pickup_address, pickup_location) "
            "VALUES (%s::uuid, %s::uuid, 'draft', %s, %s, %s, %s::geography)",
            (op.id, collector_id, p.title, p.notes, p.pickup_address, pickup),
        )
        return op.id

    if op.entity_type == "lot_item":
        p = LotItemSyncPayload(**op.payload)
        await _owned_lot_id(conn, p.lot_id, collector_id)
        await conn.execute(
            "INSERT INTO lot_items (id, lot_id, collector_category_id, material_category_id, "
            "material_subcategory_id, kind, description, quantity, declared_weight_kg, "
            "condition_id, classification_source) "
            "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s::uuid, %s)",
            (
                op.id,
                p.lot_id,
                p.collector_category_id,
                p.material_category_id,
                p.material_subcategory_id,
                p.kind,
                p.description,
                p.quantity,
                p.declared_weight_kg,
                p.condition_id,
                p.classification_source,
            ),
        )
        return op.id

    if op.entity_type == "transaction":
        p = TransactionSyncPayload(**op.payload)
        await _owned_lot_id(conn, p.lot_id, collector_id)
        await conn.execute(
            "INSERT INTO transactions (id, lot_id, collector_id, recycler_organization_id, "
            "match_id, status) VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid, 'LOT_CREATED')",
            (op.id, p.lot_id, collector_id, p.recycler_organization_id, p.match_id),
        )
        await conn.execute(
            "INSERT INTO transaction_events (transaction_id, event_type, to_status) "
            "VALUES (%s::uuid, 'LOT_CREATED', 'LOT_CREATED')",
            (op.id,),
        )
        return op.id

    if op.entity_type == "weight":
        p = WeightSyncPayload(**op.payload)
        await _owned_txn(conn, p.transaction_id, collector_id)
        await conn.execute(
            "INSERT INTO weights (id, transaction_id, weight_type, weight_kg, source, measured_by_user_id) "
            "VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s::uuid)",
            (op.id, p.transaction_id, p.weight_type, p.weight_kg, p.source, principal.user_id),
        )
        if p.weight_type == "final":
            await conn.execute(
                "UPDATE transactions SET final_weight_kg = %s WHERE id = %s::uuid",
                (p.weight_kg, p.transaction_id),
            )
        return op.id

    if op.entity_type == "payment":
        p = PaymentSyncPayload(**op.payload)
        await _owned_txn(conn, p.transaction_id, collector_id)
        await conn.execute(
            "INSERT INTO payments (id, transaction_id, amount, currency, method, status, "
            "payee_user_id, reference) "
            "VALUES (%s::uuid, %s::uuid, %s, 'INR', %s, 'recorded', %s::uuid, %s)",
            (op.id, p.transaction_id, p.amount, p.method, principal.user_id, p.reference),
        )
        return op.id

    raise ValueError(f"Unsupported entity_type: {op.entity_type}")


async def apply_operation(conn, principal, collector_id: str, op: SyncOperation) -> SyncResult:
    cur = await conn.execute(
        "SELECT entity_id::text, status FROM sync_operations WHERE idempotency_key = %s",
        (op.idempotency_key,),
    )
    row = await cur.fetchone()
    if row is not None:
        if row[1] == "applied":
            return SyncResult(
                idempotency_key=op.idempotency_key,
                entity_id=row[0],
                status="replayed",
            )
        return SyncResult(
            idempotency_key=op.idempotency_key,
            status="error",
            error=f"idempotency key already in state {row[1]}",
        )

    entity_id = await _create_entity(conn, principal, collector_id, op)
    await conn.execute(
        "INSERT INTO sync_operations (idempotency_key, user_id, entity_type, entity_id, "
        "operation, status, synced_at) "
        "VALUES (%s, %s::uuid, %s, %s::uuid, 'create', 'applied', now())",
        (op.idempotency_key, principal.user_id, op.entity_type, entity_id),
    )
    return SyncResult(
        idempotency_key=op.idempotency_key,
        entity_id=entity_id,
        status="applied",
    )
