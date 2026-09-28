"""Recycler data access (with PostGIS distance queries for matching)."""

from abc import ABC, abstractmethod

from psycopg_pool import AsyncConnectionPool

from ..models.matching import RecyclerCandidate
from ..models.recycler import AuthorizationRecord, effective_authorization


class RecyclerRepository(ABC):
    @abstractmethod
    async def find_candidates(self, latitude: float, longitude: float) -> list[RecyclerCandidate]:
        """Return matching candidates near a point (authorization-gated)."""


class PostgresRecyclerRepository(RecyclerRepository):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def find_candidates(self, latitude: float, longitude: float) -> list[RecyclerCandidate]:
        point = f"SRID=4326;POINT({longitude} {latitude})"
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT ro.id::text, o.name, ro.pickup_available, "
                "MIN(ST_Distance(f.location, %s::geography) / 1000.0) AS distance_km "
                "FROM recycler_organizations ro "
                "JOIN organizations o ON o.id = ro.organization_id "
                "JOIN recycler_facilities f ON f.recycler_organization_id = ro.id "
                "WHERE f.location IS NOT NULL "
                "GROUP BY ro.id, o.name, ro.pickup_available",
                (point,),
            )
            rows = await cur.fetchall()

            candidates: list[RecyclerCandidate] = []
            for row in rows:
                recycler_id, name, pickup, distance = row[0], row[1], row[2], float(row[3])
                authorizations = await self._authorizations(conn, recycler_id)
                _, authorized = effective_authorization(authorizations)
                if not authorized:
                    continue
                candidates.append(
                    RecyclerCandidate(
                        recycler_id=recycler_id,
                        name=name,
                        authorized=True,
                        accepted_materials=await self._accepted_materials(conn, recycler_id),
                        service_radius_km=await self._service_radius(conn, recycler_id),
                        distance_km=distance,
                        pickup_available=pickup,
                        reliability=await self._reliability(conn, recycler_id),
                    )
                )
            return candidates

    @staticmethod
    async def _authorizations(conn, recycler_id: str) -> list[AuthorizationRecord]:
        cur = await conn.execute(
            "SELECT status, expiry_date FROM recycler_authorizations "
            "WHERE recycler_organization_id = %s::uuid",
            (recycler_id,),
        )
        return [AuthorizationRecord(status=r[0], expiry_date=r[1]) for r in await cur.fetchall()]

    @staticmethod
    async def _accepted_materials(conn, recycler_id: str) -> set[str]:
        cur = await conn.execute(
            "SELECT material_category_id::text FROM recycler_material_acceptance "
            "WHERE recycler_organization_id = %s::uuid AND is_accepted",
            (recycler_id,),
        )
        return {r[0] for r in await cur.fetchall()}

    @staticmethod
    async def _service_radius(conn, recycler_id: str) -> float | None:
        cur = await conn.execute(
            "SELECT MAX(radius_km) FROM recycler_service_areas "
            "WHERE recycler_organization_id = %s::uuid AND is_active",
            (recycler_id,),
        )
        row = await cur.fetchone()
        return float(row[0]) if row and row[0] is not None else None

    @staticmethod
    async def _reliability(conn, recycler_id: str) -> float:
        cur = await conn.execute(
            "SELECT count(*)::int FROM transactions "
            "WHERE recycler_organization_id = %s::uuid AND status = 'COMPLETED'",
            (recycler_id,),
        )
        row = await cur.fetchone()
        count = row[0] if row else 0
        return min(1.0, count / 10.0)
