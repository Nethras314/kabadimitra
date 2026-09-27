"""Pydantic models (Phase 2–4 surface)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    service: str


class MeOut(BaseModel):
    user_id: str | None
    sub: str
    roles: list[str]
    organization_id: str | None
    preferred_locale: str


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None


class CollectorCategoryOut(BaseModel):
    id: str
    code: str
    name: str
    sort_order: int


# --- Lots / items / images ---


class LotCreate(BaseModel):
    title: str | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pickup_address: str | None = None


class LotOut(BaseModel):
    id: str
    collector_id: str
    status: str
    title: str | None
    notes: str | None
    pickup_address: str | None
    created_at: datetime


class LotItemCreate(BaseModel):
    collector_category_id: str | None = None
    material_category_id: str | None = None
    material_subcategory_id: str | None = None
    kind: str | None = None
    description: str | None = None
    quantity: int = 1
    declared_weight_kg: float | None = None
    condition_id: str | None = None
    classification_source: str = "collector"


class LotItemOut(BaseModel):
    id: str
    lot_id: str
    collector_category_id: str | None
    material_category_id: str | None
    material_subcategory_id: str | None
    kind: str | None
    description: str | None
    quantity: int
    declared_weight_kg: float | None
    condition_id: str | None
    classification_source: str
    created_at: datetime


class MaterialImageCreate(BaseModel):
    cloudinary_public_id: str
    cloudinary_url: str
    image_kind: str = "capture"
    is_primary: bool = False
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None


class MaterialImageOut(BaseModel):
    id: str
    lot_item_id: str | None
    lot_id: str | None
    cloudinary_public_id: str
    cloudinary_url: str
    image_kind: str
    is_primary: bool
    created_at: datetime


# --- AI classification ---


class ClassifyRequest(BaseModel):
    image_id: str | None = None


class ClassifyOut(BaseModel):
    decision_id: str
    provider: str
    confidence: float
    predicted_category_id: str | None
    predicted_subcategory_id: str | None
    suggested_action: str  # "confirm" | "manual"
    detected_material_types: list[str] | None
    quality_flags: dict


class CorrectRequest(BaseModel):
    corrected_category_id: str | None = None
    corrected_subcategory_id: str | None = None
    correction_type: str = "category"
    note: str | None = None


# --- Pricing ---


class PriceObservationCreate(BaseModel):
    material_category_id: str
    material_subcategory_id: str | None = None
    grade_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    observed_price_per_kg: float
    currency: str = "INR"
    buyer_type: Literal["recycler", "aggregator", "other"] | None = None
    buyer_organization_id: str | None = None
    source: Literal["collector_entry", "recycler_quote", "market", "verification"] = "collector_entry"
    weight_kg: float | None = None
    transport_cost: float | None = None
    observed_at: datetime | None = None
    notes: str | None = None


class PriceObservationOut(BaseModel):
    id: str
    material_category_id: str
    material_subcategory_id: str | None
    grade_id: str | None
    city: str | None
    state: str | None
    observed_price_per_kg: float
    currency: str
    buyer_type: str | None
    source: str
    verification_status: str
    weight_kg: float | None
    transport_cost: float | None
    observed_at: datetime


class PricingSummary(BaseModel):
    sample_count: int
    verified_count: int
    average_price_per_kg: float | None
    min_price_per_kg: float | None
    max_price_per_kg: float | None
    verified_average_price_per_kg: float | None


class PricingEstimateOut(BaseModel):
    material_category_id: str
    currency: str
    summary: PricingSummary
    observations: list[PriceObservationOut]


# --- Recycler verification ---


class RecyclerOrganizationCreate(BaseModel):
    name: str
    gstin: str | None = None
    registration_number: str | None = None
    facility_name: str | None = None
    facility_latitude: float | None = None
    facility_longitude: float | None = None
    authorization_number: str | None = None
    issuing_authority: str | None = None
    authorization_type: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    verification_source: str | None = None
    status: Literal["verified", "pending", "expiring", "expired", "suspended"] = "pending"


class RecyclerOrganizationOut(BaseModel):
    id: str
    organization_id: str
    name: str
    gstin: str | None
    registration_number: str | None
    status: str
    verified: bool
    authorization: dict | None = None


# --- Matching & transactions ---


class MatchOut(BaseModel):
    id: str
    lot_id: str
    recycler_organization_id: str
    recycler_name: str
    score: float | None
    distance_km: float | None
    status: str


class TransactionCreate(BaseModel):
    match_id: str | None = None
    recycler_organization_id: str | None = None


class TransactionEventOut(BaseModel):
    id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    created_at: datetime


class TransactionOut(BaseModel):
    id: str
    lot_id: str
    collector_id: str
    recycler_organization_id: str | None
    match_id: str | None
    status: str
    currency: str
    final_weight_kg: float | None
    net_earnings: float | None
    created_at: datetime


class TransitionRequest(BaseModel):
    to_status: Literal[
        "LOT_CREATED",
        "CLASSIFIED",
        "QUOTED",
        "QUOTE_ACCEPTED",
        "PICKUP_OR_DELIVERY",
        "WEIGHT_VERIFIED",
        "HANDOVER_CONFIRMED",
        "PAYMENT_RECORDED",
        "COMPLETED",
    ]


class WeightCreate(BaseModel):
    weight_type: Literal["declared", "pickup", "final"]
    weight_kg: float
    source: Literal["collector", "recycler", "scale"] = "collector"


class WeightOut(BaseModel):
    id: str
    transaction_id: str
    weight_type: str
    weight_kg: float
    source: str
    measured_at: datetime


class PaymentCreate(BaseModel):
    method: Literal["cash", "upi", "bank_transfer"]
    amount: float
    reference: str | None = None


class PaymentOut(BaseModel):
    id: str
    transaction_id: str
    amount: float
    currency: str
    method: str
    status: str
    reference: str | None
    recorded_at: datetime


class MaterialAcceptanceCreate(BaseModel):
    material_category_id: str
    is_accepted: bool = True


# --- Offline sync ---


class LotSyncPayload(BaseModel):
    title: str | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pickup_address: str | None = None


class LotItemSyncPayload(BaseModel):
    lot_id: str
    collector_category_id: str | None = None
    material_category_id: str | None = None
    material_subcategory_id: str | None = None
    kind: str | None = None
    description: str | None = None
    quantity: int = 1
    declared_weight_kg: float | None = None
    condition_id: str | None = None
    classification_source: str = "collector"


class WeightSyncPayload(BaseModel):
    transaction_id: str
    weight_type: Literal["declared", "pickup", "final"]
    weight_kg: float
    source: Literal["collector", "recycler", "scale"] = "collector"


class PaymentSyncPayload(BaseModel):
    transaction_id: str
    method: Literal["cash", "upi", "bank_transfer"]
    amount: float
    reference: str | None = None


class TransactionSyncPayload(BaseModel):
    lot_id: str
    match_id: str | None = None
    recycler_organization_id: str | None = None


class SyncOperation(BaseModel):
    idempotency_key: str
    entity_type: Literal["lot", "lot_item", "weight", "payment", "transaction"]
    id: str
    payload: dict


class SyncRequest(BaseModel):
    operations: list[SyncOperation]


class SyncResult(BaseModel):
    idempotency_key: str
    entity_id: str | None = None
    status: str
    error: str | None = None


class SyncResponse(BaseModel):
    results: list[SyncResult]


class NearbyRecyclerOut(BaseModel):
    id: str
    name: str
    distance_km: float
    latitude: float | None = None
    longitude: float | None = None
