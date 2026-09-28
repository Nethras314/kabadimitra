"""Transaction data access (with idempotency for create/handover/payment)."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from psycopg_pool import AsyncConnectionPool

from ..models.audit import AuditEvent
from ..models.transaction import (
    Dispute,
    HandoverRecord,
    Payment,
    Transaction,
    TransactionEvent,
    WeightRecord,
)


class TransactionRepository(ABC):
    @abstractmethod
    async def create_transaction(self, transaction: Transaction) -> tuple[str, bool]:
        """Create a transaction; return (id, created). created=False on replay."""

    @abstractmethod
    async def get_transaction(
        self, transaction_id: str, collector_id: str
    ) -> Transaction | None: ...

    @abstractmethod
    async def apply_transition(
        self, transaction_id: str, from_status: str, to_status: str, actor_user_id: str | None
    ) -> None:
        """Atomically update status + write a transaction event + audit event."""

    @abstractmethod
    async def add_audit_event(self, event: AuditEvent) -> None: ...

    @abstractmethod
    async def add_weight(self, weight: WeightRecord) -> str: ...

    @abstractmethod
    async def set_final_weight(self, transaction_id: str, weight_kg: float) -> None: ...

    @abstractmethod
    async def add_handover(self, handover: HandoverRecord) -> tuple[str, bool]: ...

    @abstractmethod
    async def add_payment(self, payment: Payment) -> tuple[str, bool]: ...

    @abstractmethod
    async def confirm_payment(self, payment_id: str, actor_user_id: str | None) -> None: ...

    @abstractmethod
    async def add_dispute(self, dispute: Dispute) -> str: ...

    @abstractmethod
    async def completed_transactions(self, collector_id: str) -> list[Transaction]: ...

    @abstractmethod
    async def events(self, transaction_id: str) -> list[TransactionEvent]: ...

    @abstractmethod
    async def audit_events(self, entity_id: str) -> list[AuditEvent]: ...

    @abstractmethod
    async def weights(self, transaction_id: str) -> list[WeightRecord]: ...

    @abstractmethod
    async def payments(self, transaction_id: str) -> list[Payment]: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self) -> None:
        self._transactions: dict[str, Transaction] = {}
        self._events: list[TransactionEvent] = []
        self._audit: list[AuditEvent] = []
        self._weights: dict[str, WeightRecord] = {}
        self._handovers: dict[str, HandoverRecord] = {}
        self._payments: dict[str, Payment] = {}
        self._disputes: dict[str, Dispute] = {}
        self._idempotency: dict[str, str] = {}
        self._next_id = 1

    def _new_id(self) -> str:
        value = str(self._next_id)
        self._next_id += 1
        return value

    async def create_transaction(self, transaction: Transaction) -> tuple[str, bool]:
        if transaction.idempotency_key and transaction.idempotency_key in self._idempotency:
            return self._idempotency[transaction.idempotency_key], False
        if not transaction.id:
            transaction.id = self._new_id()
        transaction.created_at = _now()
        self._transactions[transaction.id] = transaction
        if transaction.idempotency_key:
            self._idempotency[transaction.idempotency_key] = transaction.id
        return transaction.id, True

    async def get_transaction(self, transaction_id: str, collector_id: str) -> Transaction | None:
        txn = self._transactions.get(transaction_id)
        if txn is None or txn.collector_id != collector_id:
            return None
        return txn

    async def apply_transition(
        self, transaction_id: str, from_status: str, to_status: str, actor_user_id: str | None
    ) -> None:
        txn = self._transactions[transaction_id]
        txn.status = to_status
        self._events.append(
            TransactionEvent(
                id=self._new_id(),
                transaction_id=transaction_id,
                event_type="STATUS_CHANGED",
                from_status=from_status,
                to_status=to_status,
                actor_user_id=actor_user_id,
                created_at=_now(),
            )
        )
        self._audit.append(
            AuditEvent(
                id=self._new_id(),
                action="transaction.status_changed",
                actor_user_id=actor_user_id,
                entity_type="transaction",
                entity_id=transaction_id,
                before={"status": from_status},
                after={"status": to_status},
                created_at=_now(),
            )
        )

    async def add_audit_event(self, event: AuditEvent) -> None:
        if not event.id:
            event.id = self._new_id()
        event.created_at = event.created_at or _now()
        self._audit.append(event)

    async def add_weight(self, weight: WeightRecord) -> str:
        weight.id = weight.id or self._new_id()
        self._weights[weight.id] = weight
        return weight.id

    async def set_final_weight(self, transaction_id: str, weight_kg: float) -> None:
        txn = self._transactions[transaction_id]
        txn.final_weight_kg = weight_kg

    async def add_handover(self, handover: HandoverRecord) -> tuple[str, bool]:
        if handover.idempotency_key and handover.idempotency_key in self._idempotency:
            return self._idempotency[handover.idempotency_key], False
        handover.id = handover.id or self._new_id()
        self._handovers[handover.id] = handover
        if handover.idempotency_key:
            self._idempotency[handover.idempotency_key] = handover.id
        return handover.id, True

    async def add_payment(self, payment: Payment) -> tuple[str, bool]:
        if payment.idempotency_key and payment.idempotency_key in self._idempotency:
            return self._idempotency[payment.idempotency_key], False
        payment.id = payment.id or self._new_id()
        self._payments[payment.id] = payment
        if payment.idempotency_key:
            self._idempotency[payment.idempotency_key] = payment.id
        return payment.id, True

    async def confirm_payment(self, payment_id: str, actor_user_id: str | None) -> None:
        payment = self._payments[payment_id]
        payment.status = "confirmed"

    async def add_dispute(self, dispute: Dispute) -> str:
        dispute.id = dispute.id or self._new_id()
        self._disputes[dispute.id] = dispute
        return dispute.id

    async def completed_transactions(self, collector_id: str) -> list[Transaction]:
        return [
            t
            for t in self._transactions.values()
            if t.collector_id == collector_id and t.status == "COMPLETED"
        ]

    async def events(self, transaction_id: str) -> list[TransactionEvent]:
        return [e for e in self._events if e.transaction_id == transaction_id]

    async def audit_events(self, entity_id: str) -> list[AuditEvent]:
        return [a for a in self._audit if a.entity_id == entity_id]

    async def weights(self, transaction_id: str) -> list[WeightRecord]:
        return [w for w in self._weights.values() if w.transaction_id == transaction_id]

    async def payments(self, transaction_id: str) -> list[Payment]:
        return [p for p in self._payments.values() if p.transaction_id == transaction_id]


class PostgresTransactionRepository(TransactionRepository):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_transaction(self, transaction: Transaction) -> tuple[str, bool]:
        async with self._pool.connection() as conn:
            if transaction.idempotency_key:
                cur = await conn.execute(
                    "SELECT id::text FROM transactions WHERE idempotency_key = %s",
                    (transaction.idempotency_key,),
                )
                row = await cur.fetchone()
                if row is not None:
                    return row[0], False
            cur = await conn.execute(
                "INSERT INTO transactions (idempotency_key, lot_id, collector_id, "
                "recycler_organization_id, match_id, status, agreed_price_per_kg, transport_cost) "
                "VALUES (%s, %s::uuid, %s::uuid, %s::uuid, %s::uuid, 'LOT_CREATED', %s, %s) "
                "RETURNING id::text",
                (
                    transaction.idempotency_key,
                    transaction.lot_id,
                    transaction.collector_id,
                    transaction.recycler_organization_id,
                    transaction.match_id,
                    transaction.agreed_price_per_kg,
                    transaction.transport_cost,
                ),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to create transaction")
            return row[0], True

    async def get_transaction(self, transaction_id: str, collector_id: str) -> Transaction | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, lot_id::text, collector_id::text, "
                "recycler_organization_id::text, match_id::text, status, currency, "
                "agreed_price_per_kg, final_weight_kg, transport_cost, net_earnings, "
                "idempotency_key, created_at "
                "FROM transactions WHERE id = %s::uuid AND collector_id = %s::uuid",
                (transaction_id, collector_id),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return Transaction(
                id=row[0],
                lot_id=row[1],
                collector_id=row[2],
                recycler_organization_id=row[3],
                match_id=row[4],
                status=row[5],
                currency=row[6],
                agreed_price_per_kg=float(row[7]) if row[7] is not None else None,
                final_weight_kg=float(row[8]) if row[8] is not None else None,
                transport_cost=float(row[9]) if row[9] is not None else None,
                net_earnings=float(row[10]) if row[10] is not None else None,
                idempotency_key=row[11],
                created_at=row[12].isoformat() if row[12] else None,
            )

    async def apply_transition(
        self, transaction_id: str, from_status: str, to_status: str, actor_user_id: str | None
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE transactions SET status = %s WHERE id = %s::uuid",
                    (to_status, transaction_id),
                )
                await conn.execute(
                    "INSERT INTO transaction_events "
                    "(transaction_id, event_type, from_status, to_status, actor_user_id) "
                    "VALUES (%s::uuid, 'STATUS_CHANGED', %s, %s, %s::uuid)",
                    (transaction_id, from_status, to_status, actor_user_id),
                )
                await conn.execute(
                    "INSERT INTO audit_events "
                    "(actor_user_id, action, entity_type, entity_id, before, after) "
                    "VALUES (%s::uuid, 'transaction.status_changed', 'transaction', "
                    "%s::uuid, %s, %s)",
                    (
                        actor_user_id,
                        transaction_id,
                        {"status": from_status},
                        {"status": to_status},
                    ),
                )

    async def add_audit_event(self, event: AuditEvent) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO audit_events "
                "(actor_user_id, action, entity_type, entity_id, before, after) "
                "VALUES (%s::uuid, %s, %s, %s::uuid, %s, %s)",
                (
                    event.actor_user_id,
                    event.action,
                    event.entity_type,
                    event.entity_id,
                    event.before,
                    event.after,
                ),
            )

    async def add_weight(self, weight: WeightRecord) -> str:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO weights (transaction_id, weight_type, weight_kg, source) "
                "VALUES (%s::uuid, %s, %s, %s) RETURNING id::text",
                (weight.transaction_id, weight.weight_type, weight.weight_kg, weight.source),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to record weight")
            return row[0]

    async def set_final_weight(self, transaction_id: str, weight_kg: float) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE transactions SET final_weight_kg = %s WHERE id = %s::uuid",
                (weight_kg, transaction_id),
            )

    async def add_handover(self, handover: HandoverRecord) -> tuple[str, bool]:
        async with self._pool.connection() as conn:
            if handover.idempotency_key:
                cur = await conn.execute(
                    "SELECT id::text FROM handover_records WHERE idempotency_key = %s",
                    (handover.idempotency_key,),
                )
                row = await cur.fetchone()
                if row is not None:
                    return row[0], False
            cur = await conn.execute(
                "INSERT INTO handover_records (transaction_id, handed_over_by_user_id, "
                "received_by_user_id, notes, idempotency_key) "
                "VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s) RETURNING id::text",
                (
                    handover.transaction_id,
                    handover.handed_over_by_user_id,
                    handover.received_by_user_id,
                    handover.notes,
                    handover.idempotency_key,
                ),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to record handover")
            return row[0], True

    async def add_payment(self, payment: Payment) -> tuple[str, bool]:
        async with self._pool.connection() as conn:
            if payment.idempotency_key:
                cur = await conn.execute(
                    "SELECT id::text FROM payments WHERE idempotency_key = %s",
                    (payment.idempotency_key,),
                )
                row = await cur.fetchone()
                if row is not None:
                    return row[0], False
            cur = await conn.execute(
                "INSERT INTO payments (transaction_id, amount, currency, method, status, "
                "payee_user_id, reference, idempotency_key) "
                "VALUES (%s::uuid, %s, 'INR', %s, 'recorded', %s::uuid, %s, %s) RETURNING id::text",
                (
                    payment.transaction_id,
                    payment.amount,
                    payment.method,
                    payment.payee_user_id,
                    payment.reference,
                    payment.idempotency_key,
                ),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to record payment")
            return row[0], True

    async def confirm_payment(self, payment_id: str, actor_user_id: str | None) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO payment_confirmations "
                "(payment_id, confirmed_by_user_id, confirmation_source) "
                "VALUES (%s::uuid, %s::uuid, 'app')",
                (payment_id, actor_user_id),
            )
            await conn.execute(
                "UPDATE payments SET status = 'confirmed' WHERE id = %s::uuid", (payment_id,)
            )

    async def add_dispute(self, dispute: Dispute) -> str:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO disputes (transaction_id, raised_by_user_id, reason) "
                "VALUES (%s::uuid, %s::uuid, %s) RETURNING id::text",
                (dispute.transaction_id, dispute.raised_by_user_id, dispute.reason),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to raise dispute")
            return row[0]

    async def completed_transactions(self, collector_id: str) -> list[Transaction]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, lot_id::text, collector_id::text, "
                "recycler_organization_id::text, match_id::text, status, currency, "
                "agreed_price_per_kg, final_weight_kg, transport_cost, net_earnings, "
                "idempotency_key, created_at "
                "FROM transactions WHERE collector_id = %s::uuid AND status = 'COMPLETED'",
                (collector_id,),
            )
            return [
                Transaction(
                    id=r[0],
                    lot_id=r[1],
                    collector_id=r[2],
                    recycler_organization_id=r[3],
                    match_id=r[4],
                    status=r[5],
                    currency=r[6],
                    agreed_price_per_kg=float(r[7]) if r[7] is not None else None,
                    final_weight_kg=float(r[8]) if r[8] is not None else None,
                    transport_cost=float(r[9]) if r[9] is not None else None,
                    net_earnings=float(r[10]) if r[10] is not None else None,
                    idempotency_key=r[11],
                    created_at=r[12].isoformat() if r[12] else None,
                )
                for r in await cur.fetchall()
            ]

    async def events(self, transaction_id: str) -> list[TransactionEvent]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, event_type, from_status, to_status, actor_user_id::text, "
                "created_at FROM transaction_events "
                "WHERE transaction_id = %s::uuid ORDER BY created_at",
                (transaction_id,),
            )
            return [
                TransactionEvent(
                    id=r[0],
                    transaction_id=transaction_id,
                    event_type=r[1],
                    from_status=r[2],
                    to_status=r[3],
                    actor_user_id=r[4],
                    created_at=r[5].isoformat() if r[5] else None,
                )
                for r in await cur.fetchall()
            ]

    async def audit_events(self, entity_id: str) -> list[AuditEvent]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, action, actor_user_id::text, entity_type, entity_id::text, "
                "before, after, created_at FROM audit_events "
                "WHERE entity_id = %s::uuid ORDER BY created_at",
                (entity_id,),
            )
            return [
                AuditEvent(
                    id=r[0],
                    action=r[1],
                    actor_user_id=r[2],
                    entity_type=r[3],
                    entity_id=r[4],
                    before=r[5],
                    after=r[6],
                    created_at=r[7].isoformat() if r[7] else None,
                )
                for r in await cur.fetchall()
            ]

    async def weights(self, transaction_id: str) -> list[WeightRecord]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, weight_type, weight_kg, source FROM weights "
                "WHERE transaction_id = %s::uuid ORDER BY created_at",
                (transaction_id,),
            )
            return [
                WeightRecord(
                    id=r[0],
                    transaction_id=transaction_id,
                    weight_type=r[1],
                    weight_kg=float(r[2]),
                    source=r[3],
                )
                for r in await cur.fetchall()
            ]

    async def payments(self, transaction_id: str) -> list[Payment]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, amount, currency, method, status, reference, "
                "payee_user_id::text, idempotency_key FROM payments "
                "WHERE transaction_id = %s::uuid ORDER BY recorded_at",
                (transaction_id,),
            )
            return [
                Payment(
                    id=r[0],
                    transaction_id=transaction_id,
                    amount=float(r[1]),
                    currency=r[2],
                    method=r[3],
                    status=r[4],
                    reference=r[5],
                    payee_user_id=r[6],
                    idempotency_key=r[7],
                )
                for r in await cur.fetchall()
            ]
