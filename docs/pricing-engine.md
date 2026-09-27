# Pricing Engine

> Phase 4 deliverable. Price is **contextual** — there is no single hard-coded
> price per material.

## 1. Principle

No hard-coded rates (e.g. "PCB = ₹180/kg"). Price is derived from stored
**observations** that carry provenance. Collector-entered buyer prices are
observations, not authoritative market prices.

## 2. Price observations

Each `price_observations` row captures: material category/subcategory, grade,
location (PostGIS point + city/state), `observed_price_per_kg`, currency,
buyer type/organization, `source` (`collector_entry | recycler_quote | market |
verification`), `source_user_id`, weight, transport cost, `verification_status`,
and `observed_at`.

- `source = verification` → `verified`.
- all other sources default to `unverified`.

## 3. Estimate

`GET /api/v1/pricing/estimate?material_category_id=&grade_id=&city=&days=` returns
an aggregate over matching observations:

- `sample_count`, `verified_count`
- `average_price_per_kg`, `min`, `max`
- `verified_average_price_per_kg`
- the recent observations (provenance included)

If no observations exist, the aggregates are `null` — the system never invents a
price.

## 4. Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/price-observations` | record an observation (any authenticated user) |
| GET | `/api/v1/pricing/estimate` | contextual aggregate estimate |

## 5. Open items

- `price_history` (period aggregates) derivation via Redis/worker is not yet
  scheduled.
- Weighted/geographic aggregation (e.g. nearby-first) and anomaly detection are
  future refinements.
