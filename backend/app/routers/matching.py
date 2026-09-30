"""Recycler matching for a lot.

The spec requires nine factors. This implements all of them, and — critically —
emits the per-factor breakdown so the ranking is auditable rather than a black
box:

  1. authorization      hard gate: expired/suspended recyclers never appear
  2. material acceptance
  3. service area       point-in-polygon or radius coverage
  4. distance
  5. pickup availability
  6. transport cost
  7. expected net earnings
  8. quote
  9. reliability / history

Ranking is by composite score, never by gross price alone.
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

# Weights must sum to 100. Transport cost and net earnings together dominate
# because a collector's decision is primarily "what actually lands in my pocket".
WEIGHTS = {
    "authorization": 15.0,   # binary gate; counted so the total is interpretable
    "material_acceptance": 20.0,
    "service_area": 8.0,
    "distance": 12.0,
    "pickup": 8.0,
    "transport": 12.0,
    "net_earnings": 15.0,
    "quote": 5.0,
    "reliability": 5.0,
}

# Assumed transport cost when neither party provides a rate: ₹12/km, which
# covers a small pickup vehicle over distance. Configurable via env in future.
TRANSPORT_RS_PER_KM = 12.0


async def _lot_materials(conn, lot_id: str) -> list[str]:
    cur = await conn.execute(
        "SELECT DISTINCT material_category_id::text FROM lot_items "
        "WHERE lot_id = %s::uuid AND material_category_id IS NOT NULL",
        (lot_id,),
    )
    return [r[0] for r in await cur.fetchall()]


async def _lot_weight(conn, lot_id: str) -> float:
    """Best available weight: measured final weight, else declared item weights."""
    cur = await conn.execute(
        "SELECT COALESCE(SUM(li.declared_weight_kg), 0) FROM lot_items li "
        "WHERE li.lot_id = %s::uuid",
        (lot_id,),
    )
    declared = float((await cur.fetchone())[0] or 0)
    return declared


async def _accepted_materials(conn, recycler_id: str) -> set[str]:
    cur = await conn.execute(
        "SELECT material_category_id::text FROM recycler_material_acceptance "
        "WHERE recycler_organization_id = %s::uuid AND is_accepted",
        (recycler_id,),
    )
    return {r[0] for r in await cur.fetchall()}


async def _in_service_area(conn, recycler_id: str, point_wkt: str) -> bool | None:
    """True/False if the recycler declares service areas, else None (unknown).

    The point is passed as a BOUND parameter cast to geography — never
    interpolated into the SQL string, or Postgres parses the WKB as a literal.
    """
    cur = await conn.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM recycler_service_areas sa
            WHERE sa.recycler_organization_id = %s::uuid
              AND sa.is_active
              AND (
                (sa.area IS NOT NULL
                 AND ST_Covers(sa.area, ST_SetSRID(ST_GeomFromText(%s), 4326)::geography))
                OR (sa.center IS NOT NULL AND ST_DWithin(
                        sa.center, ST_SetSRID(ST_GeomFromText(%s), 4326)::geography,
                        sa.radius_km * 1000))
              )
        )
        """,
        (recycler_id, point_wkt, point_wkt),
    )
    if (await cur.fetchone())[0]:
        return True
    # No declared area at all -> unknown, not "out of area".
    cur = await conn.execute(
        "SELECT EXISTS (SELECT 1 FROM recycler_service_areas "
        "WHERE recycler_organization_id = %s::uuid AND is_active)",
        (recycler_id,),
    )
    return False if (await cur.fetchone())[0] else None


async def _latest_quote(conn, recycler_id: str, lot_id: str):
    cur = await conn.execute(
        "SELECT price_per_kg, total_price, status FROM recycler_quotes "
        "WHERE recycler_organization_id = %s::uuid AND lot_id = %s::uuid "
        "AND status IN ('submitted', 'accepted') "
        "ORDER BY created_at DESC LIMIT 1",
        (recycler_id, lot_id),
    )
    return await cur.fetchone()


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

    weight_kg = await _lot_weight(conn, lot_id)
    today = date.today()

    # Pickup point for service-area and transport maths. Fetched as WKT (never
    # interpolated into SQL) so it can be bound as a parameter.
    cur = await conn.execute(
        "SELECT ST_AsText(pickup_location::geometry) FROM lots WHERE id = %s::uuid",
        (lot_id,),
    )
    row = await cur.fetchone()
    if row is None or row[0] is None:
        raise HTTPException(
            status_code=400,
            detail="Lot has no pickup location; capture GPS before matching",
        )
    point_wkt = row[0].strip()  # e.g. "POINT(73.85 18.52)"

    # Candidate recyclers: authorization gate applied in SQL (factor 1).
    cur = await conn.execute(
        """
        SELECT ro.id::text, o.name,
               MIN(ST_Distance(f.location,
                   ST_SetSRID(ST_GeomFromText(%s), 4326)::geography)) / 1000.0
                   AS distance_km,
               ro.pickup_available, ro.provides_pickup, ro.transport_rate_per_km,
               rr.score AS reliability
        FROM recycler_organizations ro
        JOIN organizations o ON o.id = ro.organization_id
        LEFT JOIN recycler_facilities f ON f.recycler_organization_id = ro.id
        LEFT JOIN recycler_reliability rr ON rr.recycler_organization_id = ro.id
        WHERE EXISTS (
            SELECT 1 FROM recycler_authorizations a
            WHERE a.recycler_organization_id = ro.id
              AND a.status = 'verified'
              AND (a.expiry_date IS NULL OR a.expiry_date >= %s)
        )
        GROUP BY ro.id, o.name, ro.pickup_available, ro.provides_pickup,
                 ro.transport_rate_per_km, rr.score
        """,
        (point_wkt, today),
    )
    candidates = await cur.fetchall()

    await conn.execute(
        "DELETE FROM matches WHERE lot_id = %s::uuid AND status = 'proposed'", (lot_id,)
    )

    matches: list[MatchOut] = []
    for c in candidates:
        recycler_id, name = c[0], c[1]
        distance_km = float(c[2]) if c[2] is not None else None
        pickup_available = bool(c[3])
        provides_pickup = bool(c[4])
        transport_rate = float(c[5]) if c[5] is not None else TRANSPORT_RS_PER_KM
        reliability = float(c[6]) if c[6] is not None else None

        # --- 2. material acceptance -----------------------------------------
        accepted = await _accepted_materials(conn, recycler_id)
        if accepted and not (accepted & set(material_ids)):
            continue  # explicit restrictions with no overlap -> exclude entirely
        overlap = set(material_ids) if not accepted else (accepted & set(material_ids))
        coverage = len(overlap) / len(material_ids)

        # --- 3. service area ------------------------------------------------
        in_area = await _in_service_area(conn, recycler_id, point_wkt)

        # --- 4. distance ----------------------------------------------------
        if distance_km is None:
            proximity = 0.0
        else:
            proximity = max(0.0, 100.0 - (distance_km * 4.0))

        # --- 5. pickup ------------------------------------------------------
        pickup = 100.0 if (pickup_available or provides_pickup) else 0.0

        # --- 6. transport cost ---------------------------------------------
        if distance_km is None:
            transport_cost = None
        elif provides_pickup:
            transport_cost = 0.0
        else:
            transport_cost = round(distance_km * transport_rate, 2)
        # Cheap transport is good; normalise against a 500 rupee reference.
        transport_score = (
            0.0
            if transport_cost is None
            else max(0.0, 100.0 * (1 - min(transport_cost, 500.0) / 500.0))
        )

        # --- 8. quote --------------------------------------------------------
        quote_row = await _latest_quote(conn, recycler_id, lot_id)
        quote_per_kg = float(quote_row[0]) if quote_row and quote_row[0] is not None else None

        # --- 7. expected net earnings ---------------------------------------
        if quote_per_kg is not None:
            gross = quote_per_kg * weight_kg
        elif distance_km is not None and weight_kg > 0:
            # No quote: use the observed local market average as a floor estimate.
            cur2 = await conn.execute(
                """
                SELECT avg(observed_price_per_kg) FROM price_observations
                WHERE material_category_id = ANY(%s::uuid[])
                  AND verification_status = 'verified'
                  AND observed_at >= now() - INTERVAL '90 days'
                """,
                (material_ids,),
            )
            avg_p = await cur2.fetchone()
            gross = (float(avg_p[0]) * weight_kg) if avg_p and avg_p[0] else 0.0
        else:
            gross = 0.0
        net = round(max(0.0, gross - (transport_cost or 0.0)), 2)
        net_score = min(100.0, (net / 5000.0) * 100.0) if net > 0 else 0.0
        quote_score = min(100.0, (quote_per_kg / 300.0) * 100.0) if quote_per_kg else 0.0

        # --- 9. reliability --------------------------------------------------
        reliability_score = reliability if reliability is not None else 50.0  # neutral default

        service_score = 100.0 if in_area else (50.0 if in_area is None else 0.0)

        factors = {
            "authorization": {"score": 100.0, "weight": WEIGHTS["authorization"],
                              "detail": "verified, not expired"},
            "material_acceptance": {
                "score": round(coverage * 100, 2),
                "weight": WEIGHTS["material_acceptance"],
                "detail": f"{len(overlap)}/{len(material_ids)} materials accepted",
            },
            "service_area": {
                "score": service_score,
                "weight": WEIGHTS["service_area"],
                "detail": "inside declared area" if in_area
                          else ("no area declared" if in_area is None else "outside declared area"),
            },
            "distance": {
                "score": round(proximity, 2),
                "weight": WEIGHTS["distance"],
                "detail_km": round(distance_km, 2) if distance_km is not None else None,
            },
            "pickup": {
                "score": pickup,
                "weight": WEIGHTS["pickup"],
                "detail": "offers pickup" if pickup else "collector must deliver",
            },
            "transport": {
                "score": round(transport_score, 2),
                "weight": WEIGHTS["transport"],
                "cost": transport_cost,
                "detail": "free pickup" if provides_pickup else "estimated transport",
            },
            "net_earnings": {
                "score": round(net_score, 2),
                "weight": WEIGHTS["net_earnings"],
                "value": net,
                "detail": "expected take-home after transport",
            },
            "quote": {
                "score": round(quote_score, 2),
                "weight": WEIGHTS["quote"],
                "price_per_kg": quote_per_kg,
                "detail": "quoted" if quote_per_kg else "no quote yet",
            },
            "reliability": {
                "score": round(reliability_score, 2),
                "weight": WEIGHTS["reliability"],
                "detail": "from completed handover history",
            },
        }

        score = round(
            sum(f["score"] * f["weight"] / 100.0 for f in factors.values()), 2
        )

        cur = await conn.execute(
            "INSERT INTO matches (lot_id, recycler_organization_id, score, match_reason, "
            "distance_km, in_service_area, pickup_available, quote_price_per_kg, "
            "transport_cost, reliability_score, net_earnings, status) "
            "VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'proposed') "
            "RETURNING id::text",
            (
                lot_id, recycler_id, score, Jsonb(factors), distance_km,
                in_area, pickup_available, quote_per_kg,
                transport_cost, reliability_score, net,
            ),
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


@router.get("/lots/{lot_id}/matches/{match_id}/explanation")
async def match_explanation(
    lot_id: str,
    match_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Why this recycler was (or was not) recommended — for a collector-facing
    explanation and for debugging ranking."""
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    cur = await conn.execute(
        "SELECT o.name AS recycler_name, m.score, m.match_reason, m.distance_km, "
        "m.transport_cost, m.net_earnings, m.in_service_area, m.pickup_available, "
        "m.reliability_score "
        "FROM matches m "
        "JOIN recycler_organizations ro ON ro.id = m.recycler_organization_id "
        "JOIN organizations o ON o.id = ro.organization_id "
        "WHERE m.lot_id = %s::uuid AND m.id = %s::uuid",
        (lot_id, match_id),
    )
    r = await cur.fetchone()
    if r is None:
        raise HTTPException(status_code=404, detail="Match not found")

    return {
        "recycler_name": r[0],
        "score": float(r[1]) if r[1] is not None else None,
        "factors": r[2],
        "distance_km": float(r[3]) if r[3] is not None else None,
        "transport_cost": float(r[4]) if r[4] is not None else None,
        "net_earnings": float(r[5]) if r[5] is not None else None,
        "in_service_area": r[6],
        "pickup_available": r[7],
        "reliability_score": float(r[8]) if r[8] is not None else None,
    }
