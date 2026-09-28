"""Pricing business logic.

There is no single global material price. Every observation carries material,
subtype, grade, location, timestamp, source, buyer, unit, verification, and
confidence. Estimates are transparent aggregations; with no data the system
returns ``None`` rather than inventing a number (FR-PRICE-01).
"""

from datetime import UTC, datetime, timedelta
from statistics import median

from ..models.pricing import HistoricalPrice, PriceComparison, PriceKind, PriceObservation
from ..repositories.pricing import PriceObservationRepository


class PricingService:
    def __init__(self, repository: PriceObservationRepository) -> None:
        self._repo = repository

    async def record(self, observation: PriceObservation) -> PriceObservation:
        if observation.price_per_kg <= 0:
            raise ValueError("price_per_kg must be positive")
        observation.id = await self._repo.add(observation)
        return observation

    async def historical(
        self, material_category_id: str, days: int | None = None
    ) -> HistoricalPrice:
        observations = await self._repo.find(material_category_id, since=self._since(days))
        if not observations:
            return HistoricalPrice(
                kind=PriceKind.MARKET_OBSERVATION.value,
                material_category_id=material_category_id,
                average_price_per_kg=None,
                min_price_per_kg=None,
                max_price_per_kg=None,
                sample_count=0,
                verified_count=0,
            )
        prices = [o.price_per_kg for o in observations]
        verified = sum(1 for o in observations if o.verification_status == "verified")
        return HistoricalPrice(
            kind=PriceKind.MARKET_OBSERVATION.value,
            material_category_id=material_category_id,
            average_price_per_kg=round(median(prices), 2),
            min_price_per_kg=round(min(prices), 2),
            max_price_per_kg=round(max(prices), 2),
            sample_count=len(prices),
            verified_count=verified,
        )

    async def price_range(
        self, material_category_id: str, days: int | None = None
    ) -> tuple[float, float] | None:
        observations = await self._repo.find(material_category_id, since=self._since(days))
        if not observations:
            return None
        prices = [o.price_per_kg for o in observations]
        return (round(min(prices), 2), round(max(prices), 2))

    async def location_aware(
        self,
        material_category_id: str,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
    ) -> HistoricalPrice:
        nearby = await self._repo.find_near(material_category_id, latitude, longitude, radius_km)
        if not nearby:
            return HistoricalPrice(
                kind=PriceKind.INDICATIVE_VALUE.value,
                material_category_id=material_category_id,
                average_price_per_kg=None,
                min_price_per_kg=None,
                max_price_per_kg=None,
                sample_count=0,
                verified_count=0,
            )
        # distance-weighted average (closer observations weigh more)
        weighted = sum(o.price_per_kg / (1.0 + distance) for o, distance in nearby)
        total_weight = sum(1.0 / (1.0 + distance) for _, distance in nearby)
        prices = [o.price_per_kg for o, _ in nearby]
        return HistoricalPrice(
            kind=PriceKind.INDICATIVE_VALUE.value,
            material_category_id=material_category_id,
            average_price_per_kg=round(weighted / total_weight, 2),
            min_price_per_kg=round(min(prices), 2),
            max_price_per_kg=round(max(prices), 2),
            sample_count=len(prices),
            verified_count=sum(1 for o, _ in nearby if o.verification_status == "verified"),
        )

    async def compare_existing_buyers(self, material_category_id: str) -> list[PriceComparison]:
        observations = await self._repo.find(material_category_id, source="collector_entry")
        comparisons = [
            PriceComparison(
                kind=PriceKind.EXISTING_BUYER_PRICE.value,
                price_per_kg=o.price_per_kg,
                currency=o.currency,
                buyer_type=o.buyer_type,
                buyer_organization_id=o.buyer_organization_id,
                verified=o.verification_status == "verified",
                observed_at=o.observed_at,
            )
            for o in observations
        ]
        comparisons.sort(key=lambda c: c.price_per_kg, reverse=True)
        return comparisons

    async def compare_recycler_quotes(self, material_category_id: str) -> list[PriceComparison]:
        observations = await self._repo.find(material_category_id, source="recycler_quote")
        comparisons = [
            PriceComparison(
                kind=PriceKind.RECYCLER_QUOTE.value,
                price_per_kg=o.price_per_kg,
                currency=o.currency,
                buyer_type=o.buyer_type,
                buyer_organization_id=o.buyer_organization_id,
                verified=o.verification_status == "verified",
                observed_at=o.observed_at,
            )
            for o in observations
        ]
        comparisons.sort(key=lambda c: c.price_per_kg, reverse=True)
        return comparisons

    @staticmethod
    def _since(days: int | None) -> datetime | None:
        if days is None:
            return None
        return datetime.now(UTC) - timedelta(days=days)
