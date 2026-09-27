"""Geospatial: nearby recycler search (PostGIS)."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from ..auth import Principal, get_principal
from ..db import get_db
from ..schemas import NearbyRecyclerOut

router = APIRouter()


@router.get("/recycler/nearby", response_model=list[NearbyRecyclerOut])
async def nearby_recyclers(
    lat: float,
    lng: float,
    radius_km: float = Query(50, gt=0, le=500),
    material_category_id: str | None = None,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[NearbyRecyclerOut]:
    """Verified recyclers with a facility within `radius_km` of (lat, lng),
    ordered by distance. Optionally filtered by accepted material."""
    point = f"SRID=4326;POINT({lng} {lat})"
    today = date.today()
    cur = await conn.execute(
        """
        SELECT id, name, distance_km, latitude, longitude FROM (
            SELECT DISTINCT ON (ro.id)
                ro.id::text AS id,
                o.name AS name,
                ST_Distance(f.location, %s::geography) / 1000.0 AS distance_km,
                ST_Y(f.location::geometry) AS latitude,
                ST_X(f.location::geometry) AS longitude
            FROM recycler_organizations ro
            JOIN organizations o ON o.id = ro.organization_id
            JOIN recycler_facilities f ON f.recycler_organization_id = ro.id
            WHERE f.location IS NOT NULL
              AND ST_DWithin(f.location, %s::geography, %s)
              AND EXISTS (
                SELECT 1 FROM recycler_authorizations a
                WHERE a.recycler_organization_id = ro.id
                  AND a.status = 'verified'
                  AND (a.expiry_date IS NULL OR a.expiry_date >= %s)
              )
              AND (
                %s::uuid IS NULL
                OR NOT EXISTS (
                    SELECT 1 FROM recycler_material_acceptance ma
                    WHERE ma.recycler_organization_id = ro.id AND ma.is_accepted
                )
                OR EXISTS (
                    SELECT 1 FROM recycler_material_acceptance ma
                    WHERE ma.recycler_organization_id = ro.id AND ma.is_accepted
                      AND ma.material_category_id = %s::uuid
                )
              )
            ORDER BY ro.id, ST_Distance(f.location, %s::geography)
        ) t
        ORDER BY distance_km
        """,
        (point, point, radius_km * 1000, today, material_category_id, material_category_id, point),
    )
    rows = await cur.fetchall()
    return [
        NearbyRecyclerOut(
            id=r[0],
            name=r[1],
            distance_km=round(float(r[2]), 2),
            latitude=round(float(r[3]), 6) if r[3] is not None else None,
            longitude=round(float(r[4]), 6) if r[4] is not None else None,
        )
        for r in rows
    ]
