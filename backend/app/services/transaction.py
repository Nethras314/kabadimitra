"""Transaction lifecycle and traceability business logic.

Implements the state machine and writes an audit event for every critical state
transition. Creation, handover, and payment are idempotent.
"""

from ..core.errors import ConflictError, NotFoundError
from ..models.audit import AuditEvent
from ..models.transaction import (
    Dispute,
    EarningsEntry,
    EarningsLedger,
    HandoverRecord,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Transaction,
    TransactionStatus,
    WeightRecord,
    is_valid_transition,
)
from ..repositories.transaction import TransactionRepository


class TransactionService:
    def __init__(self, repository: TransactionRepository) -> None:
        self._repo = repository

    async def create(
        self,
        collector_id: str,
        lot_id: str,
        *,
        idempotency_key: str | None = None,
        recycler_organization_id: str | None = None,
        match_id: str | None = None,
        agreed_price_per_kg: float | None = None,
        transport_cost: float | None = None,
    ) -> Transaction:
        transaction = Transaction(
            lot_id=lot_id,
            collector_id=collector_id,
            recycler_organization_id=recycler_organization_id,
            match_id=match_id,
            agreed_price_per_kg=agreed_price_per_kg,
            transport_cost=transport_cost,
            idempotency_key=idempotency_key,
            status=TransactionStatus.LOT_CREATED.value,
        )
        transaction_id, created = await self._repo.create_transaction(transaction)
        if created:
            await self._repo.add_audit_event(
                AuditEvent(
                    action="transaction.created",
                    actor_user_id=collector_id,
                    entity_type="transaction",
                    entity_id=transaction_id,
                    after={"status": TransactionStatus.LOT_CREATED.value},
                )
            )
        txn = await self._repo.get_transaction(transaction_id, collector_id)
        if txn is None:
            raise RuntimeError("transaction was not created")
        return txn

    async def transition(
        self,
        collector_id: str,
        transaction_id: str,
        to_status: str,
        actor_user_id: str | None = None,
    ) -> Transaction:
        return await self._transition(collector_id, transaction_id, to_status, actor_user_id)

    async def accept_quote(
        self, collector_id: str, transaction_id: str, actor_user_id: str | None = None
    ) -> Transaction:
        return await self._transition(
            collector_id, transaction_id, TransactionStatus.QUOTE_ACCEPTED.value, actor_user_id
        )

    async def record_weight(
        self,
        collector_id: str,
        transaction_id: str,
        weight_type: str,
        weight_kg: float,
        source: str = "collector",
    ) -> WeightRecord:
        await self._get_owned(collector_id, transaction_id)
        if weight_kg <= 0:
            raise ValueError("weight_kg must be positive")
        weight = WeightRecord(
            transaction_id=transaction_id,
            weight_type=weight_type,
            weight_kg=weight_kg,
            source=source,
        )
        weight.id = await self._repo.add_weight(weight)
        if weight_type == "final":
            await self._repo.set_final_weight(transaction_id, weight_kg)
        return weight

    async def record_handover(
        self,
        collector_id: str,
        transaction_id: str,
        idempotency_key: str,
        *,
        handed_over_by_user_id: str | None = None,
        received_by_user_id: str | None = None,
        notes: str | None = None,
    ) -> dict:
        await self._get_owned(collector_id, transaction_id)
        handover = HandoverRecord(
            transaction_id=transaction_id,
            handed_over_by_user_id=handed_over_by_user_id,
            received_by_user_id=received_by_user_id,
            notes=notes,
            idempotency_key=idempotency_key,
        )
        handover_id, created = await self._repo.add_handover(handover)
        if created:
            await self._transition(
                collector_id, transaction_id, TransactionStatus.HANDOVER_CONFIRMED.value, None
            )
            await self._repo.add_audit_event(
                AuditEvent(
                    action="handover.recorded",
                    actor_user_id=collector_id,
                    entity_type="handover",
                    entity_id=handover_id,
                )
            )
        return {"id": handover_id, "created": created}

    async def record_payment(
        self,
        collector_id: str,
        transaction_id: str,
        method: str,
        amount: float,
        idempotency_key: str,
        *,
        reference: str | None = None,
    ) -> Payment:
        if method not in {m.value for m in PaymentMethod}:
            raise ValueError(f"Unsupported payment method: {method}")
        if amount <= 0:
            raise ValueError("amount must be positive")
        await self._get_owned(collector_id, transaction_id)

        payment = Payment(
            transaction_id=transaction_id,
            amount=amount,
            method=method,
            reference=reference,
            payee_user_id=collector_id,
            idempotency_key=idempotency_key,
        )
        payment_id, created = await self._repo.add_payment(payment)
        payment.id = payment_id
        if created:
            await self._transition(
                collector_id, transaction_id, TransactionStatus.PAYMENT_RECORDED.value, None
            )
            await self._repo.add_audit_event(
                AuditEvent(
                    action="payment.recorded",
                    actor_user_id=collector_id,
                    entity_type="payment",
                    entity_id=payment_id,
                    after={"method": method, "amount": amount},
                )
            )
        return payment

    async def confirm_payment(
        self, collector_id: str, payment_id: str, actor_user_id: str | None = None
    ) -> dict:
        await self._repo.confirm_payment(payment_id, actor_user_id)
        await self._repo.add_audit_event(
            AuditEvent(
                action="payment.confirmed",
                actor_user_id=actor_user_id or collector_id,
                entity_type="payment",
                entity_id=payment_id,
            )
        )
        return {"status": PaymentStatus.CONFIRMED.value}

    async def initiate_dispute(
        self, collector_id: str, transaction_id: str, reason: str
    ) -> Dispute:
        await self._get_owned(collector_id, transaction_id)
        dispute = Dispute(
            transaction_id=transaction_id,
            reason=reason,
            raised_by_user_id=collector_id,
        )
        dispute.id = await self._repo.add_dispute(dispute)
        await self._repo.add_audit_event(
            AuditEvent(
                action="dispute.raised",
                actor_user_id=collector_id,
                entity_type="dispute",
                entity_id=dispute.id,
                after={"reason": reason},
            )
        )
        return dispute

    async def earnings(self, collector_id: str) -> EarningsLedger:
        completed = await self._repo.completed_transactions(collector_id)
        entries = [
            EarningsEntry(
                transaction_id=txn.id,
                net_earnings=self._net_earnings(txn),
                currency=txn.currency,
                completed_at=txn.created_at,
            )
            for txn in completed
        ]
        total = round(sum(e.net_earnings for e in entries), 2)
        return EarningsLedger(entries=entries, total=total)

    async def _transition(
        self, collector_id: str, transaction_id: str, to_status: str, actor_user_id: str | None
    ) -> Transaction:
        txn = await self._get_owned(collector_id, transaction_id)
        if not is_valid_transition(txn.status, to_status):
            raise ConflictError(f"Cannot transition from {txn.status} to {to_status}")
        await self._repo.apply_transition(transaction_id, txn.status, to_status, actor_user_id)
        updated = await self._repo.get_transaction(transaction_id, collector_id)
        if updated is None:
            raise RuntimeError("transaction disappeared during transition")
        return updated

    async def _get_owned(self, collector_id: str, transaction_id: str) -> Transaction:
        txn = await self._repo.get_transaction(transaction_id, collector_id)
        if txn is None:
            raise NotFoundError("Transaction not found")
        return txn

    @staticmethod
    def _net_earnings(txn: Transaction) -> float:
        weight = txn.final_weight_kg or 0.0
        price = txn.agreed_price_per_kg or 0.0
        transport = txn.transport_cost or 0.0
        return round(weight * price - transport, 2)
