# Decision Log

> Architecture Decision Records (ADRs). Each entry records the context,
> decision, and consequences. New decisions are appended; superseded decisions
> are marked as such, not deleted.

---

## ADR-0001 — Monorepo layout

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Three applications (mobile, backend, web) plus shared docs must
coexist in one repository with independent lifecycles.

**Decision**: Single repository with top-level `mobile/`, `backend/`, `web/`,
and `docs/` directories. No heavy monorepo tooling (Turborepo/Nx) until the
cross-package dependency surface justifies it.

**Consequences**: Simple, transparent layout. Shared code (if any emerges,
e.g. taxonomy constants) will need an explicit decision later.

---

## ADR-0002 — Technology stack

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Approved stack specified in the design document.

**Decision**: Mobile = React Native/Expo/TypeScript/SQLite; Backend =
FastAPI/Python REST; Database = Supabase PostgreSQL + PostGIS; Media =
Cloudinary; Cache/jobs = Redis; Web = Next.js/TypeScript; Maps =
OpenStreetMap/MapLibre; AI = pluggable service.

**Consequences**: Offline-first on Android via Expo + SQLite; backend
authoritative; PostGIS for geospatial; media kept out of PostgreSQL.

---

## ADR-0003 — AI is assistive, not authoritative

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: AI classification can be wrong, especially for heterogeneous
e-waste, and cannot determine chemical composition from a photo.

**Decision**: AI provides suggestions and confidence only. High confidence ->
collector confirms; low confidence -> manual selection or "I don't know";
escalation to recycler/admin review when necessary. Corrections are feedback
candidates, not ground truth.

**Consequences**: The AI interface is strictly advisory. The backend must never
persist an AI suggestion as an authoritative fact without a confirming human
action.

---

## ADR-0004 — Price is contextual and provenance-backed

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: A single hard-coded price (e.g. "PCB = ₹180/kg") is misleading
because value depends on grade, location, buyer, weight, transport, and timing.

**Decision**: Model price observations with full provenance (material, grade,
location, date/time, buyer, weight, transport, source, verification). Collector
buyer prices are observations, not authoritative market prices.

**Consequences**: No hard-coded price constants in code. Pricing derives from
observations; any market price is a computed aggregation with clear provenance.

---

## ADR-0005 — Recycler verification is explicit and gated

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Trust requires verified authorization; a recycler must never be
treated as verified by default.

**Decision**: Store full authorization data (authority, number, type,
issue/expiry, verification source/date, accepted materials, service area,
status). Statuses: Verified/Pending/Expiring/Expired/Suspended. Expired
authorization excludes the recycler from matching.

**Consequences**: Matching must always join against current (non-expired)
authorization status.

---

## ADR-0006 — Offline-first with idempotent sync

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Collectors operate in low-connectivity areas.

**Decision**: SQLite is the local working database. Backend stays authoritative.
Sync uses idempotency keys (e.g. `KC-LOT-260926-000482`) so retries never
create duplicates.

**Consequences**: Every mutating sync request must carry an idempotency key and
be deduplicated server-side.

---

## ADR-0007 — Media lives in Cloudinary, not PostgreSQL

- **Status**: Accepted
- **Date**: 2026-09-26

**Decision**: Upload to Cloudinary; store public ID / secure URL plus metadata
in PostgreSQL.

**Consequences**: PostgreSQL stores no large binary payloads.

---

## ADR-0008 — No Aadhaar in the MVP

- **Status**: Accepted
- **Date**: 2026-09-26

**Decision**: Do not collect Aadhaar unless explicitly required later.

**Consequences**: Identity model must not assume Aadhaar; future addition would
be a separate decision.

---

## ADR-0009 — Secrets via environment variables only

- **Status**: Accepted
- **Date**: 2026-09-26

**Decision**: All credentials live in environment variables. Repository ships
`.env.example` (template, empty values) only; `.env` is git-ignored.

**Consequences**: No secret is ever committed. Production secrets are managed in
Render/Vercel/Supabase.

---

## ADR-0010 — Migrations: plain SQL + Node/pg runner

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Backend is FastAPI/Python, but the local machine has no working
Python (only the Microsoft Store stub). Node v24 is available. We needed a
repeatable, validated way to apply the PostGIS schema now.

**Decision**: Versioned `.sql` files under `backend/migrations/` applied by a
small Node runner using `pg`, tracked in `schema_migrations`.

**Consequences**: Portable SQL (usable via `psql` or Supabase SQL editor too).
The runner can be replaced by a Python/Alembic equivalent in Phase 2 without
changing the SQL files.

---

## ADR-0011 — UUID primary keys for client-created entities

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Offline-first sync means mobile clients create entities while
disconnected and upload them later. Server-assigned integer IDs would collide.

**Decision**: `uuid DEFAULT gen_random_uuid()` primary keys for all entities, so
clients can generate IDs offline safely. Lookup/seed tables use the same UUID
convention (with fixed IDs for seed rows) for consistency.

**Consequences**: No central sequence dependency; larger keys than bigint, which
is acceptable here.

---

## ADR-0012 — Taxonomy: collector-facing vs backend, equipment vs recovered

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Collectors must see simple labels; the backend needs a detailed
taxonomy; and equipment must be tracked separately from recovered material.

**Decision**: `collector_categories` (14 simple labels) map via
`collector_category_mappings` to detailed `material_categories`. The latter are
split by `kind` (`equipment` | `recovered_material`). `lot_items` records both
the collector-facing and the resolved backend category.

**Consequences**: A collector's simple choice is preserved while the backend
keeps detail; dismantling can create new recovered-material items linked to the
source equipment.

---

## ADR-0013 — RLS off; organization isolation at the backend layer

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: The backend is authoritative and connects with elevated credentials
(service role / direct DB). Mobile/web clients do not connect to Postgres
directly.

**Decision**: Do not enable Row Level Security on application tables;
organization-level isolation is enforced in backend query logic (Phase 2).

**Consequences**: Simpler schema; isolation correctness depends on the backend,
which is the intended authoritative boundary. Revisit RLS only if a direct
client-facing DB path is ever introduced.

---

## ADR-0014 — Localization via a generic translations table

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Eight languages are required across taxonomy, roles, and UI text.

**Decision**: Canonical English in each entity's `name`, with a generic
`translations (entity_type, entity_id, field, locale, value)` table for
localized labels.

**Consequences**: One mechanism serves all entities; avoids per-entity
translation tables. Full non-Hindi locale content is Phase 7 work.

---

## ADR-0015 — Supabase Auth as identity provider

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: The approved stack uses Supabase for auth; the backend must trust
client identity without reimplementing login.

**Decision**: Supabase Auth issues JWTs; the backend verifies them against the
project JWKS (RS256, `iss`/`aud` checks). The JWT `sub` maps to our `users.id`,
which is auto-provisioned (minimal email/phone) on first login.

**Consequences**: No password handling in the backend. App `users` mirror
Supabase users by UUID. Auto-provisioning is idempotent.

---

## ADR-0016 — psycopg3 async + plain SQL (no ORM)

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: The schema is DB-first (plain SQL migrations). An ORM would require
re-declaring ~40 tables and add indirection for a backend that is the
authoritative query layer.

**Decision**: Access Postgres with async psycopg3 (`AsyncConnectionPool`) and
hand-written SQL. No SQLAlchemy ORM.

**Consequences**: Queries are explicit and match the migrations. More SQL to
write, but no model/schema drift. FastAPI `async def` endpoints throughout.

---

## ADR-0017 — Windows selector event loop (dev-only)

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: psycopg async cannot run on Windows' default ProactorEventLoop, and
uvicorn 0.54 hardcodes ProactorEventLoop on Windows regardless of the loop
policy.

**Decision**: On Windows, run via `backend/run.py`, which passes a custom loop
factory (`app.loops.selector_loop_factory` → `SelectorEventLoop`) to uvicorn.
`app/__init__.py` also sets `WindowsSelectorEventLoopPolicy` so TestClient /
`asyncio.run` contexts (tests) use the selector loop.

**Consequences**: Local development on Windows works. Production on Render
(Linux) uses the default uvicorn loop unchanged (`uvicorn app.main:app`).

---

## ADR-0018 — Pluggable AI provider with a no-AI default

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: AI must be assistive and pluggable; no provider credentials are
available yet.

**Decision**: A `BaseProvider` interface with a single `classify(...)` method.
The default `AI_PROVIDER=none` uses `NullProvider`, which returns an empty
suggestion (confidence 0) and forces manual classification. Real providers are
registered later without changing the endpoint contract.

**Consequences**: The classify/confirm/correct flow is fully testable today.
AI is structurally advisory: the backend never persists a prediction as fact
without a confirming human action.

---

## ADR-0019 — Media via Cloudinary signed direct upload

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Large images must not be stored in PostgreSQL; the approved media
store is Cloudinary.

**Decision**: The collector uploads directly to Cloudinary (signed upload); the
backend stores only `cloudinary_public_id` / `cloudinary_url` metadata. Signed
upload parameters are issued by `GET /api/v1/media/upload-params`.

**Consequences**: No binary data through the backend or in PostgreSQL. The
signed-upload path is untested against Cloudinary until credentials are
provided (returns 503 when unconfigured).

---

## ADR-0020 — Pricing is observation-driven, never hard-coded

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: A fixed price per material is misleading; value depends on grade,
location, buyer, weight, transport, source, and verification.

**Decision**: Prices are stored as provenance-backed `price_observations`. The
estimate endpoint aggregates observations; it returns `null` when none exist
rather than inventing a number. Collector entries are `unverified`; only
`verification` source is `verified`.

**Consequences**: No price constants in code. Market price is a computed
aggregate with an explicit sample and provenance.

---

## ADR-0021 — Recycler verification is derived and expiry-aware

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Recyclers must not be auto-verified, and expired authorization must
exclude them from matching.

**Decision**: Verification is stored on `recycler_authorizations` and the
effective status is derived: `verified` only when a `verified` authorization is
not expired. The `/recycler/verified` endpoint filters to non-expired verified
authorizations using the backend clock (`date.today()`), consistent with the
derivation helper.

**Consequences**: Matching (Phase 5) consumes `/recycler/verified`, so expired
recyclers are structurally excluded.

---

## ADR-0022 — Matching by composite score, not gross price

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Ranking recyclers by gross price alone is wrong; matching must weigh
authorization, acceptance, service area, distance, transport, and reliability.

**Decision**: Match candidates are first filtered to non-expired verified
recyclers with material acceptance overlap, then ranked by a composite score:
`material_coverage * 60 + proximity_score` (proximity decays with distance).
`match_reason` records the factors. Gross price is not part of the score.

**Consequences**: A transparent, explainable ranking. Quotes/net-earnings are
added as factors in a later refinement without changing the storage shape.

---

## ADR-0023 — Transaction lifecycle as an explicit state machine

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: The approved lifecycle is a fixed sequence of states; illegal jumps
must be rejected and transitions must be auditable.

**Decision**: `transactions.status` is constrained to the approved sequence and a
`TRANSITIONS` map defines the single legal next state per state. The
`/transition` endpoint validates against it (409 on illegal), writes a
`transaction_events` row, and records an audit event.

**Consequences**: The lifecycle is enforced at the backend (authoritative). New
states/transitions are added by editing one map.

---

## ADR-0024 — Offline sync via batch idempotent endpoint + replay

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Offline-first clients push batched changes; retries must never
create duplicates.

**Decision**: A single `POST /api/v1/sync` accepts a batch of operations
(`lot`, `lot_item`, `transaction`, `weight`, `payment`), each with an
idempotency key and a client-generated UUID. The key is recorded in
`sync_operations` with the created `entity_id`; a repeated key returns
`replayed` with the original id rather than re-creating. Each operation commits
independently.

**Consequences**: Replay is idempotent and non-erroring (unlike the HTTP
middleware's 409). No merge logic — the backend is authoritative and last write
wins. Client-generated UUIDs (ADR-0011) make offline ID assignment safe.

---

## ADR-0025 — Mobile data layer is pure TypeScript (Expo-isolated)

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: The offline sync logic must be unit-testable without a device, and
Expo/React Native types cannot resolve under Node's native TypeScript runner.

**Decision**: Keep the data layer (`types`, `lib`, `sync`) free of Expo/React
imports and test it with `node:test` (via `tsx`). Expo-dependent code (App.tsx,
screens, `expo-sqlite` adapter) is isolated. Client IDs use a dependency-free
Math.random UUID v4 for MVP (replace with `crypto.randomUUID()` later).

**Consequences**: The sync queue and idempotency key format are verified by
tests today. The on-device runtime remains unverified until an emulator/device
is available.

---

## ADR-0026 — Nearby search via PostGIS; web map via MapLibre + OSM

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Location-based recycler discovery needs spatial queries, and the
web dashboard needs a map without paid tile services.

**Decision**: `GET /api/v1/recycler/nearby` uses PostGIS `ST_DWithin` +
`ST_Distance` on facility `geography(Point,4326)` to return verified,
non-expired recyclers within a radius (ordered by distance, with optional
material filter). The Next.js dashboard renders them with MapLibre GL over
OpenStreetMap raster tiles (no API key).

**Consequences**: Spatial filtering is done in the database (authoritative).
The map works with zero tile cost. Service-area polygon coverage is a future
refinement.

---

## ADR-0027 — Rate limiting: in-memory fixed window (Redis for scale)

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: Mutation endpoints need abuse protection, but Redis is not yet
provisioned in every environment.

**Decision**: A fixed-window per-IP middleware (`app/rate_limit.py`) with a
configurable limit/window, exempting health endpoints. In-memory for the
single-instance MVP; swap to Redis when the backend scales horizontally.

**Consequences**: Simple, dependency-free, and tested (429 after limit). Not
shared across instances — noted as a deployment hardening item.

---

## ADR-0028 — Deployment topology: Render + Vercel + Supabase + Cloudinary

- **Status**: Accepted
- **Date**: 2026-09-26

**Context**: The approved stack names Render (backend), Vercel (web), Supabase
(Postgres/PostGIS), Cloudinary (media), Redis (cache/jobs).

**Decision**: `render.yaml` (repo root, `rootDir: backend`) defines the FastAPI
service; `web/vercel.json` + Vercel auto-detect deploy the Next.js app; secrets
are set in each host's secret store (never in committed files). TLS is
terminated at each host.

**Consequences**: Documented, reproducible deployment. Redis wiring and a CI/CD
pipeline remain follow-ups.

---

## ADR-0029 — Canonical sync wire contract is snake_case (backend authoritative)

- **Status**: Accepted
- **Date**: 2026-09-27

**Context**: The architecture audit found the mobile offline-sync data layer
serializes operations in **camelCase** (`idempotencyKey`, `entityType`,
`entityId`, and payload keys like `materialCategoryId`), while the backend
`POST /api/v1/sync` contract is **snake_case** (`idempotency_key`, `entity_type`,
`entity_id`, `material_category_id`). No serialization layer exists, so the two
sides do not interoperate.

**Decision**: The backend contract is canonical and stays snake_case (it is
already shipped, documented in `offline-sync.md`, and tested). The mobile data
layer must serialize to snake_case at the API boundary. Shared wire types
(camelCase in TypeScript, snake_case on the wire) will be reconciled by an
explicit mapping in the mobile API client rather than renaming either side's
internal model.

**Consequences**: A single, unambiguous wire contract. The mobile internal model
keeps idiomatic camelCase; only the transport mapping changes. An integration
test against the real sync shape is required to prevent regression.

---

## ADR-0030 — Repair merge-conflict markers and align README to as-built state

- **Status**: Accepted
- **Date**: 2026-09-27

**Context**: The audit found unresolved git merge-conflict markers
(`<<<<<<< HEAD` / `=======` / `>>>>>>> 6cf372b…`) committed in `README.md` and
`.gitignore`, and a README status banner ("Phase 0 — Foundation") that
contradicts the implemented backend (Phases 1–6 and 8 are complete and tested).

**Decision**: Strip the conflict markers from both files and update the README to
reflect the as-built state. The `.gitignore` result will be a deliberate union of
the two sides (both the project-specific rules and the standard Node/Python
rules), not a blind "keep HEAD".

**Consequences**: Clean, parseable repository metadata. A truthful, current README
so contributors are not misled about maturity. No code behavior changes.

---

## ADR-0031 — Remove unused local-JWT config; identity is Supabase-only

- **Status**: Accepted
- **Date**: 2026-09-27

**Context**: `.env.example` advertises `JWT_SECRET`, `JWT_ALGORITHM`, and
`ACCESS_TOKEN_EXPIRE_MINUTES`, but the backend never reads them — identity is
entirely Supabase Auth (JWT verified against JWKS, RS256), per ADR-0015.

**Decision**: Remove (or explicitly deprecate) the unused local-JWT variables from
`.env.example` so configuration does not imply a local signing path that does not
exist.

**Consequences**: Config matches reality. No confusion about a second,
non-existent auth mechanism. If local/self-hosted auth is ever introduced, it
will be a new, separate decision.

