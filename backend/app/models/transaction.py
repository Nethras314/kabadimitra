"""Transaction lifecycle and traceability domain types."""

from dataclasses import dataclass, field
from enum import StrEnum


class TransactionStatus(StrEnum):
    LOT_CREATED = "LOT_CREATED"
    CLASSIFIED = "CLASSIFIED"
    QUOTED = "QUOTED"
    QUOTE_ACCEPTED = "QUOTE_ACCEPTED"
    PICKUP_OR_DELIVERY = "PICKUP_OR_DELIVERY"
    WEIGHT_VERIFIED = "WEIGHT_VERIFIED"
    HANDOVER_CONFIRMED = "HANDOVER_CONFIRMED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    COMPLETED = "COMPLETED"


TRANSITIONS: dict[TransactionStatus, frozenset[TransactionStatus]] = {
    TransactionStatus.LOT_CREATED: frozenset({TransactionStatus.CLASSIFIED}),
    TransactionStatus.CLASSIFIED: frozenset({TransactionStatus.QUOTED}),
    TransactionStatus.QUOTED: frozenset({TransactionStatus.QUOTE_ACCEPTED}),
    TransactionStatus.QUOTE_ACCEPTED: frozenset({TransactionStatus.PICKUP_OR_DELIVERY}),
    TransactionStatus.PICKUP_OR_DELIVERY: frozenset({TransactionStatus.WEIGHT_VERIFIED}),
    TransactionStatus.WEIGHT_VERIFIED: frozenset({TransactionStatus.HANDOVER_CONFIRMED}),
    TransactionStatus.HANDOVER_CONFIRMED: frozenset({TransactionStatus.PAYMENT_RECORDED}),
    TransactionStatus.PAYMENT_RECORDED: frozenset({TransactionStatus.COMPLETED}),
    TransactionStatus.COMPLETED: frozenset(),
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    allowed = TRANSITIONS.get(TransactionStatus(from_status), frozenset())
    return to_status in {s.value for s in allowed}


def is_terminal(status: str) -> bool:
    return not TRANSITIONS.get(TransactionStatus(status), frozenset())


class WeightType(StrEnum):
    DECLARED = "declared"
    PICKUP = "pickup"
    FINAL = "final"


class PaymentMethod(StrEnum):
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(StrEnum):
    RECORDED = "recorded"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"


class DisputeStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Transaction:
    lot_id: str
    collector_id: str
    id: str = ""
    recycler_organization_id: str | None = None
    match_id: str | None = None
    status: str = TransactionStatus.LOT_CREATED.value
    currency: str = "INR"
    agreed_price_per_kg: float | None = None
    final_weight_kg: float | None = None
    transport_cost: float | None = None
    net_earnings: float | None = None
    idempotency_key: str | None = None
    created_at: str | None = None


@dataclass
class TransactionEvent:
    transaction_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    id: str = ""
    actor_user_id: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: str | None = None


@dataclass
class WeightRecord:
    transaction_id: str
    weight_type: str
    weight_kg: float
    id: str = ""
    source: str = "collector"


@dataclass
class HandoverRecord:
    transaction_id: str
    id: str = ""
    handed_over_by_user_id: str | None = None
    received_by_user_id: str | None = None
    notes: str | None = None
    idempotency_key: str | None = None


@dataclass
class Payment:
    transaction_id: str
    amount: float
    method: str
    id: str = ""
    currency: str = "INR"
    status: str = PaymentStatus.RECORDED.value
    reference: str | None = None
    payee_user_id: str | None = None
    idempotency_key: str | None = None


@dataclass
class Dispute:
    transaction_id: str
    reason: str
    id: str = ""
    raised_by_user_id: str | None = None
    status: str = DisputeStatus.OPEN.value


@dataclass
class EarningsEntry:
    transaction_id: str
    net_earnings: float
    currency: str
    completed_at: str | None = None


@dataclass
class EarningsLedger:
    entries: list[EarningsEntry]
    total: float
