# Kabadi Mitra — Architecture & Repository Audit

> Audit date: 2026-09-27. This document supersedes the earlier "Phase 0" version
> of this file. It records the **approved (target) architecture**, the **as-built
> (current) state** discovered by the audit, the **gap analysis**, and the
> **recommended implementation order**. It is a planning artifact, not a spec of
> record for the already-approved design (that lives in the sibling docs listed
> in the [Documentation](#documentation) section).

---

## 1. Executive summary

Kabadi Mitra is a collector-first digital bridge between informal e-waste
collection and authorized recyclers. The repository is a monorepo
(`backend/`, `mobile/`, `web/`, `docs/`) whose **backend is substantially
complete and tested**, while the **mobile and web clients are early-stage
scaffolds**.

The single most important finding: the mobile offline-sync data layer is
implemented and unit-tested **in isolation**, but its wire contract is
**camelCase** while the authoritative backend `/api/v1/sync` contract is
**snake_case**. The two sides do not currently interoperate — a silent, blocking
gap that no existing document records.

Two source files (`README.md`, `.gitignore`) contain **unresolved git
merge-conflict markers** and must be repaired.

---

## 2. Current architecture (as-built)

### 2.1 Repository layout

```
kabadimitra/
├── .env.example         # env template (no secrets)
├── .gitignore           # ⚠ contains merge-conflict markers
├── README.md            # ⚠ contains merge-conflict markers; status is stale
├── render.yaml          # Render blueprint (FastAPI)
├── backend/             # FastAPI + psycopg3 async (plain SQL) — Phases 1–6, 8–9
│   ├── app/
│   │   ├── main.py      # app assembly, CORS, middleware, 14 routers
│   │   ├── config.py    # pydantic-settings env config
│   │   ├── db.py        # AsyncConnectionPool + get_db
│   │   ├── auth.py      # Supabase JWT verify + principal resolution
│   │   ├── dependencies.py  # require_role, org_scope
│   │   ├── audit.py     # audit_events writer
│   │   ├── idempotency.py   # Idempotency-Key middleware (409 on dup)
│   │   ├── rate_limit.py    # in-memory fixed-window rate limit
│   │   ├── media.py     # Cloudinary signed-upload params
│   │   ├── recyclers.py # effective (expiry-aware) verification
│   │   ├── collectors.py    # collector profile resolution
│   │   ├── sync.py      # idempotent batch sync application
│   │   ├── loops.py     # Windows selector-loop factory
│   │   ├── schemas.py   # Pydantic request/response models
│   │   ├── ai/provider.py   # pluggable BaseProvider + NullProvider
│   │   └── routers/     # health, auth, taxonomy, admin, lots, ai, media,
│   │                    # pricing, recyclers, matching, transactions, sync, geo
│   ├── migrations/      # 15 SQL migrations + Node/pg runner
│   ├── tests/           # 54 pytest integration tests
│   └── run.py           # Windows dev entrypoint
├── mobile/              # Expo/RN — offline data layer only (no screens)
│   └── src/
│       ├── types/       # ⚠ camelCase wire types (mismatch with backend)
│       ├── lib/         # uuid + idempotency-key (pure, tested)
│       ├── sync/        # outbox queue + sync client (pure, tested)
│       ├── api/         # backend fetch wrapper
│       ├── db/          # local SQLite schema (declared, not wired)
│       └── i18n/        # 8 locales scaffolded; en + hi only
├── web/                 # Next.js — nearby-recycler map only
│   ├── app/             # layout + single page
│   └── src/
│       ├── api/client.ts    # nearby-recycler fetch
│       └── components/NearbyMap.tsx  # MapLibre + OSM
└── docs/                # 14 docs (architecture, ADRs, RTM, subsystem docs)
```

### 2.2 Backend (implemented & tested)

| Concern | Status | Notes |
| ------- | ------ | ----- |
| Auth | ✅ Implemented | Supabase JWT → JWKS (RS256, `iss`/`aud`), auto-provision `users`, no local password handling |
| RBAC | ✅ Implemented | `require_role(...)`, six roles seeded |
| Org isolation | ✅ Implemented | `org_scope()` (admin=all, org=scoped, none=nothing) |
| Audit | ✅ Implemented | `record_audit` on capture/classification/transactions/etc. |
| Idempotency | ✅ Implemented | middleware (409) + batch replay (`applied`/`replayed`) |
| Rate limiting | ✅ Implemented | in-memory fixed window (single-instance only) |
| Material capture | ✅ Implemented | lots, items, images (Cloudinary metadata only) |
| AI | ⚠️ Partial | Pluggable `BaseProvider`; only `NullProvider` (manual) shipped |
| Media | ⚠️ Partial | Signed-upload params; untested without Cloudinary creds |
| Pricing | ✅ Implemented | provenance-backed observations + contextual estimate |
| Recycler verification | ✅ Implemented | expiry-aware derived status |
| Matching | ✅ Implemented | composite score (coverage × 60 + proximity) |
| Transactions | ✅ Implemented | explicit state machine + events + audit |
| Weights / payments | ✅ Implemented | declared/pickup/final; cash/upi/bank_transfer |
| Offline sync | ✅ Implemented | `POST /api/v1/sync` batch, idempotent, ownership-checked |
| Geospatial | ✅ Implemented | PostGIS `ST_DWithin`/`ST_Distance` nearby search |

**Persistence**: Supabase PostgreSQL + PostGIS, 41 tables, seeded taxonomy
(6 roles, 14 collector categories, 22 material categories, 17 subcategories,
5 grades, 5 conditions, 6 hazards, 19 mappings, 14 Hindi translations).
Migrations are plain SQL applied by a Node/`pg` runner (ADR-0010), tracked in
`schema_migrations`. Access is psycopg3 async with hand-written SQL — no ORM
(ADR-0016).

### 2.3 Mobile (scaffold + data layer)

- Expo SDK 52 / React Native 0.76 / TypeScript; Android-first `app.json`.
- `App.tsx` is a placeholder; **no screens**.
- Pure-TS data layer (no Expo imports, node:test verified): UUID v4, idempotency
  keys (`KC-<ENTITY>-<YYMMDD>-<NNNNNN>`), outbox `SyncQueue`, `SyncClient`.
- Local SQLite schema declared in `src/db/schema.ts` (not wired to `expo-sqlite`).
- i18n scaffold with `en` + `hi` content only.
- **No Supabase Auth wiring, no token storage, no on-device runtime verification.**

### 2.4 Web (scaffold)

- Next.js 14, single "Nearby Recyclers" page rendering a MapLibre GL map over
  OSM raster tiles (no API key), backed by `GET /api/v1/recycler/nearby`.
- `next build` compiles and type-checks.
- **No auth token wiring, no dashboards, no other workflows.**

### 2.5 Tests

| Target | Count | Kind | Requires |
| ------ | ----- | ---- | -------- |
| Backend | 54 | pytest, integration | live Supabase DB (`DATABASE_URL`) |
| Mobile | 6 | node:test, unit | none (pure TS) |
| Web | — | `next build` type-check | none |

### 2.6 Configuration & deployment

- `.env.example` — comprehensive template; **contains `JWT_SECRET`/`JWT_ALGORITHM`
  that the backend does not use** (identity is Supabase-only, ADR-0015).
- `render.yaml` — FastAPI service on Render (`rootDir: backend`), env keys present.
- `web/vercel.json` — Next.js on Vercel (auto-detected).
- Redis is reserved in config but **not wired** (rate limiting is in-memory).

---

## 3. Target architecture (approved)

This is the approved design, unchanged from the original `architecture.md`. The
gap analysis in §4 is measured against it.

### 3.1 Guiding constraints

- Backend-authoritative business logic.
- AI is **assistive**, never authoritative; uncertain classifications require
  human confirmation.
- Collector UX hides the industrial taxonomy behind simple categories.
- No single hard-coded prices; price is contextual and carries provenance.
- Recyclers are never auto-verified; authorization status gates matching.
- No large media in PostgreSQL; images live in Cloudinary.
- Offline capture works locally (SQLite) and syncs with idempotency keys.

### 3.2 Components

| Component | Technology | Responsibility |
| --------- | ---------- | -------------- |
| Mobile | React Native + Expo + TypeScript + SQLite | Collector capture, lots, offline-first sync |
| Backend | FastAPI + Python (REST) | Authoritative logic, auth, matching, pricing, sync |
| Database | Supabase PostgreSQL + PostGIS | Relational core + geospatial |
| Media | Cloudinary | Image upload, transformation, secure URLs |
| Cache/jobs | Redis | Caching, background/async jobs |
| Web | Next.js + TypeScript | Admin/recycler/aggregator dashboards, maps |
| Maps | OpenStreetMap + MapLibre | Tiles, geocoding, distance |
| AI | Pluggable classification service | Suggestive category/subcategory, confidence, flags |

### 3.3 Deployment topology

```
[Collector]  Mobile (Expo/RN) --HTTPS--> FastAPI (Render)
                                          |-- Supabase PostgreSQL/PostGIS
                                          |-- Cloudinary (media)
                                          |-- Redis (cache/jobs)
                                          |-- AI service (pluggable)
[Admin/Recycler]  Web (Next.js/Vercel) --HTTPS--> FastAPI
```

### 3.4 Primary workflow

```
Collector -> Material Capture -> Classification -> Digital Lot -> Weight
  -> Price Discovery -> Existing Buyer Comparison -> Verified Recycler Matching
  -> Recycler Quote -> Pickup/Delivery -> Final Weight -> Digital Handover
  -> Payment -> Earnings History -> Traceability
```

### 3.5 Domain model

Equipment and recovered material are represented **separately**. Core entities:

- Identity & org: `organizations`, `users`, `roles`, `user_roles`, `collectors`
- Recycler side: `recycler_organizations`, `recycler_facilities`,
  `recycler_authorizations`, `recycler_material_acceptance`, `recycler_service_areas`
- Taxonomy: `material_categories`, `material_subcategories`, `material_grades`,
  `material_conditions`, `material_hazards`, `material_hazard_links`,
  `collector_categories`, `collector_category_mappings`, `translations`
- Lots: `lots`, `lot_items`, `material_images`
- Pricing: `price_observations`, `price_history`, `recycler_quotes`
- Matching: `matches`
- Transactions: `transactions`, `transaction_events`, `weights`, `handover_records`
- Payments: `payments`, `payment_confirmations`
- Disputes: `disputes`, `dispute_events`
- AI: `ai_models`, `ai_decisions`, `ai_corrections`
- Ops: `audit_events`, `notifications`, `sync_operations`

### 3.6 Key subsystems (approved behavior)

- **Classification & AI**: photo → prediction → confidence → confirm/correct;
  corrections are feedback candidates, never auto-ground-truth. AI must not claim
  exact composition/grade from a photo.
- **Price discovery**: observation-driven; collector entries are `unverified`.
- **Recycler verification**: explicit authorization data; `verified` only when a
  non-expired `verified` authorization exists; expired excludes from matching.
- **Matching**: composite score (authorization, acceptance, distance, proximity);
  never gross price alone.
- **Transaction lifecycle**: `LOT_CREATED -> CLASSIFIED -> QUOTED ->
  QUOTE_ACCEPTED -> PICKUP_OR_DELIVERY -> WEIGHT_VERIFIED -> HANDOVER_CONFIRMED
  -> PAYMENT_RECORDED -> COMPLETED`.
- **Offline sync**: SQLite local DB; idempotency keys (`KC-LOT-260926-000482`).
- **Geospatial**: `geography(Point,4326)` + PostGIS distance queries.
- **Security**: HTTPS, JWT auth, RBAC, org isolation, validation, rate limiting,
  audit, secure image handling, env-only secrets, no Aadhaar.

---

## 4. Gap analysis

### 4.1 Blocking

| # | Gap | Detail |
| - | --- | ------ |
| G-1 | **Mobile ↔ backend sync contract mismatch** | Mobile `SyncOperation`/`SyncResult` and payloads use **camelCase** (`idempotencyKey`, `entityType`, `entityId`, `materialCategoryId`, `pickupAddress`). Backend `SyncOperation`/`SyncResult`/payloads use **snake_case** (`idempotency_key`, `entity_type`, `entity_id`, `material_category_id`, `pickup_address`). `ApiClient.postSync` serializes `{ operations }` with no key mapping, so the backend would return `422`. Offline sync is therefore non-functional end-to-end despite both sides being individually tested. |

### 4.2 Missing (planned but not built)

| # | Gap | Detail | Target phase |
| - | --- | ------ | ------------ |
| G-2 | Mobile UI | Capture / lots / sync-status screens absent | 7 |
| G-3 | Mobile auth | Supabase Auth + token storage not wired | 7 |
| G-4 | Mobile SQLite adapter | schema declared; `expo-sqlite` persistence unverified | 7 |
| G-5 | Real AI provider | only `NullProvider`; no OpenAI/Anthropic/self-hosted | 3 |
| G-6 | Web auth + dashboards | no token wiring; single map page only | 8 |
| G-7 | Redis wiring | reserved; rate limit/cache/jobs not using it | 9 |
| G-8 | CI/CD | no pipeline for tests/builds | 9 |
| G-9 | `price_history` derivation | table exists; no worker/job populates it | 4 |
| G-10 | Recycler status flips | no `verified -> expiring -> expired` worker | 4 |
| G-11 | Escalation workflow | recycler/admin review path (FR-AI-08) not implemented | 5 |
| G-12 | i18n content | 6 of 8 locales have no content | 7 |
| G-13 | `material_image` sync | image metadata not in the batch sync contract | 6/7 |

### 4.3 Defects in source

| # | Defect | Severity |
| - | ------ | -------- |
| G-14 | `README.md` contains unresolved merge-conflict markers | High (corrupted file) |
| G-15 | `.gitignore` contains unresolved merge-conflict markers | High (corrupted file) |
| G-16 | `README.md` status ("Phase 0 — Foundation") contradicts the implemented backend | Medium (misleading) |
| G-17 | `.env.example` lists `JWT_SECRET`/`JWT_ALGORITHM` unused by the backend | Low (confusing config) |

### 4.4 Partially implemented (external dependencies)

| # | Item | What's missing |
| - | ---- | -------------- |
| G-18 | Cloudinary signed upload | returns 503 without creds; never exercised against Cloudinary |
| G-19 | Rate limiting | in-memory only; not shared across instances |

---

## 5. Dependency map

```
mobile/src/sync  ──►  POST /api/v1/sync  ──►  backend/app/sync.py  ──►  Supabase PG
      ▲                                        (⚠ snake_case contract)
      └─ mobile/src/api (camelCase — BROKEN)

mobile screens (todo) ──► Supabase Auth ──► mobile token store ──► ApiClient
mobile screens (todo) ──► expo-sqlite ──► src/db/schema.ts

web/app/page ──► web/src/api/client ──► GET /api/v1/recycler/nearby ──► PostGIS
web (todo)    ──► Supabase Auth (token) [not wired]

backend AI ──► ai/provider.py ──► AI_PROVIDER env (real provider todo)
backend media ──► Cloudinary (creds todo)
backend rate-limit ──► in-memory (Redis todo)

matching ──► recycler verification + taxonomy + lots
transactions ──► matches + lots + weights + payments
pricing ──► price_observations

render.yaml ──► backend (env secrets)
web/vercel.json ──► web (NEXT_PUBLIC_API_URL)
```

**Key dependency ordering**: taxonomy → lots/items → AI → pricing/verification →
matching → transactions → payments → sync → mobile/web clients.

---

## 6. Major risks

| # | Risk | Impact | Likelihood |
| - | ---- | ------ | ---------- |
| R-1 | Offline-sync contract mismatch ships as-is → collector offline capture silently fails | High | Certain (as-built) |
| R-2 | Merge-conflict markers in `README.md`/`.gitignore` confuse contributors and tooling | Medium | Certain (as-built) |
| R-3 | Backend tests require a live Supabase DB → no hermetic/CI run, brittle | Medium | High |
| R-4 | No real AI provider → classification is manual-only; AI value prop unrealized | Medium | High until creds/decision |
| R-5 | No CI/CD → regressions undetected between manual runs | Medium | High |
| R-6 | Cloudinary path untested → media upload may fail at first real use | Medium | Medium |
| R-7 | Mobile never run on a device/emulator → runtime behavior unverified | Medium | Medium |
| R-8 | In-memory rate limiting not shared → ineffective under horizontal scale | Low-Med | Medium |
| R-9 | Supabase credentials shared during setup → rotation needed (noted in `security.md`) | Low-Med | Certain (historical) |

---

## 7. Recommended implementation order

Priorities assume the collector offline-capture loop is the primary value path.

1. **Repair repository hygiene** (G-14, G-15, G-16, G-17): resolve
   merge-conflict markers, refresh README status to match as-built state, remove
   unused `JWT_SECRET`/`JWT_ALGORITHM` (or document them).
2. **Fix the sync wire contract** (G-1): standardize on the backend's snake_case;
   add a snake_case serialization layer (or shared contract types) to the mobile
   data layer, and add an integration test against the real `/api/v1/sync` shape.
3. **Introduce a test DB strategy + CI** (R-3, R-5): either a dedicated Supabase
   test project or a local PostGIS container so backend tests run in CI.
4. **Mobile capture loop** (G-2, G-3, G-4, G-13): Supabase auth + token storage,
   `expo-sqlite` adapter, capture/lots/sync-status screens, `material_image`
   metadata sync.
5. **Web auth + dashboards** (G-6): Supabase token wiring and admin/recycler views.
6. **Operational hardening** (G-7, G-8, G-19): Redis-backed rate limiting, CI/CD,
   staging environment.
7. **AI provider + media validation** (G-5, G-18): register a real `BaseProvider`,
   provision Cloudinary creds, validate signed upload.
8. **Recycler/pricing jobs** (G-9, G-10, G-11): `price_history` derivation,
   recycler status-flip worker, escalation workflow.
9. **Content completeness** (G-12): remaining six locale translations.

---

## 8. Reuse / refactor / do-not-touch

**Reuse (high quality, already tested):**

- Entire backend: routers, `auth`, `dependencies`, `audit`, `idempotency`,
  `rate_limit`, `schemas`, `sync`, `collectors`, `recyclers`, `media`, `loops`.
- All 15 migrations + seed taxonomy.
- Mobile pure-TS data layer (after the contract fix in G-1).
- Web `NearbyMap` component + OSM/MapLibre setup.
- All 28 existing ADRs and the subsystem docs.

**Refactor (targeted, low blast radius):**

- Mobile `src/types` + `src/api/client.ts`: add snake_case serialization.
- `README.md`, `.gitignore`: strip conflict markers.
- `.env.example`: remove/document unused JWT fields.

**Do NOT touch (working, tested, approved):**

- Backend routers, migrations, seed data, auth/RBAC/org-isolation logic.
- Existing decision-log entries (ADRs are accurate and historical).
- Approved architecture decisions in `requirements.md`, `api-design.md`,
  `database-design.md`, and the subsystem docs.

---

## 9. Documentation

- [Requirements](requirements.md)
- [Requirement Traceability Matrix](requirement-traceability-matrix.md)
- [Database Design](database-design.md)
- [API Design](api-design.md)
- [AI Architecture](ai-architecture.md)
- [Offline Sync](offline-sync.md)
- [Pricing Engine](pricing-engine.md)
- [Recycler Verification](recycler-verification.md)
- [Security](security.md)
- [Deployment](deployment.md)
- [Testing Strategy](testing-strategy.md)
- [Field Pilot](field-pilot.md)
- [Decision Log](decision-log.md)
