"""Indicative valuation (assistive, never guaranteed).

Combines material classification, weight, location, price observations, recycler
quotes, and transport cost into an **INDICATIVE VALUE** — a transparent estimate,
not a guaranteed price.
"""

from dataclasses import dataclass, field
from statistics import median


@dataclass
class PricePoint:
    price_per_kg: float
    source: str
    verified: bool = False


@dataclass
class ValuationRequest:
    material_category_id: str
    weight_kg: float
    location: str | None = None
    observations: list[PricePoint] = field(default_factory=list)
    quotes: list[PricePoint] = field(default_factory=list)
    transport_cost: float = 0.0


@dataclass
class IndicativeValuation:
    label: str
    estimated_value: float | None
    value_range: tuple[float, float] | None
    currency: str
    basis: dict
    disclaimer: str


class ValuationService:
    """Produce an indicative value from available price signals."""

    def estimate(self, request: ValuationRequest) -> IndicativeValuation:
        points = request.observations + request.quotes
        if not points:
            return IndicativeValuation(
                label="INDICATIVE VALUE",
                estimated_value=None,
                value_range=None,
                currency="INR",
                basis={"reason": "insufficient price data", "location": request.location},
                disclaimer=self._disclaimer(),
            )

        prices = [p.price_per_kg for p in points]
        price_per_kg = median(prices)
        low = min(prices)
        high = max(prices)

        def net(price: float) -> float:
            return round(request.weight_kg * price - request.transport_cost, 2)

        return IndicativeValuation(
            label="INDICATIVE VALUE",
            estimated_value=net(price_per_kg),
            value_range=(net(low), net(high)),
            currency="INR",
            basis={
                "weight_kg": request.weight_kg,
                "location": request.location,
                "price_per_kg": round(price_per_kg, 2),
                "transport_cost": request.transport_cost,
                "sample_count": len(points),
                "verified_count": sum(1 for p in points if p.verified),
            },
            disclaimer=self._disclaimer(),
        )

    @staticmethod
    def _disclaimer() -> str:
        return (
            "Indicative estimate only — not a guaranteed price. Combines material "
            "classification, weight, location, price observations, recycler quotes, "
            "and transport cost."
        )
