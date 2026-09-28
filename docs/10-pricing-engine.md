# Pricing Engine

> Phase deliverable. Price is **contextual** — there is no single global material
> price. Prices are derived from stored observations and quotes that carry full
> provenance, and every computed number is an estimate, never a guarantee.

---

## 1. Principle

No hard-coded rates (e.g. "PCB = ₹180/kg"). Value depends on material, subtype,
grade, location, time, source, buyer, unit, verification, and confidence. The
system aggregates observations transparently and returns `null` when it has no
data rather than inventing a number (FR-PRICE-01).

## 2. Price observation model

Each `PriceObservation` captures:

| Field | Meaning |
| ----- | ------- |
| material_category_id | material (required) |
| material_subcategory_id | subtype |
| grade_id | grade (A/B/C/… ) |
| latitude / longitude / city / state | location |
| observed_at | timestamp |
| source | `collector_entry` / `recycler_quote` / `market` / `verification` |
| buyer_type / buyer_organization_id | buyer |
| unit | `per_kg` (canonical) |
| currency | `INR` |
| verification_status | `unverified` / `verified` |
| confidence | 0..1 |

Migration `0017_pricing_matching.sql` (additive) adds `unit` and `confidence` to
`price_observations`.

## 3. Four price kinds

The system clearly distinguishes four price kinds (always labelled):

| Kind | Source | Meaning |
| ---- | ------ | ------- |
| **MARKET OBSERVATION** | `source = market` / `verification` | an observed market price |
| **RECYCLER QUOTE** | `source = recycler_quote` | a recycler's quote |
| **EXISTING BUYER PRICE** | `source = collector_entry` | what the collector's existing buyer pays |
| **INDICATIVE VALUE** | computed | the estimate produced from the above (never guaranteed) |

## 4. Capabilities

| Capability | Service method | Notes |
| ---------- | -------------- | ----- |
| Price observations | `record(observation)` | validates `price_per_kg > 0` |
| Historical price | `historical(material, days)` | median/min/max/count/verified count |
| Price range | `price_range(material, days)` | `(min, max)` or `None` |
| Location-aware lookup | `location_aware(material, lat, lng, radius)` | distance-weighted average (PostGIS) |
| Existing buyer comparison | `compare_existing_buyers(material)` | ranked by price, descending |
| Recycler quote comparison | `compare_recycler_quotes(material)` | ranked by price, descending |

Location-aware lookup uses PostGIS `ST_DWithin` + `ST_Distance` (the in-memory
repository uses the haversine formula for tests).

## 5. Indicative valuation

The **INDICATIVE VALUE** combines material classification, weight, location,
price observations, recycler quotes, and transport cost:

```
indicative_value = weight_kg × median(price_per_kg) − transport_cost
```

It is always labelled `"INDICATIVE VALUE"`, carries a value range and its basis,
and returns `null` with no data. (Implemented in `app/services/valuation.py`.)

## 6. Relationship to matching

Pricing feeds matching: a recycler's **quoted price** and the resulting
**expected net earnings** are two of the nine matching factors, but they are
deliberately a minority of the composite score so matching never ranks by gross
price alone (see [matching](#matching) and `app/services/matching.py`).

## 7. Implementation status

- **Implemented & unit-tested**: `PricingService` (record, historical, range,
  location-aware, buyer/quote comparison) and the price-kind labels.
- **Persistence**: `InMemoryPriceObservationRepository` (tested) and
  `PostgresPriceObservationRepository` (PostGIS; requires migration `0017`).
- **Not yet wired**: the HTTP endpoints still live in the legacy
  `app/routers/pricing.py` and will migrate onto this service layer.

## 8. Validation

`pytest tests/unit/test_pricing.py` covers aggregation (median/min/max), empty
ranges, location-aware weighting (far observations excluded), and buyer/quote
comparison ranking + kind labels.
