"""Price trends and instant value estimation.

Trends are DERIVED from observations (never invented) and cached into
`price_history` so repeated reads are cheap. The estimate is a range, not a
promise: it reflects observed prices with provenance attached.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import Principal, get_principal
from ..db import get_db

router = APIRouter()

# Assumed small-vehicle transport cost per km when a recycler has no stated rate.
# Mirrors matching.TRANSPORT_RS_PER_KM so the two never disagree.
TRANSPORT_RS_PER_KM = 12.0


@router.post("/pricing/refresh-history")
async def refresh_history(
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Derive `price_history` aggregates from recent observations.

    Grouped by (category, city) over trailing 30-day windows. Only VERIFIED
    observations feed the trusted average, so unverified collector entries can
    never inflate the market view.
    """
    cur = await conn.execute(
        """
        INSERT INTO price_history
            (material_category_id, region, period_start, period_end,
             average_price_per_kg, min_price_per_kg, max_price_per_kg, sample_count)
        SELECT
            material_category_id,
            COALESCE(city, 'ALL'),
            date_trunc('month', now())::date,
            (date_trunc('month', now()) + INTERVAL '1 month - 1 day')::date,
            avg(observed_price_per_kg),
            min(observed_price_per_kg),
            max(observed_price_per_kg),
            count(*)::int
        FROM price_observations
        WHERE verification_status = 'verified'
          AND observed_at >= now() - INTERVAL '90 days'
        GROUP BY material_category_id, COALESCE(city, 'ALL')
        ON CONFLICT (material_category_id, region, period_start)
        DO UPDATE SET
            period_end = EXCLUDED.period_end,
            average_price_per_kg = EXCLUDED.average_price_per_kg,
            min_price_per_kg = EXCLUDED.min_price_per_kg,
            max_price_per_kg = EXCLUDED.max_price_per_kg,
            sample_count = EXCLUDED.sample_count
        RETURNING material_category_id::text, region, average_price_per_kg, sample_count
        """,
    )
    rows = await cur.fetchall()
    return {
        "refreshed": len(rows),
        "entries": [
            {
                "material_category_id": r[0],
                "region": r[1],
                "average_price_per_kg": float(r[2]) if r[2] is not None else None,
                "sample_count": r[3],
            }
            for r in rows
        ],
    }


@router.get("/pricing/trends")
async def price_trends(
    material_category_id: str,
    city: str | None = None,
    days: int = Query(90, ge=7, le=365),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Direction and percentage change for a material.

    Verified observations drive the trend. Unverified collector entries are
    included with a reduced weight so early, low-volume data is not left with
    no signal at all — but the response always reports how much of the data was
    verified, so a thin dataset is visible as thin.
    """
    cur = await conn.execute(
        """
        WITH weighted AS (
            SELECT date_trunc('day', observed_at)::date AS d,
                   observed_price_per_kg AS p,
                   CASE WHEN verification_status = 'verified' THEN 1.0 ELSE 0.35 END AS w
            FROM price_observations
            WHERE material_category_id = %s::uuid
              AND (%s::text IS NULL OR city = %s)
              AND observed_at >= now() - make_interval(days => %s)
        ),
        agg AS (
            SELECT d, sum(p * w) / NULLIF(sum(w), 0) AS wp, max(p) AS mp, min(p) AS np,
                   count(*)::int AS n,
                   count(*) FILTER (WHERE w = 1.0)::int AS verified_n,
                   -- Verified-only mean for this day, when it exists.
                   avg(p) FILTER (WHERE w = 1.0) AS vp
            FROM weighted GROUP BY d
        ),
        series AS (
            SELECT jsonb_agg(
                jsonb_build_object('date', d, 'price', round(wp::numeric, 2),
                                   'samples', n, 'verified', verified_n)
                ORDER BY d) AS pts
            FROM agg
        ),
        bounds AS (
            SELECT
                -- The headline direction is driven by VERIFIED data only when any
                -- verified data exists in the window. An unverified collector
                -- entry (often stale or self-reported) must never be able to flip
                -- a rising market into a "falling" one. Unverified data is still
                -- reported in the series and counted, so thin periods stay visible.
                (array_agg(COALESCE(vp, wp) ORDER BY d ASC) FILTER
                     (WHERE vp IS NOT NULL))[1] AS first_price,
                (array_agg(COALESCE(vp, wp) ORDER BY d DESC) FILTER
                     (WHERE vp IS NOT NULL))[1] AS last_price,
                min(np) AS min_price, max(mp) AS max_price,
                sum(n)::int AS samples,
                sum(verified_n)::int AS verified,
                count(*) FILTER (WHERE vp IS NOT NULL)::int AS verified_days
            FROM agg
        )
        SELECT b.first_price, b.last_price, b.min_price, b.max_price,
               b.samples, b.verified, b.verified_days,
               (b.last_price - b.first_price) / NULLIF(b.first_price, 0) * 100.0 AS pct,
               s.pts
        FROM bounds b CROSS JOIN series s
        """,
        (material_category_id, city, city, days),
    )
    r = await cur.fetchone()
    if r is None or r[4] == 0:
        raise HTTPException(status_code=404, detail="No price observations for this material")

    verified = int(r[5] or 0)
    total = int(r[4] or 0)
    verified_days = int(r[6] or 0)

    # Direction is only asserted when verified data exists; otherwise the data
    # is too weak to claim a trend and we say so.
    if verified_days == 0:
        return {
            "material_category_id": material_category_id,
            "city": city,
            "days": days,
            "direction": "unknown",
            "pct_change": None,
            "first_price": None,
            "last_price": None,
            "min_price": round(float(r[2]), 2) if r[2] is not None else None,
            "max_price": round(float(r[3]), 2) if r[3] is not None else None,
            "samples": total,
            "verified_samples": verified,
            "verified_days": 0,
            "confidence": "low",
            "note": "No verified observations in this window; trend withheld.",
            "series": r[8],
        }

    pct = float(r[7]) if r[7] is not None else 0.0
    if pct > 2:
        direction = "rising"
    elif pct < -2:
        direction = "falling"
    else:
        direction = "stable"

    return {
        "material_category_id": material_category_id,
        "city": city,
        "days": days,
        "direction": direction,
        "pct_change": round(pct, 2),
        "first_price": round(float(r[0]), 2) if r[0] is not None else None,
        "last_price": round(float(r[1]), 2) if r[1] is not None else None,
        "min_price": round(float(r[2]), 2) if r[2] is not None else None,
        "max_price": round(float(r[3]), 2) if r[3] is not None else None,
        "samples": total,
        "verified_samples": verified,
        "verified_days": verified_days,
        "confidence": (
            "high" if total >= 5 and verified == total
            else "medium" if verified > 0
            else "low"
        ),
        "series": r[8],
    }


@router.get("/pricing/board")
async def price_board(
    city: str | None = None,
    locale: str = Query("en"),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Simple, low-literacy-friendly price board: one row per material.

    Shows the current buying rate, a plain-language direction, and a range.
    Designed to render as large text with an icon per row.
    """
    cur = await conn.execute(
        """
        WITH latest AS (
            SELECT DISTINCT ON (po.material_category_id, COALESCE(po.city, 'ALL'))
                po.material_category_id,
                COALESCE(po.city, 'ALL') AS city,
                po.observed_price_per_kg,
                po.observed_at
            FROM price_observations po
            WHERE po.verification_status = 'verified'
              AND (%s::text IS NULL OR po.city = %s OR po.city IS NULL)
            ORDER BY po.material_category_id, COALESCE(po.city, 'ALL'),
                     po.observed_at DESC
        ),
        agg AS (
            SELECT po.material_category_id,
                   avg(po.observed_price_per_kg) AS avg_p,
                   min(po.observed_price_per_kg) AS min_p,
                   max(po.observed_price_per_kg) AS max_p,
                   count(*)::int AS n,
                   (array_agg(po.observed_price_per_kg ORDER BY po.observed_at ASC))[1]  AS first_p,
                   (array_agg(po.observed_price_per_kg ORDER BY po.observed_at DESC))[1] AS last_p
            FROM price_observations po
            WHERE po.verification_status = 'verified'
              AND po.observed_at >= now() - INTERVAL '90 days'
              AND (%s::text IS NULL OR po.city = %s)
            GROUP BY po.material_category_id
        )
        SELECT mc.id::text AS id, mc.code AS code,
               COALESCE(t.value, mc.name) AS name,
               l.observed_price_per_kg AS current_price, l.city AS city,
               l.observed_at AS observed_at,
               a.avg_p AS avg_p, a.min_p AS min_p, a.max_p AS max_p,
               a.n AS n,
               (a.last_p - a.first_p) / NULLIF(a.first_p, 0) * 100.0 AS pct_change
        FROM material_categories mc
        JOIN latest l ON l.material_category_id = mc.id
        JOIN agg a ON a.material_category_id = mc.id
        LEFT JOIN translations t
               ON t.entity_type = 'material_category' AND t.entity_id = mc.id
              AND t.field = 'name' AND t.locale = %s
        WHERE mc.is_active
        ORDER BY a.avg_p DESC
        """,
        (city, city, city, city, locale),
    )
    board = []
    for r in await cur.fetchall():
        pct = float(r[10]) if r[10] is not None else 0.0
        if pct > 2:
            direction, icon = "rising", "trending_up"
        elif pct < -2:
            direction, icon = "falling", "trending_down"
        else:
            direction, icon = "stable", "trending_flat"
        board.append(
            {
                "material_category_id": r[0],
                "code": r[1],
                "name": r[2],
                "current_price": round(float(r[3]), 2) if r[3] is not None else None,
                "city": r[4],
                "observed_at": r[5],
                "avg_price": round(float(r[6]), 2) if r[6] is not None else None,
                "min_price": round(float(r[7]), 2) if r[7] is not None else None,
                "max_price": round(float(r[8]), 2) if r[8] is not None else None,
                "samples": r[9],
                "direction": direction,
                "icon": icon,
                "pct_change": round(pct, 1),
            }
        )
    return {"city": city, "locale": locale, "count": len(board), "board": board}


@router.get("/pricing/estimate-value")
async def estimate_value(
    material_category_id: str,
    weight_kg: float = Query(..., gt=0, le=100000),
    city: str | None = None,
    transport_km: float = Query(0, ge=0, le=2000),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Instant approximate value for a lot, as a RANGE with provenance.

    Deliberately not a single number: a collector should see a range and the
    reason for it, not false precision. Falls back to national (all-city)
    observations when the city has none.
    """
    cur = await conn.execute(
        """
        WITH city_obs AS (
            SELECT * FROM price_observations
            WHERE material_category_id = %s::uuid
              AND verification_status = 'verified'
              AND city = %s
              AND observed_at >= now() - INTERVAL '90 days'
        ),
        all_obs AS (
            SELECT * FROM price_observations
            WHERE material_category_id = %s::uuid
              AND verification_status = 'verified'
              AND observed_at >= now() - INTERVAL '90 days'
        ),
        pick AS (
            SELECT * FROM city_obs
            UNION ALL
            SELECT * FROM all_obs WHERE NOT EXISTS (SELECT 1 FROM city_obs)
        )
        SELECT
            (SELECT avg(observed_price_per_kg) FROM pick),
            (SELECT min(observed_price_per_kg) FROM pick),
            (SELECT max(observed_price_per_kg) FROM pick),
            (SELECT count(*)::int FROM pick),
            (SELECT count(*)::int FROM city_obs),
            (SELECT COALESCE(city, 'ALL') FROM pick LIMIT 1)
        """,
        (material_category_id, city, material_category_id),
    )
    r = await cur.fetchone()

    if not r or r[3] == 0:
        raise HTTPException(
            status_code=404,
            detail="No verified price data for this material yet",
        )

    avg_p, min_p, max_p = float(r[0]), float(r[1]), float(r[2])
    scope = r[5] if city is None or r[4] == 0 else city
    city_specific = bool(r[4]) and r[4] > 0

    # Transport reduces what the collector actually takes home, so the net figure
    # is the one that matters for a decision.
    transport = round(transport_km * TRANSPORT_RS_PER_KM, 2)

    def net(gross: float) -> float:
        return round(max(0.0, gross - transport), 2)

    return {
        "material_category_id": material_category_id,
        "weight_kg": weight_kg,
        "currency": "INR",
        "price_per_kg": {
            "avg": round(avg_p, 2),
            "min": round(min_p, 2),
            "max": round(max_p, 2),
        },
        "gross_value": {
            "low": round(min_p * weight_kg, 2),
            "mid": round(avg_p * weight_kg, 2),
            "high": round(max_p * weight_kg, 2),
        },
        "transport_cost": transport,
        "transport_km": transport_km,
        "estimated_value": {
            "low": net(min_p * weight_kg),
            "mid": net(avg_p * weight_kg),
            "high": net(max_p * weight_kg),
        },
        "samples": r[3],
        "region": scope,
        "city_specific": city_specific,
        "basis": "verified observations (last 90 days)",
        "disclaimer": "Approximate only. Final price is decided at handover after weighing.",
    }
