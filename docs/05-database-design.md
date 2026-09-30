# Kabadi Mitra — Production Database Design

> Phase 3 deliverable. Production-grade PostgreSQL + PostGIS schema design for
> Kabadi Mitra, mapped to the Phase 2
> [Requirement Traceability Matrix](requirement-traceability-matrix.md).
>
> **Status**: the schema below is **implemented** in `backend/migrations/*.sql`
> (19 files, 41 tables). This
> document is the design-of-record that the migrations realize. **No migration
> SQL is created or modified in this phase** — the existing migrations are
> preserved as-is, and any schema change proposed below is recorded as a
> reviewed recommendation, not applied.

---

## 1. Scope & principles

The database is the authoritative relational core. It is accessed only through
the FastAPI backend (ADR-0013); mobile/web clients never connect to Postgres
directly.

Design principles (each traced to a requirement):

| Principle | RTM |
| --------- | --- |
| Backend-authoritative; DB is the source of truth, not the client | FR-043, TR-009 |
| AI is advisory — predictions are stored, never applied as fact | FR-021, FR-011 (AT-011) |
| No hard-coded prices; price is observation-driven | FR-022, FR-023 |
| Recyclers are never auto-verified; expiry-aware | FR-026, FR-028, FR-029 |
| Equipment vs recovered material tracked separately | FR-009 |
| No large media in Postgres; Cloudinary refs only | FR-045, FR-046 |
| Offline-safe: UUID PKs + idempotency keys | FR-044, TR-010, TR-016 |
| No Aadhaar; data minimization | FR-060, FR-061 |
| Env-only secrets; no secrets in schema | FR-059 |

---

## 2. ERD description

Nineteen domains grouped into five clusters. The diagram below shows the
relationship **direction** (parent → child) and cardinality; exact foreign keys
are in §5.

```
                        ┌─────────────────────────────────────────────┐
                        │  IDENTITY & ORGANIZATION                     │
                        │  organizations (1) ──< users (n)             │
                        │  organizations (1) ──< user_roles (n)        │
                        │  roles (1) ──< user_roles (n)                │
                        └───────┬─────────────────────────┬───────────┘
                                │                         │
                    ┌───────────▼──────────┐   ┌──────────▼───────────┐
                    │  COLLECTOR           │   │  RECYCLER             │
                    │  collectors          │   │  recycler_organizations│
                    │   (picker/kabadiwala)│   │   ──< facilities       │
                    └───────────┬──────────┘   │   ──< authorizations   │
                                │              │   ──< acceptance       │
                                │              │   ──< service_areas    │
                                │              └──────────┬────────────┘
                                │                         │
        ┌───────────────────────┼─────────────────────────┤
        │                       │                         │
┌───────▼─────────┐   ┌─────────▼──────────┐   ┌─────────▼──────────────┐
│  TAXONOMY        │   │  CAPTURE & MEDIA    │   │  PRICING & QUOTES      │
│  material_*      │   │  lots (1)──<items   │   │  price_observations    │
│  collector_*     │   │  lots ──< images    │   │  price_history         │
│  translations    │   │  items ──< images   │   │  recycler_quotes       │
└───────┬─────────┘   └─────────┬──────────┘   └────────────┬───────────┘
        │                       │                           │
        │            ┌──────────▼──────────┐                │
        └───────────►│  MATCHING           │◄───────────────┘
                     │  matches (lot↔recycler)│
                     └──────────┬──────────┘
                                │
                ┌───────────────▼───────────────────────────────┐
                │  TRANSACTION LIFECYCLE                        │
                │  transactions ──< transaction_events          │
                │  transactions ──< weights                     │
                │  transactions ──< handover_records            │
                │  transactions ──< payments ──< confirmations  │
                │  transactions ──< disputes ──< dispute_events │
                └──────────────────┬────────────────────────────┘
                                   │
        ┌──────────────┬───────────┴───────────┬──────────────────┐
        │              │                       │                  │
┌───────▼──────┐ ┌─────▼───────┐      ┌────────▼────────┐  ┌──────▼─────────┐
│  AI           │ │  AUDIT       │      │  OFFLINE SYNC   │  │  NOTIFICATIONS │
│  ai_models    │ │  audit_events│      │  sync_operations│  │  notifications │
│  ai_decisions │ │              │      │                 │  │                │
│  ai_corrections│ └─────────────┘      └─────────────────┘  └────────────────┘
└───────────────┘
```

**Relationship summary**

- **Identity/org** is the hub: `organizations` → `users` → (`user_roles`, `collectors`).
- **Collector** owns capture (`lots`), and lots drive matching, transactions, and pricing.
- **Recycler** owns facilities/authorizations/acceptance/service areas, quotes, and the "sell side" of a transaction.
- **Taxonomy** is reference data referenced by lots/items, pricing, quotes, AI, and recycler acceptance.
- **AI / audit / sync / notifications** are cross-cutting, attached to the entities they describe.

---

## 3. Schema conventions

| Concern | Convention | RTM |
| ------- | ---------- | --- |
| Primary key | `uuid PRIMARY KEY DEFAULT gen_random_uuid()` | TR-010, ADR-0011 |
| Timestamps | `created_at` / `updated_at timestamptz`; `updated_at` kept fresh by `set_updated_at()` trigger | — |
| Enums | `text` + `CHECK` (not native enums) for easy migration | — |
| Foreign keys | `ON DELETE CASCADE` for owned children; `ON DELETE SET NULL` for reference/lookup | — |
| Geography | `geography(Point, 4326)` / `geography(Polygon, 4326)` + GiST index | FR-047, FR-048 |
| Media | Cloudinary `public_id`/`url` only — no `bytea`/`blob` | FR-045 |
| Secrets | none in schema (env-only) | FR-059 |

---

## 4. Cross-cutting strategies

### 4.1 RLS / security strategy

- **Current state**: Row Level Security is **disabled** on application tables
  (ADR-0013). The backend is the sole data-access layer and connects with
  elevated (service-role) credentials, which would bypass RLS anyway.
- **Authorization boundary**: enforced in the backend via `require_role`
  (RBAC, FR-002) and collector/ownership checks (FR-054). Organization isolation
  (`org_scope`, FR-003) is **defined and unit-tested but not yet applied to all
  org-scoped queries** — see §9 risk R-DB-1.
- **Defense-in-depth (future, not applied now)**: if a direct client-facing DB
  path is ever introduced, enable RLS with policies scoped by `organization_id`,
  and keep the backend on a service-role that bypasses RLS. This would be a new
  decision (successor to ADR-0013), not a silent change.
- **Column-level minimization**: no Aadhaar column (FR-061); `users.password_hash`
  is unused (identity is Supabase Auth, ADR-0015); auto-provisioned users store
  only `id` + `email`/`phone` (FR-060). Sensitive recycler fields (`gstin`,
  `registration_number`, `authorization_number`) are read only by admin/recycler
  roles (FR-027).

### 4.2 Audit strategy

- `audit_events` is the append-only trail (FR-057): actor, organization, action,
  entity type/id, `before`/`after` JSON, and `ip_address`.
- Wired to: lot/item creation, AI classify/confirm/correct, price observation,
  recycler onboarding, transaction creation, status transitions, weight, and
  payment. (FR-035, FR-051.)
- `transaction_events` is the **transaction-specific** immutable status-change
  trail (from/to status + actor), distinct from the generic audit trail (FR-035).
- Audit rows are **never updated or soft-deleted**.

### 4.3 Soft-delete strategy

The schema uses **logical deactivation via state columns** rather than a
universal `deleted_at` timestamp, because most entities need an auditable
lifecycle that a boolean cannot express.

| Mechanism | Tables | RTM |
| --------- | ------ | --- |
| `status` (`active`/`inactive`/`suspended`) | `organizations`, `users`, `collectors` | FR-060 |
| `status` (domain lifecycle) | `recycler_authorizations`, `matches`, `transactions`, `payments`, `disputes`, `recycler_quotes` | FR-028, FR-034, FR-038, FR-062, FR-032 |
| `is_active` flag | taxonomy tables, `recycler_facilities`, `recycler_service_areas`, `ai_models` | FR-008, FR-050 |

Append-only tables (`audit_events`, `transaction_events`, `dispute_events`,
`sync_operations`, `price_history`) are **never soft-deleted**.

> **Recommendation (reviewed, not applied)**: hard deletes are currently
> possible via `ON DELETE CASCADE` on financial/transactional children (e.g.
> deleting a `lot` cascades to `transactions` → `weights`/`payments`). For
> production, change `lots → transactions` and `transactions → payments/weights`
> to `RESTRICT` (or force soft-close via `status`) so money movements can never
> be silently destroyed. Tracked as open item O-DB-1.

### 4.4 Versioning strategy

- **Schema versioning**: `schema_migrations(version, applied_at)` records each
  applied file (TR-013).
- **Row versioning**: mutable tables carry `created_at`/`updated_at` with an
  automatic `set_updated_at()` trigger (0001). There is **no per-row temporal
  (bitemporal) versioning**.
- **State-change history**: important transitions are versioned through
  `audit_events.before/after` (JSON) and `transaction_events.from_status/to_status`
  rather than duplicating full rows. This is the intended, lightweight history
  model for this product.

### 4.5 Idempotency strategy

| Layer | Mechanism | RTM |
| ----- | --------- | --- |
| Per-entity | `idempotency_key TEXT UNIQUE` on `lots`, `transactions`, `payments` | FR-044 |
| Offline sync | `sync_operations` ledger — `idempotency_key` UNIQUE, records `entity_id` + `status` (`pending`/`applied`/`failed`) for replay | FR-044, FR-042 |
| Key format | `KC-<ENTITY>-<YYMMDD>-<NNNNNN>` generated client-side | TR-016 |

A repeated sync key returns the original `entity_id` with `status = replayed`
(never a duplicate); the HTTP `Idempotency-Key` middleware returns `409` on
duplicate direct mutations.

### 4.6 Migration strategy

- **Versioned, forward-only**: `backend/migrations/*.sql`, applied in filename
  order (`0001…0019`), each wrapped in a transaction by `run.js`.
- **Tracking**: `schema_migrations` records each applied `version`.
- **Idempotent DDL**: `CREATE … IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`,
  and `ON CONFLICT … DO NOTHING` for seeds.
- **Rules**: never edit an applied migration — apply an additive new migration;
  keep DDL + seed separated; run out-of-band via `node backend/migrations/run.js`
  (reads `DATABASE_URL`) or the Supabase SQL editor.
- **Preservation**: the 19 existing migration files are **preserved unchanged**
  (non-destructive requirement). PostGIS is enabled by `0001_extensions.sql`.

### 4.7 PostGIS usage

| Field | Type | Table | Purpose | RTM |
| ----- | ---- | ----- | ------- | --- |
| `location` | `geography(Point, 4326)` | `recycler_facilities` | facility point for nearby search | FR-048, FR-049 |
| `center` / `area` | `geography(Point, 4326)` / `geography(Polygon, 4326)` | `recycler_service_areas` | service radius / polygon | FR-027 (future FR-030) |
| `pickup_location` | `geography(Point, 4326)` | `lots` | collector pickup point | FR-010, FR-030 |
| `location` | `geography(Point, 4326)` | `price_observations` | geographic price provenance | FR-023 |

GiST index: `idx_recycler_facilities_location` on `recycler_facilities.location`.
Queries use `ST_DWithin` (nearby search, FR-049) and `ST_Distance` (matching
distance, FR-030).

---

## 5. Table catalog

Each table lists purpose, columns, relationships, constraints, indexes, security,
and RTM requirement IDs. DB-xxx IDs match the Phase 2 catalog.

### 5.1 Identity & organization

#### organizations — DB-001
- **Purpose**: base legal/operational entity (platform, aggregator, recycler, dismantler, collector_group).
- **RTM**: FR-003, FR-027, UR-005, UR-007, UR-010.
- **Columns**: `id uuid PK`, `name text NOT NULL`, `organization_type text CHECK IN ('platform','aggregator','recycler','dismantler','collector_group')`, `status text DEFAULT 'active' CHECK IN ('active','inactive','suspended')`, `address_line`, `city`, `state`, `postal_code`, `country text DEFAULT 'IN'`, `contact_email`, `contact_phone`, `created_at`, `updated_at`.
- **Relationships**: 1→N `users`, `user_roles` (org-scoped roles), `recycler_organizations` (1:1).
- **Constraints**: `organization_type` CHECK; `status` CHECK.
- **Indexes**: none beyond PK (lookup by type is low-cardinality; add a partial index if filtered by `status` at scale).
- **Security**: soft-delete via `status`; contact fields minimized.

#### users — DB-002
- **Purpose**: login identity mirroring a Supabase Auth user by UUID.
- **RTM**: FR-053, FR-060, FR-061.
- **Columns**: `id uuid PK`, `organization_id uuid FK organizations ON DELETE SET NULL`, `email text UNIQUE`, `phone text`, `password_hash text` (unused — Supabase Auth), `full_name`, `preferred_locale text DEFAULT 'en'`, `status text DEFAULT 'active' CHECK ('active','inactive','suspended')`, `created_at`, `updated_at`.
- **Relationships**: N→1 `organizations`; 1→N `user_roles`, `collectors`, `audit_events.actor`.
- **Constraints**: `email UNIQUE`; `status` CHECK.
- **Indexes**: `email` unique index (from UNIQUE); consider a `(organization_id)` index for org-scoped reads.
- **Security**: auto-provisioned minimal (id + email/phone); no Aadhaar (FR-061); `password_hash` unused (ADR-0015).

#### roles — DB-003
- **Purpose**: six fixed roles.
- **RTM**: FR-001.
- **Columns**: `id smallint GENERATED ALWAYS AS IDENTITY PK`, `code text NOT NULL UNIQUE`, `name text NOT NULL`, `description text`, `created_at`.
- **Relationships**: 1→N `user_roles`.
- **Constraints**: `code UNIQUE`.
- **Security**: read-only seed; write access is admin-only.

#### user_roles — DB-004
- **Purpose**: role assignment, optionally scoped to an organization.
- **RTM**: FR-002, FR-004, FR-054.
- **Columns**: `id uuid PK`, `user_id uuid NOT NULL FK users ON DELETE CASCADE`, `role_id smallint NOT NULL FK roles ON DELETE CASCADE`, `organization_id uuid FK organizations ON DELETE CASCADE`, `granted_at timestamptz DEFAULT now()`.
- **Constraints**: two partial unique indexes — `uq_user_roles_org (user_id, role_id, organization_id) WHERE organization_id IS NOT NULL`, and `uq_user_roles_no_org (user_id, role_id) WHERE organization_id IS NULL` — so a platform-wide role and org-scoped roles coexist.
- **Indexes**: the two partial unique indexes.
- **Security**: org-scoped role assignment; backend loads these into the principal.

### 5.2 Collectors

#### collectors — DB-005
- **Purpose**: collector profile (`picker` | `kabadiwala`), linked to a user and optionally an org.
- **RTM**: UR-001..UR-006, FR-010.
- **Columns**: `id uuid PK`, `user_id uuid FK users ON DELETE SET NULL`, `organization_id uuid FK organizations ON DELETE SET NULL`, `collector_type text NOT NULL CHECK ('picker','kabadiwala')`, `display_name text NOT NULL`, `phone`, `city`, `state`, `postal_code`, `primary_language text DEFAULT 'hi'`, `status text DEFAULT 'active' CHECK ('active','inactive','suspended')`, `created_at`, `updated_at`.
- **Relationships**: N→1 `users`, N→1 `organizations`; 1→N `lots`.
- **Constraints**: `collector_type` and `status` CHECK.
- **Indexes**: `(user_id)` lookup index (implicit via FK path is not automatic — add for `require_collector`). Recommend `CREATE INDEX idx_collectors_user ON collectors(user_id)`.
- **Security**: collector ownership of lots is enforced by matching `lots.collector_id` (FR-054).

### 5.3 Recyclers

#### recycler_organizations — DB-006
- **Purpose**: recycler extension of an organization (GSTIN, registration).
- **RTM**: FR-026, FR-027.
- **Columns**: `id uuid PK`, `organization_id uuid NOT NULL UNIQUE FK organizations ON DELETE CASCADE`, `gstin text`, `registration_number text`, `created_at`, `updated_at`.
- **Relationships**: 1:1 `organizations`; 1→N `recycler_facilities`, `recycler_authorizations`, `recycler_material_acceptance`, `recycler_service_areas`, `recycler_quotes`, `matches`, `transactions`.
- **Constraints**: `organization_id UNIQUE`.
- **Security**: `gstin`/`registration_number` are admin/recycler-only (FR-027); not returned to collectors.

#### recycler_facilities — DB-007
- **Purpose**: physical facility with a geospatial point.
- **RTM**: FR-027, FR-048, FR-049.
- **Columns**: `id uuid PK`, `recycler_organization_id uuid NOT NULL FK recycler_organizations ON DELETE CASCADE`, `name text NOT NULL`, `address_line`, `city`, `state`, `postal_code`, `location geography(Point,4326)`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.
- **PostGIS**: `location geography(Point, 4326)`.
- **Indexes**: `idx_recycler_facilities_location` GiST on `location`.
- **Security**: facility PII (address) is admin/recycler-only.

#### recycler_authorizations — DB-008
- **Purpose**: recycler authorization/license with expiry and verification status.
- **RTM**: FR-026, FR-027, FR-028, FR-029.
- **Columns**: `id uuid PK`, `recycler_organization_id uuid NOT NULL FK recycler_organizations ON DELETE CASCADE`, `authorization_number text NOT NULL`, `issuing_authority text`, `authorization_type text`, `issue_date date`, `expiry_date date`, `verification_source text`, `verification_date timestamptz`, `status text NOT NULL DEFAULT 'pending' CHECK ('verified','pending','expiring','expired','suspended')`, `document_url text`, `notes text`, `created_at`, `updated_at`.
- **Constraints**: `status` CHECK (five statuses, FR-028).
- **Indexes**: `(recycler_organization_id)` — consider `(recycler_organization_id, status, expiry_date)` for the verification/matching join.
- **Security**: verification is derived expiry-aware in the backend (FR-029); expired authorizations are structurally excluded from matching.

#### recycler_material_acceptance — DB-009
- **Purpose**: which material categories a recycler accepts.
- **RTM**: FR-027, FR-030.
- **Columns**: `id uuid PK`, `recycler_organization_id uuid NOT NULL FK recycler_organizations ON DELETE CASCADE`, `material_category_id uuid NOT NULL FK material_categories ON DELETE CASCADE`, `material_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `is_accepted boolean DEFAULT true`, `notes`, `created_at`, `updated_at`.
- **Constraints**: `UNIQUE (recycler_organization_id, material_category_id, material_subcategory_id)`.
- **Security**: drives matching acceptance overlap (FR-030).

#### recycler_service_areas — DB-010
- **Purpose**: service radius and/or polygon.
- **RTM**: FR-027; FR-030 (future — not yet consumed by matching).
- **Columns**: `id uuid PK`, `recycler_organization_id uuid NOT NULL FK recycler_organizations ON DELETE CASCADE`, `name text NOT NULL`, `radius_km numeric DEFAULT 0`, `center geography(Point,4326)`, `area geography(Polygon,4326)`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.
- **PostGIS**: `center geography(Point,4326)`, `area geography(Polygon,4326)`.
- **Security**: not yet used for matching (gap O-DB-2).

### 5.4 Material taxonomy

#### material_categories — DB-011
- **Purpose**: detailed backend taxonomy, split by `kind` (equipment / recovered_material).
- **RTM**: FR-009, FR-012.
- **Columns**: `id uuid PK`, `code text NOT NULL UNIQUE`, `name text NOT NULL`, `kind text NOT NULL CHECK ('equipment','recovered_material')`, `parent_id uuid FK material_categories ON DELETE SET NULL` (self-reference), `sort_order integer DEFAULT 0`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.
- **Constraints**: `code UNIQUE`, `kind` CHECK, self-FK `parent_id`.
- **Security**: `is_active` soft-delete; reference data.

#### material_subcategories — DB-012
- **Purpose**: per-category detail.
- **RTM**: FR-012, FR-023.
- **Columns**: `id uuid PK`, `material_category_id uuid NOT NULL FK material_categories ON DELETE CASCADE`, `code text NOT NULL`, `name text NOT NULL`, `sort_order integer DEFAULT 0`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.
- **Constraints**: `UNIQUE (material_category_id, code)`.

#### material_grades — DB-013
- **Purpose**: grade lookup (A/B/C/Mixed/Low).
- **RTM**: FR-023.
- **Columns**: `id uuid PK`, `code text NOT NULL UNIQUE`, `name text NOT NULL`, `description`, `sort_order integer DEFAULT 0`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.

#### material_conditions — DB-014
- **Purpose**: condition lookup (new/used/damaged/mixed/unknown).
- **RTM**: FR-010.
- **Columns**: `id uuid PK`, `code text NOT NULL UNIQUE`, `name text NOT NULL`, `sort_order integer DEFAULT 0`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.

#### material_hazards — DB-015
- **Purpose**: hazard lookup (lithium, lead, mercury, …).
- **RTM**: FR-050.
- **Columns**: `id uuid PK`, `code text NOT NULL UNIQUE`, `name text NOT NULL`, `description`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.

#### material_hazard_links — DB-016
- **Purpose**: category → hazard association (many-to-many).
- **RTM**: FR-050.
- **Columns**: `material_category_id uuid FK material_categories ON DELETE CASCADE`, `material_hazard_id uuid FK material_hazards ON DELETE CASCADE`, `PRIMARY KEY (material_category_id, material_hazard_id)`.
- **Constraints**: composite PK.

#### collector_categories — DB-017
- **Purpose**: the 14 simple collector-facing labels.
- **RTM**: FR-007, FR-008.
- **Columns**: `id uuid PK`, `code text NOT NULL UNIQUE`, `name text NOT NULL`, `sort_order integer DEFAULT 0`, `is_active boolean DEFAULT true`, `created_at`, `updated_at`.

#### collector_category_mappings — DB-018
- **Purpose**: maps a collector category to backend category/subcategory.
- **RTM**: FR-008, FR-009.
- **Columns**: `id uuid PK`, `collector_category_id uuid NOT NULL FK collector_categories ON DELETE CASCADE`, `material_category_id uuid NOT NULL FK material_categories ON DELETE CASCADE`, `material_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `created_at`.
- **Constraints**: `UNIQUE (collector_category_id, material_category_id, material_subcategory_id)`.

#### translations — DB-019
- **Purpose**: generic i18n store.
- **RTM**: FR-005, FR-006.
- **Columns**: `id uuid PK`, `entity_type text NOT NULL`, `entity_id uuid NOT NULL`, `field text NOT NULL`, `locale text NOT NULL`, `value text NOT NULL`, `created_at`, `updated_at`.
- **Constraints**: `UNIQUE (entity_type, entity_id, field, locale)`.
- **Indexes**: unique constraint serves `(entity_type, entity_id, field, locale)` lookups.

### 5.5 Lots & items

#### lots — DB-020
- **Purpose**: a grouping of items (a digital lot).
- **RTM**: FR-010, FR-044.
- **Columns**: `id uuid PK`, `idempotency_key text UNIQUE`, `collector_id uuid NOT NULL FK collectors ON DELETE CASCADE`, `organization_id uuid FK organizations ON DELETE SET NULL`, `status text NOT NULL DEFAULT 'draft' CHECK ('draft','ready','synced','matched','closed')`, `title`, `notes`, `currency text DEFAULT 'INR'`, `pickup_location geography(Point,4326)`, `pickup_address text`, `created_at`, `updated_at`.
- **PostGIS**: `pickup_location geography(Point,4326)`.
- **Constraints**: `idempotency_key UNIQUE`; `status` CHECK.
- **Indexes**: `(collector_id, created_at DESC)` for the collector's lot list.
- **Security**: collector ownership enforced (`lots.collector_id`, FR-054). Note the CASCADE risk (O-DB-1).

#### lot_items — DB-021
- **Purpose**: items within a lot, carrying both collector and backend category refs.
- **RTM**: FR-009, FR-010.
- **Columns**: `id uuid PK`, `lot_id uuid NOT NULL FK lots ON DELETE CASCADE`, `collector_category_id uuid FK collector_categories ON DELETE SET NULL`, `material_category_id uuid FK material_categories ON DELETE SET NULL`, `material_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `kind text CHECK ('equipment','recovered_material')`, `description`, `quantity integer NOT NULL DEFAULT 1`, `declared_weight_kg numeric`, `condition_id uuid FK material_conditions ON DELETE SET NULL`, `classification_source text NOT NULL DEFAULT 'collector' CHECK ('collector','ai','recycler','admin')`, `created_at`, `updated_at`.
- **Constraints**: `kind` CHECK; `classification_source` CHECK (FR-009).
- **Indexes**: `(lot_id)`.

#### material_images — DB-022
- **Purpose**: Cloudinary image references + metadata (no binary).
- **RTM**: FR-011, FR-045, FR-046.
- **Columns**: `id uuid PK`, `lot_item_id uuid FK lot_items ON DELETE CASCADE`, `lot_id uuid FK lots ON DELETE CASCADE`, `collector_id uuid FK collectors ON DELETE SET NULL`, `cloudinary_public_id text`, `cloudinary_url text`, `image_kind text NOT NULL DEFAULT 'capture' CHECK ('capture','quality_check','handover','other')`, `is_primary boolean DEFAULT false`, `mime_type text`, `width integer`, `height integer`, `captured_at timestamptz DEFAULT now()`, `created_at`, `updated_at`.
- **Constraints**: `image_kind` CHECK.
- **Security**: only `cloudinary_public_id`/`cloudinary_url` stored (FR-045); signed upload URL issued by backend (FR-046).

### 5.6 Pricing & quotes

#### price_observations — DB-023
- **Purpose**: contextual, provenance-backed price points.
- **RTM**: FR-022, FR-023, FR-024, FR-025, FR-064.
- **Columns**: `id uuid PK`, `material_category_id uuid NOT NULL FK material_categories ON DELETE CASCADE`, `material_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `grade_id uuid FK material_grades ON DELETE SET NULL`, `location geography(Point,4326)`, `city text`, `state text`, `observed_price_per_kg numeric NOT NULL`, `currency text DEFAULT 'INR'`, `buyer_type text CHECK ('recycler','aggregator','other')`, `buyer_organization_id uuid FK organizations ON DELETE SET NULL`, `source text NOT NULL CHECK ('collector_entry','recycler_quote','market','verification')`, `source_user_id uuid FK users ON DELETE SET NULL`, `weight_kg numeric`, `transport_cost numeric`, `verification_status text NOT NULL DEFAULT 'unverified' CHECK ('unverified','verified')`, `observed_at timestamptz DEFAULT now()`, `notes`, `created_at`, `updated_at`.
- **PostGIS**: `location geography(Point,4326)`.
- **Constraints**: `source` CHECK (FR-024); `verification_status` CHECK (FR-025); `observed_price_per_kg NOT NULL`.
- **Indexes**: `(material_category_id, observed_at DESC)` for estimates; consider a GiST index on `location` for geographic pricing.
- **Security**: collector entries are `unverified`; only `verification` source is `verified` (FR-025).

#### price_history — DB-024
- **Purpose**: derived period aggregates (computed, not hand-set).
- **RTM**: FR-066.
- **Columns**: `id uuid PK`, `material_category_id uuid NOT NULL FK material_categories ON DELETE CASCADE`, `material_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `region text`, `period_start date NOT NULL`, `period_end date NOT NULL`, `average_price_per_kg numeric`, `min_price_per_kg numeric`, `max_price_per_kg numeric`, `sample_count integer DEFAULT 0`, `created_at`.
- **Constraints**: `period_start`/`period_end` NOT NULL.
- **Security**: append-only derived data; populated by a future worker (gap O-DB-3).

#### recycler_quotes — DB-025
- **Purpose**: a recycler's quote on a lot.
- **RTM**: FR-032.
- **Columns**: `id uuid PK`, `recycler_organization_id uuid NOT NULL FK recycler_organizations ON DELETE CASCADE`, `lot_id uuid NOT NULL FK lots ON DELETE CASCADE`, `price_per_kg numeric`, `total_price numeric`, `currency text DEFAULT 'INR'`, `grade_id uuid FK material_grades ON DELETE SET NULL`, `terms text`, `status text NOT NULL DEFAULT 'submitted' CHECK ('draft','submitted','accepted','rejected','expired')`, `valid_until timestamptz`, `created_at`, `updated_at`.
- **Constraints**: `status` CHECK.
- **Security**: schema-ready; no endpoint yet (FR-032 Schema-ready).

### 5.7 Matching

#### matches — DB-026
- **Purpose**: lot ↔ recycler with score and explanatory factors.
- **RTM**: FR-030, FR-031.
- **Columns**: `id uuid PK`, `lot_id uuid NOT NULL FK lots ON DELETE CASCADE`, `recycler_organization_id uuid NOT NULL FK recycler_organizations ON DELETE CASCADE`, `score numeric`, `match_reason jsonb NOT NULL DEFAULT '{}'`, `distance_km numeric`, `transport_cost numeric`, `expected_net_earnings numeric`, `status text NOT NULL DEFAULT 'proposed' CHECK ('proposed','shown','accepted','rejected')`, `created_at`, `updated_at`.
- **Constraints**: `status` CHECK.
- **Indexes**: `(lot_id)` for the collector's match list; `(recycler_organization_id)`.
- **Security**: `match_reason` documents the composite score (FR-031, never gross price alone).

### 5.8 Transactions

#### transactions — DB-027
- **Purpose**: lifecycle state machine; the money/fulfilment record.
- **RTM**: FR-034, FR-040, FR-044.
- **Columns**: `id uuid PK`, `idempotency_key text UNIQUE`, `lot_id uuid NOT NULL FK lots ON DELETE CASCADE`, `collector_id uuid NOT NULL FK collectors ON DELETE CASCADE`, `recycler_organization_id uuid FK recycler_organizations ON DELETE SET NULL`, `match_id uuid FK matches ON DELETE SET NULL`, `status text NOT NULL DEFAULT 'LOT_CREATED' CHECK ('LOT_CREATED','CLASSIFIED','QUOTED','QUOTE_ACCEPTED','PICKUP_OR_DELIVERY','WEIGHT_VERIFIED','HANDOVER_CONFIRMED','PAYMENT_RECORDED','COMPLETED')`, `currency text DEFAULT 'INR'`, `agreed_price_per_kg numeric`, `expected_weight_kg numeric`, `final_weight_kg numeric`, `transport_cost numeric`, `net_earnings numeric`, `pickup_method text CHECK ('pickup','delivery')`, `scheduled_at timestamptz`, `created_at`, `updated_at`.
- **Constraints**: `idempotency_key UNIQUE`; `status` CHECK (FR-034); `pickup_method` CHECK.
- **Indexes**: `(collector_id, created_at DESC)`; `(lot_id)`.
- **Security**: ownership enforced (`collector_id`, FR-054). `net_earnings` is derived (FR-040). CASCADE risk (O-DB-1).

#### transaction_events — DB-028
- **Purpose**: immutable status-change audit trail.
- **RTM**: FR-035, FR-051.
- **Columns**: `id uuid PK`, `transaction_id uuid NOT NULL FK transactions ON DELETE CASCADE`, `event_type text NOT NULL`, `from_status text`, `to_status text`, `actor_user_id uuid FK users ON DELETE SET NULL`, `metadata jsonb NOT NULL DEFAULT '{}'`, `created_at`.
- **Constraints**: append-only; no `updated_at`.
- **Indexes**: `(transaction_id, created_at)`.

### 5.9 Weight & handover

#### weights — DB-029
- **Purpose**: declared/pickup/final weight measurements.
- **RTM**: FR-036, FR-051.
- **Columns**: `id uuid PK`, `transaction_id uuid NOT NULL FK transactions ON DELETE CASCADE`, `weight_type text NOT NULL CHECK ('declared','pickup','final')`, `weight_kg numeric NOT NULL`, `measured_at timestamptz DEFAULT now()`, `measured_by_user_id uuid FK users ON DELETE SET NULL`, `source text NOT NULL DEFAULT 'collector' CHECK ('collector','recycler','scale')`, `created_at`, `updated_at`.
- **Constraints**: `weight_type` and `source` CHECK; `weight_kg NOT NULL`.
- **Indexes**: `(transaction_id)`.

#### handover_records — DB-030
- **Purpose**: digital handover between parties.
- **RTM**: FR-037, FR-051.
- **Columns**: `id uuid PK`, `transaction_id uuid NOT NULL FK transactions ON DELETE CASCADE`, `handed_over_by_user_id uuid FK users ON DELETE SET NULL`, `received_by_user_id uuid FK users ON DELETE SET NULL`, `handed_over_at timestamptz DEFAULT now()`, `signature_ref text`, `notes`, `created_at`.
- **Constraints**: append-only.
- **Security**: schema-ready; no endpoint yet (FR-037 Schema-ready).

### 5.10 Payments

#### payments — DB-031
- **Purpose**: payment record (cash/UPI/bank transfer).
- **RTM**: FR-038, FR-044.
- **Columns**: `id uuid PK`, `idempotency_key text UNIQUE`, `transaction_id uuid NOT NULL FK transactions ON DELETE CASCADE`, `amount numeric NOT NULL`, `currency text DEFAULT 'INR'`, `method text NOT NULL CHECK ('cash','upi','bank_transfer')`, `status text NOT NULL DEFAULT 'recorded' CHECK ('recorded','confirmed','disputed')`, `payer_organization_id uuid FK organizations ON DELETE SET NULL`, `payee_user_id uuid FK users ON DELETE SET NULL`, `reference text`, `recorded_at timestamptz DEFAULT now()`, `created_at`, `updated_at`.
- **Constraints**: `idempotency_key UNIQUE`; `method` and `status` CHECK; `amount NOT NULL`.
- **Indexes**: `(transaction_id)`.
- **Security**: digital payment optional (FR-039); no payment-gateway token stored (only `reference`).

#### payment_confirmations — DB-032
- **Purpose**: confirmation trail for a payment.
- **RTM**: FR-038.
- **Columns**: `id uuid PK`, `payment_id uuid NOT NULL FK payments ON DELETE CASCADE`, `confirmed_by_user_id uuid FK users ON DELETE SET NULL`, `confirmation_source text`, `confirmed_at timestamptz DEFAULT now()`, `created_at`.
- **Constraints**: append-only.

### 5.11 Disputes

#### disputes — DB-033
- **Purpose**: dispute against a transaction.
- **RTM**: FR-062.
- **Columns**: `id uuid PK`, `transaction_id uuid NOT NULL FK transactions ON DELETE CASCADE`, `raised_by_user_id uuid FK users ON DELETE SET NULL`, `reason text NOT NULL`, `status text NOT NULL DEFAULT 'open' CHECK ('open','under_review','resolved','closed')`, `resolution text`, `resolved_at timestamptz`, `created_at`, `updated_at`.
- **Constraints**: `status` CHECK.
- **Security**: schema-ready; no endpoint yet (FR-062 Schema-ready).

#### dispute_events — DB-034
- **Purpose**: dispute history.
- **RTM**: FR-062.
- **Columns**: `id uuid PK`, `dispute_id uuid NOT NULL FK disputes ON DELETE CASCADE`, `event_type text NOT NULL`, `actor_user_id uuid FK users ON DELETE SET NULL`, `note text`, `created_at`.
- **Constraints**: append-only.

### 5.12 AI

#### ai_models — DB-035
- **Purpose**: pluggable provider/model registry.
- **RTM**: TR-008.
- **Columns**: `id uuid PK`, `provider text NOT NULL`, `model_name text NOT NULL`, `version text`, `task text NOT NULL CHECK ('classification','quality','valuation')`, `is_active boolean DEFAULT true`, `created_at`.
- **Constraints**: `task` CHECK.
- **Security**: registry is currently unused (`ai_model_id` always null) — semi-orphan (see §9).

#### ai_decisions — DB-036
- **Purpose**: one prediction per item/image (advisory only).
- **RTM**: FR-012..FR-017, FR-065.
- **Columns**: `id uuid PK`, `ai_model_id uuid FK ai_models ON DELETE SET NULL`, `lot_item_id uuid FK lot_items ON DELETE SET NULL`, `material_image_id uuid FK material_images ON DELETE SET NULL`, `predicted_category_id uuid FK material_categories ON DELETE SET NULL`, `predicted_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `confidence numeric NOT NULL CHECK (confidence >= 0 AND confidence <= 1)`, `detected_material_types jsonb`, `quality_flags jsonb`, `valuation_hint jsonb`, `status text NOT NULL DEFAULT 'suggested' CHECK ('suggested','confirmed','corrected','rejected')`, `created_at`.
- **Constraints**: `confidence` CHECK; `status` CHECK.
- **Security**: advisory only — a prediction is never applied to the item until a human confirm/correct (FR-021, AT-011).

#### ai_corrections — DB-037
- **Purpose**: human corrections, stored as training candidates.
- **RTM**: FR-018, FR-020, FR-063.
- **Columns**: `id uuid PK`, `ai_decision_id uuid NOT NULL FK ai_decisions ON DELETE CASCADE`, `corrected_category_id uuid FK material_categories ON DELETE SET NULL`, `corrected_subcategory_id uuid FK material_subcategories ON DELETE SET NULL`, `corrected_by_user_id uuid FK users ON DELETE SET NULL`, `correction_type text NOT NULL CHECK ('category','subcategory','grade','condition','other')`, `is_training_candidate boolean NOT NULL DEFAULT true`, `note text`, `created_at`.
- **Constraints**: `correction_type` CHECK; `is_training_candidate` defaults true (FR-020).

### 5.13 Audit & ops

#### audit_events — DB-038
- **Purpose**: append-only before/after audit trail.
- **RTM**: FR-057, FR-035, FR-051.
- **Columns**: `id uuid PK`, `actor_user_id uuid FK users ON DELETE SET NULL`, `organization_id uuid FK organizations ON DELETE SET NULL`, `action text NOT NULL`, `entity_type text`, `entity_id uuid`, `before jsonb`, `after jsonb`, `ip_address inet`, `created_at`.
- **Constraints**: append-only; no `updated_at`.
- **Indexes**: `(entity_type, entity_id)`; `(actor_user_id)`; `(action)` as needed.
- **Security**: immutable; `ip_address` stored as `inet` for origin attribution.

#### notifications — DB-039
- **Purpose**: user notifications (reserved; no endpoint yet).
- **RTM**: FR-051 (traceability), FR-062 (disputes) — **NEEDS VALIDATION**: no dedicated notification FR; flagged as an orphan feature in the RTM. Recommend adding a `FR-068 — Notifications` before building the endpoint.
- **Columns**: `id uuid PK`, `user_id uuid NOT NULL FK users ON DELETE CASCADE`, `organization_id uuid FK organizations ON DELETE SET NULL`, `type text NOT NULL`, `title text`, `body text`, `is_read boolean NOT NULL DEFAULT false`, `created_at`.
- **Indexes**: `(user_id, is_read, created_at)` for the unread inbox.
- **Security**: schema-ready; do not build the endpoint until an FR exists.

#### sync_operations — DB-040
- **Purpose**: idempotency ledger for offline sync.
- **RTM**: FR-042, FR-044, TR-016.
- **Columns**: `id uuid PK`, `idempotency_key text NOT NULL UNIQUE`, `client_id text`, `user_id uuid FK users ON DELETE SET NULL`, `entity_type text`, `entity_id uuid`, `operation text NOT NULL CHECK ('create','update')`, `status text NOT NULL DEFAULT 'pending' CHECK ('pending','applied','failed')`, `request_payload jsonb`, `response_payload jsonb`, `error text`, `synced_at timestamptz`, `created_at`.
- **Constraints**: `idempotency_key UNIQUE`; `operation` and `status` CHECK.
- **Security**: replay-safe (FR-044); `request_payload`/`response_payload` retain only necessary fields.

#### schema_migrations — DB-041
- **Purpose**: migration tracking (infrastructure).
- **RTM**: TR-013.
- **Columns**: `version text PK`, `applied_at timestamptz DEFAULT now()`.

---

## 6. Index summary

| Index | Table | Type | Purpose | RTM |
| ----- | ----- | ---- | ------- | --- |
| `email` (UNIQUE) | users | B-tree | login lookup | FR-053 |
| `code` (UNIQUE) ×n | roles, taxonomy | B-tree | reference lookup | FR-001, FR-008 |
| `uq_user_roles_org` / `uq_user_roles_no_org` | user_roles | partial unique | org-scoped role uniqueness | FR-004 |
| `(recycler_organization_id, material_category_id, material_subcategory_id)` | recycler_material_acceptance | unique | acceptance dedup | FR-030 |
| `idx_recycler_facilities_location` | recycler_facilities | GiST | nearby search | FR-049 |
| `idempotency_key` (UNIQUE) | lots, transactions, payments, sync_operations | B-tree | idempotency | FR-044 |

> **Recommended (reviewed, not applied)**: `(collector_id, created_at)` on
> `lots`/`transactions`; `(material_category_id, observed_at)` on
> `price_observations`; `(user_id, is_read, created_at)` on `notifications`;
> `(transaction_id, created_at)` on `transaction_events`. These are additive and
> belong in a later migration once query profiles are confirmed.

---

## 7. Seed data

| Table | Rows | Notes |
| ----- | ---- | ----- |
| roles | 9 | collector, kabadiwala, aggregator, recycler, dismantler, super_admin, support, operations_admin, data_ai_admin (0014 seeds 6; 0019 renames 2 + adds 3) |
| collector_categories | 14 | the approved simple labels |
| material_categories | 22 | 8 equipment + 14 recovered_material |
| material_subcategories | 17 | representative subset |
| material_grades | 5 | A, B, C, Mixed, Low |
| material_conditions | 5 | new, used, damaged, mixed, unknown |
| material_hazards | 6 | lithium, CRT lead, mercury, lead-acid, FR, capacitors |
| material_hazard_links | 6 | category → hazard |
| collector_category_mappings | 19 | collector → backend mapping |
| translations | 14 | Hindi collector-category labels |

Seed is **reference/demo data**, not exhaustive. Six of eight locales remain
content work (FR-005 In progress).

---

## 8. RTM coverage map

| Domain | Tables | RTM IDs |
| ------ | ------ | ------- |
| Identity | users, roles, user_roles | FR-001, FR-002, FR-004, FR-053, FR-054, FR-060, FR-061 |
| Organizations | organizations | FR-003, FR-027 |
| Collectors | collectors | UR-001..006, FR-010 |
| Recyclers | recycler_organizations, recycler_facilities, recycler_authorizations, recycler_material_acceptance, recycler_service_areas | FR-026..029, FR-048, FR-049 |
| Material taxonomy | material_*, collector_categories, collector_category_mappings, translations | FR-005..009, FR-012, FR-023, FR-050 |
| Lots | lots, lot_items | FR-010, FR-044 |
| Images | material_images | FR-011, FR-045, FR-046 |
| Pricing | price_observations, price_history | FR-022..025, FR-064, FR-066 |
| Quotes | recycler_quotes | FR-032 |
| Matching | matches | FR-030, FR-031 |
| Transactions | transactions, transaction_events | FR-034, FR-035, FR-040, FR-044, FR-051 |
| Weight | weights | FR-036 |
| Handover | handover_records | FR-037 |
| Payments | payments, payment_confirmations | FR-038, FR-044 |
| Disputes | disputes, dispute_events | FR-062 |
| AI | ai_models, ai_decisions, ai_corrections | FR-012..018, FR-020, FR-021, FR-063, FR-065 |
| Audit | audit_events | FR-057, FR-035, FR-051 |
| Offline sync | sync_operations | FR-042, FR-044, TR-016 |
| Notifications | notifications | FR-051, FR-062 ⚠ NEEDS VALIDATION |

---

## 9. Risks & open items (reviewed, not applied)

| ID | Issue | Severity | Action |
| -- | ----- | -------- | ------ |
| R-DB-1 | `org_scope` (FR-003) is defined but not applied to all org-scoped queries; RLS is off | High | Wire `org_scope` into org-scoped endpoints before production |
| O-DB-1 | `lots → transactions` and `transactions → weights/payments` use `ON DELETE CASCADE` | High | Switch to `RESTRICT` / soft-close so money movements cannot be cascaded away |
| O-DB-2 | `recycler_service_areas` radius/polygon not consumed by matching | Medium | Use service area in FR-030 matching |
| O-DB-3 | `price_history` has no derivation job | Medium | Schedule a worker (Redis) to compute period aggregates (FR-066) |
| O-DB-4 | `notifications` (DB-039) has no dedicated FR/endpoint | Medium | Add `FR-068` before building the endpoint |
| O-DB-5 | `ai_models` registry unused (`ai_model_id` null) | Low | Populate when a real provider lands (TR-008) |
| O-DB-6 | Recommended composite indexes not yet created | Low | Add in a later migration after query profiling |

---

## 10. Migration files (preserved, unchanged)

The following files are the reviewed implementation of this design and are
**preserved as-is** in this phase:

```
0001_extensions.sql    — postgis + set_updated_at()
0002_identity.sql      — organizations, users, roles, user_roles
0003_collectors.sql    — collectors
0004_taxonomy.sql      — material_*, collector_*, translations
0005_recycler.sql      — recycler_* (facilities, authorizations, acceptance, service areas)
0006_lots.sql          — lots, lot_items, material_images
0007_pricing.sql       — price_observations, price_history, recycler_quotes
0008_matching.sql      — matches
0009_transactions.sql  — transactions, transaction_events, weights, handover_records
0010_payments.sql      — payments, payment_confirmations
0011_disputes.sql      — disputes, dispute_events
0012_ai.sql            — ai_models, ai_decisions, ai_corrections
0013_ops.sql           — audit_events, notifications, sync_operations
0014_seed_roles.sql    — 6 roles
0015_seed_taxonomy.sql — reference taxonomy
0016_ai_enhancements.sql — ai_decisions: provider/model_name/model_version/alternatives
0017_pricing_matching.sql — price_observations unit+confidence; recycler_organizations pickup_available
0018_transaction_handover_idempotency.sql — handover_records idempotency_key
0019_roles.sql — role renames + 3 new roles (6 → 9)
```

**No new migration SQL is written in this phase.** Schema changes (open items in
§9) are documented for a separate review/approval step before any migration is
authored, per the "create migration SQL only after the schema has been reviewed
logically" rule.
