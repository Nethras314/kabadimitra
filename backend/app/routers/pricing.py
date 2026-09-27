"""Price discovery: provenance-backed observations + contextual estimate.

There is no single hard-coded price. Observations carry provenance; collector
entries are observations, not authoritative market prices.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..db import get_db
from ..schemas import (
    PriceObservationCreate,
    PriceObservationOut,
    PricingEstimateOut,
    PricingSummary,
)

router = APIRouter()


def _obs_out(r) -> PriceObservationOut:
    return PriceObservationOut(
        id=r[0],
        material_category_id=r[1],
        material_subcategory_id=r[2],
        grade_id=r[3],
        city=r[4],
        state=r[5],
        observed_price_per_kg=float(r[6]),
        currency=r[7],
        buyer_type=r[8],
        source=r[9],
        verification_status=r[10],
        weight_kg=float(r[11]) if r[11] is not None else None,
        transport_cost=float(r[12]) if r[12] is not None else None,
        observed_at=r[13],
    )


@router.post("/price-observations", response_model=PriceObservationOut, status_code=201)
async def create_observation(
    body: PriceObservationCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> PriceObservationOut:
    verification_status = "verified" if body.source == "verification" else "unverified"
    observed_at = body.observed_at or datetime.now(timezone.utc)

    location = None
    if body.latitude is not None and body.longitude is not None:
        location = f"SRID=4326;POINT({body.longitude} {body.latitude})"

    cur = await conn.execute(
        "INSERT INTO price_observations (material_category_id, material_subcategory_id, "
        "grade_id, location, city, state, observed_price_per_kg, currency, buyer_type, "
        "buyer_organization_id, source, source_user_id, weight_kg, transport_cost, "
        "verification_status, observed_at, notes) "
        "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::geography, %s, %s, %s, %s, %s, "
        "%s::uuid, %s, %s::uuid, %s, %s, %s, %s, %s) "
        "RETURNING id::text, material_category_id::text, material_subcategory_id::text, "
        "grade_id::text, city, state, observed_price_per_kg, currency, buyer_type, source, "
        "verification_status, weight_kg, transport_cost, observed_at",
        (
            body.material_category_id,
            body.material_subcategory_id,
            body.grade_id,
            location,
            body.city,
            body.state,
            body.observed_price_per_kg,
            body.currency,
            body.buyer_type,
            body.buyer_organization_id,
            body.source,
            principal.user_id,
            body.weight_kg,
            body.transport_cost,
            verification_status,
            observed_at,
            body.notes,
        ),
    )
    row = await cur.fetchone()
    await record_audit(
        conn,
        action="price.observed",
        actor_user_id=principal.user_id,
        entity_type="price_observation",
        entity_id=row[0],
    )
    return _obs_out(row)


@router.get("/pricing/estimate", response_model=PricingEstimateOut)
async def estimate(
    material_category_id: str,
    grade_id: str | None = None,
    city: str | None = None,
    days: int = Query(30, ge=1, le=365),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> PricingEstimateOut:
    params = (material_category_id, grade_id, grade_id, city, city, days)

    s_cur = await conn.execute(
        "SELECT count(*)::int, "
        "count(*) FILTER (WHERE verification_status = 'verified')::int, "
        "avg(observed_price_per_kg), min(observed_price_per_kg), max(observed_price_per_kg), "
        "avg(observed_price_per_kg) FILTER (WHERE verification_status = 'verified') "
        "FROM price_observations "
        "WHERE material_category_id = %s::uuid "
        "AND (%s::uuid IS NULL OR grade_id = %s::uuid) "
        "AND (%s::text IS NULL OR city = %s::text) "
        "AND observed_at >= now() - make_interval(days => %s)",
        params,
    )
    s = await s_cur.fetchone()

    o_cur = await conn.execute(
        "SELECT id::text, material_category_id::text, material_subcategory_id::text, "
        "grade_id::text, city, state, observed_price_per_kg, currency, buyer_type, source, "
        "verification_status, weight_kg, transport_cost, observed_at "
        "FROM price_observations "
        "WHERE material_category_id = %s::uuid "
        "AND (%s::uuid IS NULL OR grade_id = %s::uuid) "
        "AND (%s::text IS NULL OR city = %s::text) "
        "AND observed_at >= now() - make_interval(days => %s) "
        "ORDER BY observed_at DESC LIMIT 20",
        params,
    )
    observations = [_obs_out(r) for r in await o_cur.fetchall()]

    summary = PricingSummary(
        sample_count=s[0],
        verified_count=s[1],
        average_price_per_kg=float(s[2]) if s[2] is not None else None,
        min_price_per_kg=float(s[3]) if s[3] is not None else None,
        max_price_per_kg=float(s[4]) if s[4] is not None else None,
        verified_average_price_per_kg=float(s[5]) if s[5] is not None else None,
    )
    return PricingEstimateOut(
        material_category_id=material_category_id,
        currency="INR",
        summary=summary,
        observations=observations,
    )
