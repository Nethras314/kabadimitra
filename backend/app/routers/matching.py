"""Recycler matching for a lot.

Matches are ranked by a composite score (authorization, material acceptance,
distance, proximity) — never by gross price alone.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb

from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..db import get_db
from ..schemas import MatchOut
from .lots import _owned_lot_id

router = APIRouter()


async def _lot_materials(conn, lot_id: str) -> list[str]:
    cur = await conn.execute(
        "SELECT DISTINCT material_category_id::text FROM lot_items "
        "WHERE lot_id = %s::uuid AND material_category_id IS NOT NULL",
        (lot_id,),
    )
    return [r[0] for r in await cur.fetchall()]


async def _accepted_materials(conn, recycler_id: str) -> set[str]:
    cur = await conn.execute(
        "SELECT material_category_id::text FROM recycler_material_acceptance "
        "WHERE recycler_organization_id = %s::uuid AND is_accepted",
        (recycler_id,),
    )
    return {r[0] for r in await cur.fetchall()}


@router.post("/lots/{lot_id}/matches", response_model=list[MatchOut])
async def generate_matches(
    lot_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[MatchOut]:
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    material_ids = await _lot_materials(conn, lot_id)
    if not material_ids:
        raise HTTPException(status_code=400, detail="Lot has no classified materials")

    today = date.today()
    cur = await conn.execute(
        """
        SELECT ro.id::text, o.name,
               MIN(ST_Distance(f.location,
                   (SELECT pickup_location FROM lots WHERE id = %s::uuid)) / 1000.0) AS distance_km
        FROM recycler_organizations ro
        JOIN organizations o ON o.id = ro.organization_id
        LEFT JOIN recycler_facilities f ON f.recycler_organization_id = ro.id
        WHERE EXISTS (
            SELECT 1 FROM recycler_authorizations a
            WHERE a.recycler_organization_id = ro.id
              AND a.status = 'verified'
              AND (a.expiry_date IS NULL OR a.expiry_date >= %s)
        )
        GROUP BY ro.id, o.name
        """,
        (lot_id, today),
    )
    candidates = await cur.fetchall()

    await conn.execute(
        "DELETE FROM matches WHERE lot_id = %s::uuid AND status = 'proposed'", (lot_id,)
    )

    matches: list[MatchOut] = []
    for c in candidates:
        recycler_id, name = c[0], c[1]
        distance_km = float(c[2]) if c[2] is not None else None
        accepted = await _accepted_materials(conn, recycler_id)
        if accepted and not (accepted & set(material_ids)):
            continue  # explicit restrictions with no overlap

        overlap = set(material_ids) if not accepted else (accepted & set(material_ids))
        coverage = len(overlap) / len(material_ids)
        proximity = max(0.0, 40.0 - (distance_km * 2.0)) if distance_km is not None else 0.0
        score = round(coverage * 60.0 + proximity, 2)
        reason = {
            "authorization": "verified",
            "material_coverage": round(coverage, 2),
            "distance_km": round(distance_km, 2) if distance_km is not None else None,
            "proximity_score": round(proximity, 2),
        }

        cur = await conn.execute(
            "INSERT INTO matches (lot_id, recycler_organization_id, score, match_reason, "
            "distance_km, status) VALUES (%s::uuid, %s::uuid, %s, %s, %s, 'proposed') "
            "RETURNING id::text",
            (lot_id, recycler_id, score, Jsonb(reason), distance_km),
        )
        match_id = (await cur.fetchone())[0]
        matches.append(
            MatchOut(
                id=match_id,
                lot_id=lot_id,
                recycler_organization_id=recycler_id,
                recycler_name=name,
                score=score,
                distance_km=distance_km,
                status="proposed",
            )
        )

    matches.sort(key=lambda m: m.score or 0, reverse=True)
    return matches


@router.get("/lots/{lot_id}/matches", response_model=list[MatchOut])
async def list_matches(
    lot_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[MatchOut]:
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    cur = await conn.execute(
        "SELECT m.id::text, m.lot_id::text, m.recycler_organization_id::text, o.name, "
        "m.score, m.distance_km, m.status "
        "FROM matches m "
        "JOIN recycler_organizations ro ON ro.id = m.recycler_organization_id "
        "JOIN organizations o ON o.id = ro.organization_id "
        "WHERE m.lot_id = %s::uuid ORDER BY m.score DESC NULLS LAST",
        (lot_id,),
    )
    rows = await cur.fetchall()
    return [
        MatchOut(
            id=r[0],
            lot_id=r[1],
            recycler_organization_id=r[2],
            recycler_name=r[3],
            score=float(r[4]) if r[4] is not None else None,
            distance_km=float(r[5]) if r[5] is not None else None,
            status=r[6],
        )
        for r in rows
    ]
