# Database Design

> Phase 1 deliverable. Describes the PostgreSQL + PostGIS schema, conventions,
> seed data, and how migrations are run. The schema is **implemented and
> verified** against the live Supabase project as of 2026-09-26.

## 1. Overview

- **Engine**: Supabase PostgreSQL (PostGIS enabled).
- **Migration files**: `backend/migrations/*.sql`, applied in filename order.
- **Runner**: `backend/migrations/run.js` (Node + `pg`) — chosen because the
  local machine has Node but no working Python. Recorded as ADR-0010.
- **Tracking table**: `schema_migrations (version, applied_at)`.

Run migrations:

```bash
node backend/migrations/run.js   # reads DATABASE_URL from .env
```

## 2. Conventions

- **Primary keys**: `uuid DEFAULT gen_random_uuid()`. Client-created entities
  (`lots`, `lot_items`, `material_images`, `weights`, `payments`,
  `transactions`) can be generated offline and remain collision-free on sync.
  (ADR-0011.)
- **Timestamps**: every mutable table carries `created_at` / `updated_at`
  (`timestamptz`), with `updated_at` kept fresh by a `set_updated_at()` trigger.
- **Enums**: modeled as `text` + `CHECK` constraints (not native enums), for
  easier migration and extension.
- **Foreign keys**: `ON DELETE CASCADE` for owned children, `ON DELETE SET NULL`
  for reference/lookup columns that should not cascade.
- **Media**: images live in Cloudinary; PostgreSQL stores only `cloudinary_public_id`
  / `cloudinary_url` + metadata (`material_images`).
- **Geospatial**: `geography(Point, 4326)` for points; `geography(Polygon, 4326)`
  for service-area polygons.

## 3. Entity catalog

### Identity & organization
- `organizations` — base legal/operational entity (platform, aggregator,
  recycler, dismantler, collector_group).
- `users` — login identity; optional `organization_id`.
- `roles` — the six roles (seeded).
- `user_roles` — role assignment, optionally scoped to an organization.
  Uniqueness handled with two partial unique indexes (with/without org).

### Collector side
- `collectors` — collector profile (`picker` | `kabadiwala`), linked to a user
  and optionally an organization.

### Recycler side
- `recycler_organizations` — recycler extension of `organizations` (GSTIN, reg no).
- `recycler_facilities` — physical facility with `location geography(Point,4326)`
  and a GiST index for nearby search.
- `recycler_authorizations` — authorization number, authority, type, issue/expiry,
  verification source/date, and `status` (`verified|pending|expiring|expired|suspended`).
- `recycler_material_acceptance` — which materials a recycler accepts.
- `recycler_service_areas` — radius (`radius_km`, `center`) and/or polygon (`area`).

### Taxonomy (backend) + collector mapping
- `material_categories` — detailed backend taxonomy, split by `kind`
  (`equipment` | `recovered_material`). This is the equipment/recovered-material
  separation required by FR-UX-03.
- `material_subcategories` — per-category detail.
- `material_grades`, `material_conditions`, `material_hazards` — lookups.
- `material_hazard_links` — category → hazard association.
- `collector_categories` — the 14 simple collector-facing labels.
- `collector_category_mappings` — collector category → backend category(ies).
- `translations` — generic i18n store `(entity_type, entity_id, field, locale)`.

### Lots & media
- `lots` — a grouping of items, with `idempotency_key` for sync.
- `lot_items` — items within a lot; carries both collector-facing and backend
  category references, `kind`, declared weight, condition.
- `material_images` — Cloudinary references + image metadata.

### Pricing
- `price_observations` — contextual, provenance-backed price points (source,
  source_user, buyer, grade, location, weight, transport, verification_status).
- `price_history` — derived aggregate (period averages), computed, not hand-set.
- `recycler_quotes` — quote on a lot with status and validity.

### Matching & transactions
- `matches` — lot ↔ recycler with `score`, `match_reason` (jsonb factors),
  distance, transport cost, expected net earnings.
- `transactions` — lifecycle status machine (see §4).
- `transaction_events` — immutable status-change audit trail.
- `weights` — `weight_type` (`declared|pickup|final`).
- `handover_records` — digital handover between parties.

### Payments
- `payments` — `method` (`cash|upi|bank_transfer`), status, reference.
- `payment_confirmations` — confirmation trail.

### Disputes
- `disputes` — reason, status, resolution.
- `dispute_events` — dispute history.

### AI
- `ai_models` — pluggable provider/model registry.
- `ai_decisions` — prediction + confidence + quality flags (advisory only).
- `ai_corrections` — human corrections, `is_training_candidate = true` (never
  auto-ground-truth).

### Operations
- `audit_events` — before/after JSON audit trail.
- `notifications` — user notifications.
- `sync_operations` — idempotency ledger for offline sync.

## 4. Transaction lifecycle

`transactions.status` is constrained to the approved sequence:

```
LOT_CREATED -> CLASSIFIED -> QUOTED -> QUOTE_ACCEPTED
  -> PICKUP_OR_DELIVERY -> WEIGHT_VERIFIED -> HANDOVER_CONFIRMED
  -> PAYMENT_RECORDED -> COMPLETED
```

State transitions are captured in `transaction_events` (from_status/to_status).
The enforcement of *legal* transitions (e.g. no jump from `LOT_CREATED` to
`COMPLETED`) is backend logic in Phase 5; the schema stores the status and the
event trail.

## 5. Seed data

| Table | Count | Notes |
| ----- | ----- | ----- |
| `roles` | 6 | picker, kabadiwala, aggregator, recycler, dismantler, platform_admin |
| `collector_categories` | 14 | the approved simple labels |
| `material_categories` | 22 | 8 equipment + 14 recovered_material |
| `material_subcategories` | 17 | representative subset |
| `material_grades` | 5 | A, B, C, Mixed, Low |
| `material_conditions` | 5 | new, used, damaged, mixed, unknown |
| `material_hazards` | 6 | lithium, CRT lead, mercury, lead-acid, FR, capacitors |
| `material_hazard_links` | 6 | category → hazard associations |
| `collector_category_mappings` | 19 | collector → backend mapping |
| `translations` | 14 | Hindi collector-category labels (i18n demonstration) |

The taxonomy is **reference/demo data**, not exhaustive. Remaining locales
(`mr`, `ta`, `te`, `ml`, `kn`, `bn`) are Phase 7 content work — the `translations`
table is ready for them.

## 6. Security notes

- **RLS**: not enabled on these tables. The backend is authoritative and
  connects with elevated credentials (service role / direct DB); organization
  isolation is enforced at the application layer (Phase 2). (ADR-0013.)
- **Secrets**: `DATABASE_URL` lives only in git-ignored `.env`.
- **Aadhaar**: no Aadhaar column exists (FR-SEC-10).

## 7. Validation performed

Executed against the live Supabase project (2026-09-26):

- `postgis` extension enabled.
- 41/41 expected tables present (plus PostGIS `spatial_ref_sys`).
- All seed counts match the values above.
- `geography` columns present on `recycler_facilities.location`,
  `recycler_service_areas.center/area`, `lots.pickup_location`,
  `price_observations.location`.
- PostGIS distance round-trip returns ~1106 m for 0.01° latitude (correct).

## 8. Open items / future work

- Legal transition enforcement for `transactions.status` (Phase 5).
- Full 8-language translation content (Phase 7).
- `price_history` derivation job (Phase 4, via Redis/worker).
- RLS policy if a direct client-facing DB path is ever introduced (currently
  not planned — all access goes through the backend).
