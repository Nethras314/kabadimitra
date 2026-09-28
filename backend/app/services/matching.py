"""Recycler matching business logic.

Matching ranks recyclers on a composite score — authorization (gate), material
acceptance (gate), service area (gate), distance, pickup, transport cost, quoted
price, and historical reliability. It never ranks by gross price alone
(FR-MATCH-01/FR-MATCH-02).
"""

from ..models.matching import Lot, MatchConfig, MatchResult, RecyclerCandidate


class MatchingService:
    def __init__(self, config: MatchConfig | None = None) -> None:
        self._config = config or MatchConfig()

    def match(self, lot: Lot, candidates: list[RecyclerCandidate]) -> list[MatchResult]:
        eligible = [c for c in candidates if self._eligible(lot, c)]
        if not eligible:
            return []

        max_quote = max(
            (c.quote_price_per_kg for c in eligible if c.quote_price_per_kg is not None),
            default=None,
        )
        results = [self._score(lot, c, max_quote) for c in eligible]
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _eligible(self, lot: Lot, candidate: RecyclerCandidate) -> bool:
        if not candidate.authorized:
            return False
        if candidate.accepted_materials and not (
            candidate.accepted_materials & set(lot.material_category_ids)
        ):
            return False
        if candidate.service_radius_km is not None and candidate.distance_km is not None:
            if candidate.distance_km > candidate.service_radius_km:
                return False
        return True

    def _score(
        self, lot: Lot, candidate: RecyclerCandidate, max_quote: float | None
    ) -> MatchResult:
        cfg = self._config
        material_coverage = self._material_coverage(lot, candidate)
        proximity = self._proximity(candidate.distance_km)
        pickup = 1.0 if candidate.pickup_available else 0.0
        transport = self._transport(candidate.transport_cost)
        quote = self._quote(candidate.quote_price_per_kg, max_quote)
        reliability = min(1.0, max(0.0, candidate.reliability))

        score = (
            cfg.material_weight * material_coverage
            + cfg.proximity_weight * proximity
            + cfg.pickup_weight * pickup
            + cfg.transport_weight * transport
            + cfg.quote_weight * quote
            + cfg.reliability_weight * reliability
        )

        reason = {
            "material_coverage": round(material_coverage, 3),
            "proximity_score": round(proximity, 3),
            "pickup_available": candidate.pickup_available,
            "transport_cost": candidate.transport_cost,
            "quoted_price_per_kg": candidate.quote_price_per_kg,
            "reliability": round(reliability, 3),
            "distance_km": candidate.distance_km,
            "expected_net_earnings": self._expected_net_earnings(lot, candidate),
        }
        return MatchResult(
            recycler_id=candidate.recycler_id,
            name=candidate.name,
            score=round(score, 2),
            reason=reason,
        )

    def _material_coverage(self, lot: Lot, candidate: RecyclerCandidate) -> float:
        if not lot.material_category_ids:
            return 0.0
        if not candidate.accepted_materials:
            return 1.0  # no explicit restrictions -> accepts everything
        overlap = candidate.accepted_materials & set(lot.material_category_ids)
        return len(overlap) / len(lot.material_category_ids)

    def _proximity(self, distance_km: float | None) -> float:
        if distance_km is None:
            return 0.5
        return max(0.0, 1.0 - distance_km / self._config.proximity_km_reference)

    def _transport(self, transport_cost: float | None) -> float:
        if transport_cost is None or transport_cost <= 0:
            return 1.0
        return max(0.0, 1.0 - transport_cost / self._config.transport_cost_reference)

    def _quote(self, quote_price: float | None, max_quote: float | None) -> float:
        if quote_price is None or max_quote is None or max_quote <= 0:
            return 0.0
        return quote_price / max_quote

    def _expected_net_earnings(self, lot: Lot, candidate: RecyclerCandidate) -> float | None:
        if lot.weight_kg is None or candidate.quote_price_per_kg is None:
            return None
        gross = lot.weight_kg * candidate.quote_price_per_kg
        transport = candidate.transport_cost or 0.0
        return round(gross - transport, 2)
