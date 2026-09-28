import asyncio

import pytest

from app.core.errors import ConflictError
from app.models.transaction import PaymentMethod
from app.repositories.transaction import InMemoryTransactionRepository
from app.services.transaction import TransactionService


def run(coro):
    return asyncio.run(coro)


def make():
    repo = InMemoryTransactionRepository()
    return repo, TransactionService(repo)


async def _advance_to_weight_verified(svc, collector, txn_id):
    for state in ["CLASSIFIED", "QUOTED", "QUOTE_ACCEPTED", "PICKUP_OR_DELIVERY", "WEIGHT_VERIFIED"]:
        await svc.transition(collector, txn_id, state)


def test_payment_methods_include_cash():
    methods = {m.value for m in PaymentMethod}
    assert "cash" in methods
    assert "upi" in methods
    assert "bank_transfer" in methods


def test_end_to_end_lifecycle():
    repo, svc = make()

    async def _run():
        collector, lot = "c-1", "lot-1"
        txn = await svc.create(
            collector, lot, idempotency_key="KC-TXN-1",
            agreed_price_per_kg=200.0, transport_cost=100.0,
        )
        assert txn.status == "LOT_CREATED"

        txn = await svc.transition(collector, txn.id, "CLASSIFIED")
        txn = await svc.transition(collector, txn.id, "QUOTED")
        txn = await svc.accept_quote(collector, txn.id)
        assert txn.status == "QUOTE_ACCEPTED"
        txn = await svc.transition(collector, txn.id, "PICKUP_OR_DELIVERY")

        await svc.record_weight(collector, txn.id, "declared", 9.5)
        await svc.record_weight(collector, txn.id, "pickup", 10.0)
        txn = await svc.transition(collector, txn.id, "WEIGHT_VERIFIED")
        await svc.record_weight(collector, txn.id, "final", 10.0)

        await svc.record_handover(collector, txn.id, "KC-HANDOVER-1")
        await svc.record_payment(collector, txn.id, "cash", 1900.0, "KC-PAY-1")
        txn = await svc.transition(collector, txn.id, "COMPLETED")
        assert txn.status == "COMPLETED"

        ledger = await svc.earnings(collector)
        assert ledger.total == 1900.0  # 10kg * 200 - 100 transport
        assert len(ledger.entries) == 1

        events = await repo.events(txn.id)
        assert len(events) == 8

        audit = await repo.audit_events(txn.id)
        status_changes = [a for a in audit if a.action == "transaction.status_changed"]
        assert len(status_changes) == 8  # every critical transition audited
        assert any(a.action == "transaction.created" for a in audit)

    run(_run())


def test_illegal_transition_raises_conflict():
    repo, svc = make()

    async def _run():
        txn = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        with pytest.raises(ConflictError):
            await svc.transition("c-1", txn.id, "COMPLETED")

    run(_run())


def test_transaction_creation_idempotent():
    repo, svc = make()

    async def _run():
        t1 = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        t2 = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        assert t1.id == t2.id
        audit = await repo.audit_events(t1.id)
        assert sum(1 for a in audit if a.action == "transaction.created") == 1

    run(_run())


def test_handover_idempotent():
    repo, svc = make()

    async def _run():
        txn = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        await _advance_to_weight_verified(svc, "c-1", txn.id)
        r1 = await svc.record_handover("c-1", txn.id, "KC-HO-1")
        r2 = await svc.record_handover("c-1", txn.id, "KC-HO-1")
        assert r1["id"] == r2["id"]
        assert r2["created"] is False

    run(_run())


def test_payment_idempotent():
    repo, svc = make()

    async def _run():
        txn = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        await _advance_to_weight_verified(svc, "c-1", txn.id)
        await svc.record_handover("c-1", txn.id, "KC-HO-1")
        p1 = await svc.record_payment("c-1", txn.id, "cash", 1900.0, "KC-PAY-1")
        p2 = await svc.record_payment("c-1", txn.id, "cash", 1900.0, "KC-PAY-1")
        assert p1.id == p2.id
        payments = await repo.payments(txn.id)
        assert len(payments) == 1

    run(_run())


def test_all_payment_methods_supported():
    repo, svc = make()

    async def _run():
        for method in ["cash", "upi", "bank_transfer"]:
            txn = await svc.create("c-1", "lot-1", idempotency_key=f"KC-TXN-{method}")
            await _advance_to_weight_verified(svc, "c-1", txn.id)
            await svc.record_handover("c-1", txn.id, f"KC-HO-{method}")
            payment = await svc.record_payment("c-1", txn.id, method, 100.0, f"KC-PAY-{method}")
            assert payment.method == method
            assert payment.status == "recorded"

    run(_run())


def test_invalid_payment_method_rejected():
    repo, svc = make()

    async def _run():
        txn = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        await _advance_to_weight_verified(svc, "c-1", txn.id)
        await svc.record_handover("c-1", txn.id, "KC-HO-1")
        with pytest.raises(ValueError):
            await svc.record_payment("c-1", txn.id, "bitcoin", 100.0, "KC-PAY-1")

    run(_run())


def test_weight_types_recorded():
    repo, svc = make()

    async def _run():
        txn = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        await svc.record_weight("c-1", txn.id, "declared", 9.5)
        await svc.record_weight("c-1", txn.id, "pickup", 10.0)
        await svc.record_weight("c-1", txn.id, "final", 10.2)

        weights = await repo.weights(txn.id)
        assert {w.weight_type for w in weights} == {"declared", "pickup", "final"}
        txn = await repo.get_transaction(txn.id, "c-1")
        assert txn.final_weight_kg == 10.2

    run(_run())


def test_dispute_initiation():
    repo, svc = make()

    async def _run():
        txn = await svc.create("c-1", "lot-1", idempotency_key="KC-TXN-1")
        dispute = await svc.initiate_dispute("c-1", txn.id, "weight mismatch")
        assert dispute.status == "open"
        assert dispute.reason == "weight mismatch"
        audit = await repo.audit_events(dispute.id)
        assert any(a.action == "dispute.raised" for a in audit)

    run(_run())
