"""Pricing domain types."""

from dataclasses import dataclass
from enum import StrEnum


class PriceKind(StrEnum):
    MARKET_OBSERVATION = "market_observation"
    RECYCLER_QUOTE = "recycler_quote"
    EXISTING_BUYER_PRICE = "existing_buyer_price"
    INDICATIVE_VALUE = "indicative_value"


def kind_for_source(source: str) -> PriceKind:
    if source == "recycler_quote":
        return PriceKind.RECYCLER_QUOTE
    if source in ("market", "verification"):
        return PriceKind.MARKET_OBSERVATION
    return PriceKind.EXISTING_BUYER_PRICE


@dataclass
class PriceObservation:
    material_category_id: str
    price_per_kg: float
    material_subcategory_id: str | None = None
    grade_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    unit: str = "per_kg"
    currency: str = "INR"
    buyer_type: str | None = None
    buyer_organization_id: str | None = None
    source: str = "collector_entry"
    verification_status: str = "unverified"
    confidence: float = 1.0
    observed_at: str | None = None
    weight_kg: float | None = None
    transport_cost: float | None = None
    id: str = ""


@dataclass
class HistoricalPrice:
    kind: str
    material_category_id: str
    average_price_per_kg: float | None
    min_price_per_kg: float | None
    max_price_per_kg: float | None
    sample_count: int
    verified_count: int


@dataclass
class PriceComparison:
    kind: str
    price_per_kg: float
    currency: str
    buyer_type: str | None = None
    buyer_organization_id: str | None = None
    verified: bool = False
    observed_at: str | None = None
    distance_km: float | None = None
