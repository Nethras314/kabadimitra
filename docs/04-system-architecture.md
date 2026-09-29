# Kabadi Mitra — System Architecture

> Audit date: 2026-09-28. Records the **approved (target)** architecture, the
> **as-built (current)** state, the **gap analysis**, and the **recommended
> implementation order**. It is a planning artifact; the spec-of-record lives in
> the sibling docs in [Documentation](#10-documentation).

## 1. Executive summary

Kabadi Mitra is a collector-first digital bridge between informal e-waste
collection and authorized recyclers. The repository is a monorepo
(`backend/`, `mobile/`, `web/`, `docs/`) whose **backend is the most complete
layer**, while **mobile and web are early scaffolds**.

The most important structural finding: the backend is **mid-refactor**. Two
structures coexist:

- **Mounted (live)** — `app/main.py` + `app/routers/*` (13 routers, 32 endpoints,
  inline hand-written SQL, **legacy 6-role model**).
- **Layered (unmounted)** — `app/foundation.py` + `app/{api,services,models,
  repositories,core}` (route→service→repository, **9-role model** with hierarchy,
  migrations 0016–0019). This is implemented and unit-tested (72 tests) but only
  the health domain is mounted; the full app is not yet served from it.

The layered backend is the approved target (ADR-0029, ADR-0030, ADR-0031 mark
the reconciliation work); the mounted routers still reflect the pre-refactor
6-role / pre-0016 schema.

## 2. Repository layout (as-built)

```
kabadimitra/
├── .env.example         # env template (no secrets)
├── .gitignore           # clean (merge markers were removed)
├── README.md            # ⚠ status banner still says "Phase 0" (stale)
├── render.yaml          # Render blueprint (FastAPI)
├── backend/             # FastAPI — Phases 1–6, 8–9
│   ├── app/
│   │   ├── main.py      # MOUNTED app: CORS, middleware, app/routers (13)
│   │   ├── config.py    # pydantic-settings env config
│   │   ├── db.py        # AsyncConnectionPool + get_db
│   │   ├── auth.py      # Supabase JWT verify + Principal (6-role, flat)
│   │   ├── dependencies.py  # require_role, org_scope (6-role)
│   │   ├── audit.py     # audit_events writer
│   │   ├── idempotency.py   # Idempotency-Key middleware (409 on dup)
│   │   ├── rate_limit.py    # in-memory fixed-window rate limit
│   │   ├── media.py     # Cloudinary signed-upload params
│   │   ├── recyclers.py # effective (expiry-aware) verification
│   │   ├── collectors.py    # collector profile resolution
│   │   ├── sync.py      # idempotent batch sync application
│   │   ├── loops.py     # Windows selector-loop factory
│   │   ├── schemas.py   # Pydantic request/response models
│   │   ├── ai/          # provider.py (BaseProvider + NullProvider + ReferenceProvider)
│   │   ├── routers/     # 13 routers, 32 endpoints (MOUNTED, inline SQL)
│   │   ├── foundation.py    # LAYERED app factory (health only, unmounted)
│   │   ├── api/         # thin route handlers + deps (health)
│   │   ├── services/    # business logic (admin, ai, matching, pricing, transaction, valuation, health)
│   │   ├── models/      # domain dataclasses/enums (role, transaction, pricing, matching, recycler, audit)
│   │   ├── repositories/    # data access (in-memory + Postgres variants)
│   │   └── core/        # config, db, security (9-role), errors, rate_limit
│   ├── migrations/      # 19 SQL migrations + Node/pg runner
│   ├── tests/           # 54 integration tests (need live DB)
│   │   └── unit/        # 72 unit tests (pure, passing)
│   └── run.py           # Windows dev entrypoint (app.main:app)
├── mobile/              # Expo SDK 52 — offline data layer only (no screens)
│   └── src/             # types (snake_case), sync, db, cache, i18n, lib
├── web/                 # Next.js 14 — single nearby-recycler map page
│   ├── app/             # layout + page
│   └── src/             # api/client.ts + components/NearbyMap.tsx
└── docs/                # this documentation package
```

## 3. Target architecture (approved)

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
React Native + Expo ──HTTPS──► FastAPI (Render)
                                │── Supabase PostgreSQL/PostGIS
                                │── Cloudinary (media)
                                │── Redis (cache/jobs)
                                └── AI service (pluggable)
Next.js (Vercel) ────HTTPS────► FastAPI
```

### 3.4 Primary workflow

```
Collector → Material Capture → Classification → Digital Lot → Weight
  → Price Discovery → Existing Buyer Comparison → Verified Recycler Matching
  → Recycler Quote → Pickup/Delivery → Final Weight → Digital Handover
  → Payment → Earnings History → Traceability
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

## 4. As-built state (verified)

### 4.1 Backend — mounted (`app/main.py` → `app/routers/*`)

| Concern | Status | Notes |
| ------- | ------ | ----- |
| Auth | IMPLEMENTED | Supabase JWT → JWKS (RS256, `iss`/`aud`), auto-provision `users` |
| RBAC | IMPLEMENTED | `require_role(...)` — **6 legacy roles** |
| Org isolation | PARTIAL | `org_scope()` defined + unit-tested; not wired to all org-scoped endpoints |
| Audit | IMPLEMENTED | `record_audit` on capture/classification/transactions/etc. |
| Idempotency | IMPLEMENTED | middleware (409) + batch replay (`applied`/`replayed`) |
| Rate limiting | IMPLEMENTED | in-memory fixed window (single-instance only) |
| Material capture | IMPLEMENTED | lots, items, images (Cloudinary metadata only) |
| AI | PARTIAL | `NullProvider` + `ReferenceProvider`; no real model |
| Media | PARTIAL | signed-upload params; untested without Cloudinary creds |
| Pricing | IMPLEMENTED | provenance-backed observations + contextual estimate |
| Recycler verification | IMPLEMENTED | expiry-aware derived status |
| Matching | IMPLEMENTED | composite score (coverage × 60 + proximity) |
| Transactions | IMPLEMENTED | explicit state machine + events + audit |
| Weights / payments | IMPLEMENTED | declared/pickup/final; cash/upi/bank_transfer |
| Offline sync | IMPLEMENTED | `POST /api/v1/sync` batch, idempotent, ownership-checked |
| Geospatial | IMPLEMENTED | PostGIS `ST_DWithin`/`ST_Distance` nearby search |

**Persistence**: Supabase PostgreSQL + PostGIS, 41 tables, 19 migrations
(`0001…0019`). Seed taxonomy: roles, 14 collector categories, 22 material
categories, 17 subcategories, 5 grades, 5 conditions, 6 hazards, mappings, and
14 Hindi translations. Access is psycopg3 async with hand-written SQL (no ORM,
ADR-0016).

### 4.2 Backend — layered (unmounted, `app/foundation.py` + `services/models/repositories/core`)

| Layer | Contents | Status |
| ----- | -------- | ------ |
| `core/security.py` | `Principal` with **9-role** `ROLE_IMPLIES` hierarchy, `org_scope` | IMPLEMENTED (unit-tested) |
| `core/errors.py` | `AppError` + uniform `{"error":{code,message,details}}` envelope | IMPLEMENTED (unit-tested) |
| `models/*` | role hierarchy, transaction state machine, pricing, matching, recycler, audit dataclasses/enums | IMPLEMENTED (unit-tested) |
| `services/*` | admin, ai, matching, pricing, transaction, valuation, health | IMPLEMENTED (unit-tested) |
| `repositories/*` | in-memory + Postgres variants for ai, pricing, recycler, transaction, health | IMPLEMENTED (unit-tested) |
| `api/health.py` | thin health routes → `HealthService` | IMPLEMENTED (unit-tested) |
| `foundation.py` | `create_app()` factory mounting **health only** | IMPLEMENTED (unmounted) |

The layered stack consumes the 0016–0019 schema (AI provider/model/alternatives,
price `unit`/`confidence`, `pickup_available`, handover idempotency, 9 roles).
The mounted routers do **not** use these columns — the two layers are out of
sync until the migration of domains onto the layered stack is completed.

### 4.3 Mobile (scaffold + data layer)

- Expo SDK 52 / RN 0.76 / TypeScript; `App.tsx` is a placeholder; **no screens**.
- Pure-TS data layer (snake_case): UUID v4, idempotency keys, outbox `SyncQueue`,
  `SyncService`, `SyncApi`, local SQLite schema (declared), i18n (`en` + `hi`).
- **`expo-sqlite` adapter NOT written** (interface + `InMemoryStore` only).
- **No Supabase Auth wiring, no token storage, no on-device runtime verification.**
- The earlier camelCase↔snake_case mismatch (ADR-0029) is **resolved** — mobile
  wire types are snake_case.

### 4.4 Web (scaffold)

- Next.js 14, single "Nearby Recyclers" page rendering MapLibre GL over OSM
  raster tiles (no API key), backed by `GET /api/v1/recycler/nearby`.
- **No auth token is sent** (the optional `token` arg is never passed), so the
  endpoint — which requires auth — returns 401 in practice.
- `next build` compiles and type-checks.

## 5. Tests (verified 2026-09-28)

| Target | Count | Kind | Status |
| ------ | ----- | ---- | ------ |
| Backend unit | 72 | pytest, pure (in-memory repos) | PASSING |
| Backend integration | 54 | pytest, live Supabase DB | BLOCKED (no DB) |
| Mobile | 20 | node:test, pure TS | PASSING |
| Web | — | `next build` type-check | PASSING |

## 6. Gap analysis

### 6.1 Blocking / high

| # | Gap | Detail |
| - | --- | ------ |
| G-1 | **No live DB** | 54 integration tests and all PostGIS/HTTP runtime hang on connect; nothing end-to-end is exercisable until `DATABASE_URL` points at a real Supabase project. |
| G-2 | **Role model drift (6 → 9)** | Migrations seed 9 roles (0019 renames `picker→collector`, `platform_admin→super_admin`; adds `support`/`operations_admin`/`data_ai_admin`). The layered `models/role.py` implements 9 with a hierarchy, but the **mounted routers still use the 6 legacy codes** (`picker`, `platform_admin`). |
| G-3 | **Two backend structures out of sync** | Mounted routers (inline SQL, 6 roles, pre-0016 schema) vs layered stack (services/repositories, 9 roles, 0016–0019). Domains must migrate onto the layered stack or be reconciled. |
| G-4 | **Org isolation not wired** | `org_scope` exists and is unit-tested, but is not applied to org-scoped endpoints (FR-003). |
| G-5 | **Web sends no auth token** | `/recycler/nearby` requires auth; the web page calls it with no `Authorization` header, so the demo returns 401. |

### 6.2 Missing (planned but not built)

| # | Gap | Target phase |
| - | --- | ------------ |
| G-6 | Mobile UI (capture / lots / sync-status screens) | 7 |
| G-7 | Mobile auth (Supabase + token storage) | 7 |
| G-8 | Mobile `expo-sqlite` adapter | 7 |
| G-9 | Real AI provider (OpenAI/Anthropic/self-hosted) | 3 |
| G-10 | Web auth + dashboards | 8 |
| G-11 | Redis wiring (rate limit/cache/jobs) | 9 |
| G-12 | CI/CD pipeline | 9 |
| G-13 | `price_history` derivation worker | 4 |
| G-14 | Recycler status-flip worker (`verified → expiring → expired`) | 4 |
| G-15 | Escalation workflow (recycler/admin review) | 5 |
| G-16 | i18n content (6 of 8 locales) | 7 |
| G-17 | `material_image` metadata in batch sync | 6/7 |

### 6.3 Defects / hygiene

| # | Defect | Severity |
| - | ------ | -------- |
| G-18 | `README.md` status banner ("Phase 0 — Foundation") contradicts the implemented backend | Medium |
| G-19 | `.env.example` previously listed unused `JWT_SECRET`/`JWT_ALGORITHM` (ADR-0031) — verify removal | Low |

> Note: the merge-conflict markers previously reported in `README.md`/`.gitignore`
> have been **resolved** (ADR-0030); `README.md` is now clean but its status
> banner is stale.

### 6.4 Partially implemented (external dependencies)

| # | Item | What's missing |
| - | ---- | -------------- |
| G-20 | Cloudinary signed upload | returns 503 without creds; never exercised against Cloudinary |
| G-21 | Rate limiting | in-memory only; not shared across instances |

## 7. Dependency map

```
mobile/src/sync ──► POST /api/v1/sync ──► app/routers/sync.py ──► Supabase PG
mobile screens (todo) ──► Supabase Auth ──► token store ──► ApiClient
mobile screens (todo) ──► expo-sqlite ──► src/db/schema.ts

web/app/page ──► web/src/api/client ──► GET /api/v1/recycler/nearby ──► PostGIS
                 (⚠ no auth token)

layered: foundation ──► api/health ──► services/health ──► repositories/health ──► PG
mounted:  main ──► routers/* (inline SQL) ──► PG
```

**Key dependency ordering**: taxonomy → lots/items → AI → pricing/verification →
matching → transactions → payments → sync → mobile/web clients → layered
migration.

## 8. Major risks

| # | Risk | Impact | Likelihood |
| - | ---- | ------ | ---------- |
| R-1 | No live DB → integration/PostGIS/auth untested end-to-end | High | Certain (as-built) |
| R-2 | Role-model drift (6 vs 9) between mounted and layered layers | High | Certain (as-built) |
| R-3 | Two backend structures diverge further if left unreconciled | High | Medium |
| R-4 | No real AI provider → classification is manual/reference only | Medium | High |
| R-5 | No CI/CD → regressions undetected | Medium | High |
| R-6 | Cloudinary path untested | Medium | Medium |
| R-7 | Mobile never run on device/emulator | Medium | Medium |
| R-8 | Web demo returns 401 (no token) | Medium | Certain (as-built) |
| R-9 | In-memory rate limiting not shared under scale | Low-Med | Medium |

## 9. Recommended implementation order

1. **Provision a live Supabase DB** and run migrations so the integration suite
   and PostGIS paths can be exercised (unblocks R-1).
2. **Reconcile the role model** (G-2): complete the 6→9 migration across the
   mounted routers or finish migrating domains onto the layered stack.
3. **Finish the backend layering migration** (G-3): migrate routers onto
   `services`/`repositories` and mount the full app from `foundation.py`.
4. **Wire `org_scope`** into org-scoped endpoints (G-4, FR-003).
5. **Web auth token** (G-5): pass a Supabase JWT to `/recycler/nearby`.
6. **Mobile capture loop** (G-6, G-7, G-8, G-17): Supabase auth + token storage,
   `expo-sqlite` adapter, capture/lots/sync-status screens, image metadata sync.
7. **Web auth + dashboards** (G-10).
8. **Operational hardening** (G-11, G-12, G-21): Redis, CI/CD, staging.
9. **AI provider + media validation** (G-9, G-20): register a real provider,
   provision Cloudinary, validate signed upload.
10. **Recycler/pricing jobs** (G-13, G-14, G-15).
11. **Content completeness** (G-16): remaining six locales.
12. **README refresh** (G-18).

## 10. Documentation

- [Requirements](02-requirements.md)
- [Requirement Traceability Matrix](03-requirement-traceability-matrix.md)
- [Database Design](05-database-design.md)
- [API Design](06-api-design.md)
- [Mobile Architecture](07-mobile-architecture.md)
- [Offline Sync](08-offline-sync.md)
- [AI Architecture](09-ai-architecture.md)
- [Pricing Engine](10-pricing-engine.md)
- [Recycler Verification](11-recycler-verification.md)
- [Transaction Traceability](12-transaction-traceability.md)
- [Security](13-security.md)
- [Testing Strategy](14-testing-strategy.md)
- [Deployment](15-deployment.md)
- [Field Pilot](16-field-pilot.md)
- [Dataset Strategy](17-dataset-strategy.md)
- [Decision Log](18-decision-log.md)
- [FINAL_STATUS](FINAL_STATUS.md)
