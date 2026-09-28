"""Price observation data access (with PostGIS for location-aware lookup)."""

import math
from abc import ABC, abstractmethod
from datetime import datetime

from psycopg_pool import AsyncConnectionPool

from ..models.pricing import PriceObservation


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


class PriceObservationRepository(ABC):
    @abstractmethod
    async def add(self, observation: PriceObservation) -> str:
        """Persist an observation; return its id."""

    @abstractmethod
    async def find(
        self,
        material_category_id: str,
        source: str | None = None,
        since: datetime | None = None,
    ) -> list[PriceObservation]:
        """Return observations for a material, optionally filtered by source/time."""

    @abstractmethod
    async def find_near(
        self,
        material_category_id: str,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[tuple[PriceObservation, float]]:
        """Return (observation, distance_km) within radius of a point."""


class InMemoryPriceObservationRepository(PriceObservationRepository):
    def __init__(self) -> None:
        self._observations: dict[str, PriceObservation] = {}
        self._next_id = 1

    async def add(self, observation: PriceObservation) -> str:
        observation.id = observation.id or str(self._next_id)
        self._next_id += 1
        self._observations[observation.id] = observation
        return observation.id

    async def find(
        self,
        material_category_id: str,
        source: str | None = None,
        since: datetime | None = None,
    ) -> list[PriceObservation]:
        result = []
        for obs in self._observations.values():
            if obs.material_category_id != material_category_id:
                continue
            if source is not None and obs.source != source:
                continue
            if since is not None and obs.observed_at:
                try:
                    observed = datetime.fromisoformat(obs.observed_at.replace("Z", "+00:00"))
                    if observed < since:
                        continue
                except ValueError:
                    pass  # unparseable timestamp: include
            result.append(obs)
        return result

    async def find_near(
        self,
        material_category_id: str,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[tuple[PriceObservation, float]]:
        result = []
        for obs in self._observations.values():
            if obs.material_category_id != material_category_id:
                continue
            if obs.latitude is None or obs.longitude is None:
                continue
            distance = haversine_km(latitude, longitude, obs.latitude, obs.longitude)
            if distance <= radius_km:
                result.append((obs, distance))
        result.sort(key=lambda pair: pair[1])
        return result


class PostgresPriceObservationRepository(PriceObservationRepository):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def add(self, observation: PriceObservation) -> str:
        location = None
        if observation.latitude is not None and observation.longitude is not None:
            location = f"SRID=4326;POINT({observation.longitude} {observation.latitude})"
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO price_observations "
                "(material_category_id, material_subcategory_id, grade_id, location, city, state, "
                "observed_price_per_kg, unit, currency, buyer_type, buyer_organization_id, source, "
                "weight_kg, transport_cost, verification_status, confidence, observed_at) "
                "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::geography, %s, %s, %s, %s, %s, %s, "
                "%s::uuid, %s, %s, %s, %s, %s, now()) RETURNING id::text",
                (
                    observation.material_category_id,
                    observation.material_subcategory_id,
                    observation.grade_id,
                    location,
                    observation.city,
                    observation.state,
                    observation.price_per_kg,
                    observation.unit,
                    observation.currency,
                    observation.buyer_type,
                    observation.buyer_organization_id,
                    observation.source,
                    observation.weight_kg,
                    observation.transport_cost,
                    observation.verification_status,
                    observation.confidence,
                ),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to create price observation")
            return row[0]

    async def find(
        self,
        material_category_id: str,
        source: str | None = None,
        since: datetime | None = None,
    ) -> list[PriceObservation]:
        query = (
            "SELECT id::text, material_category_id::text, material_subcategory_id::text, "
            "grade_id::text, city, state, observed_price_per_kg, unit, currency, "
            "buyer_type, buyer_organization_id::text, source, verification_status, "
            "confidence, observed_at "
            "FROM price_observations WHERE material_category_id = %s::uuid"
        )
        params: list = [material_category_id]
        if source is not None:
            query += " AND source = %s"
            params.append(source)
        if since is not None:
            query += " AND observed_at >= %s"
            params.append(since)
        query += " ORDER BY observed_at DESC"
        async with self._pool.connection() as conn:
            cur = await conn.execute(query, tuple(params))
            rows = await cur.fetchall()
            return [self._to_observation(r) for r in rows]

    async def find_near(
        self,
        material_category_id: str,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[tuple[PriceObservation, float]]:
        point = f"SRID=4326;POINT({longitude} {latitude})"
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id::text, material_category_id::text, material_subcategory_id::text, "
                "grade_id::text, city, state, observed_price_per_kg, unit, currency, "
                "buyer_type, buyer_organization_id::text, source, verification_status, "
                "confidence, observed_at, "
                "ST_Distance(location, %s::geography) / 1000.0 AS distance_km "
                "FROM price_observations "
                "WHERE material_category_id = %s::uuid AND location IS NOT NULL "
                "AND ST_DWithin(location, %s::geography, %s) "
                "ORDER BY distance_km",
                (point, material_category_id, point, radius_km * 1000),
            )
            rows = await cur.fetchall()
            return [(self._to_observation(r), float(r[14])) for r in rows]

    @staticmethod
    def _to_observation(row) -> PriceObservation:
        return PriceObservation(
            id=row[0],
            material_category_id=row[1],
            material_subcategory_id=row[2],
            grade_id=row[3],
            city=row[4],
            state=row[5],
            price_per_kg=float(row[6]),
            unit=row[7],
            currency=row[8],
            buyer_type=row[9],
            buyer_organization_id=row[10],
            source=row[11],
            verification_status=row[12],
            confidence=float(row[13]),
            observed_at=row[14].isoformat() if row[14] else None,
        )
