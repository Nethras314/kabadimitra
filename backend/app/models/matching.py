"""Recycler matching domain types."""

from dataclasses import dataclass, field


@dataclass
class RecyclerCandidate:
    recycler_id: str
    name: str
    authorized: bool
    accepted_materials: set[str] = field(default_factory=set)
    service_radius_km: float | None = None
    distance_km: float | None = None
    pickup_available: bool = False
    transport_cost: float | None = None
    quote_price_per_kg: float | None = None
    reliability: float = 0.0  # 0..1


@dataclass
class Lot:
    lot_id: str
    material_category_ids: list[str]
    weight_kg: float | None = None


@dataclass
class MatchResult:
    recycler_id: str
    name: str
    score: float
    reason: dict


@dataclass
class MatchConfig:
    material_weight: float = 30.0
    proximity_weight: float = 25.0
    pickup_weight: float = 10.0
    transport_weight: float = 15.0
    quote_weight: float = 10.0
    reliability_weight: float = 10.0
    proximity_km_reference: float = 50.0
    transport_cost_reference: float = 2000.0
