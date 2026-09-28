# Recycler Verification

> Phase deliverable. A recycler is never auto-verified. Eligibility for matching
> is derived from explicit authorization data; expired or suspended
> authorizations exclude the recycler.

---

## 1. Model

| Entity | Purpose |
| ------ | ------- |
| `recycler_organizations` | recycler extension of an organization (GSTIN, registration, pickup capability) |
| `recycler_facilities` | physical facility with `geography(Point, 4326)` |
| `recycler_authorizations` | authorization number, authority, type, issue/expiry, verification source/date, status |
| `recycler_material_acceptance` | which materials the recycler accepts |
| `recycler_service_areas` | service radius and/or polygon |

Migration `0017_pricing_matching.sql` (additive) adds `pickup_available` to
`recycler_organizations`.

## 2. Effective verification

`app/models/recycler.py:effective_authorization()` derives the **effective**
status and an `authorized` boolean:

- `verified` **and** not expired → `authorized = true`.
- `suspended` (any) → `suspended`, `authorized = false`.
- `verified` but expired → `expired`, `authorized = false`.
- no / pending authorization → `pending`, `authorized = false`.

**Expired or suspended authorizations exclude the recycler from matching**
(FR-VERIF-01/FR-VERIF-04).

## 3. Matching integration

`app/services/matching.py` gates candidates on:

1. **Authorization** — `authorized` must be true.
2. **Material acceptance** — if the recycler declares accepted materials, the
   lot's materials must overlap.
3. **Service area** — if a service radius is set, the lot must be within it.

Eligible candidates are then ranked by a composite score (see
[pricing-engine.md](pricing-engine.md) §6) that includes distance, pickup,
transport cost, quoted price, and historical reliability — never gross price
alone.

## 4. PostGIS distance

`app/repositories/recycler.py:PostgresRecyclerRepository` computes facility
distance with `ST_Distance` / `ST_DWithin` on `recycler_facilities.location`
(`geography(Point, 4326)`), and derives `authorized` via
`effective_authorization()`.

## 5. Implementation status

- **Implemented & unit-tested**: `effective_authorization` (verified / expired /
  suspended / pending) and `MatchingService` gates + composite scoring.
- **Persistence**: `PostgresRecyclerRepository` (PostGIS; requires migration
  `0017` + a live database).
- **Not yet wired**: the HTTP endpoints still live in the legacy
  `app/routers/recyclers.py` / `app/routers/matching.py` and will migrate onto
  this service layer.

## 6. Validation

`pytest tests/unit/test_recycler.py` and `test_matching.py` cover authorized,
expired, suspended, unsupported material, outside/inside service area, transport
cost, quote value, and net-earnings factors.
