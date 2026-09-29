# Kabadi Mitra — FINAL STATUS

> Consolidated engineering status, verified against the actual repository on
> 2026-09-28. **No feature is reported as implemented unless it was verified in
> code or by a passing test/build.** Status labels: **IMPLEMENTED** · **PARTIAL**
> · **PLANNED** · **FUTURE** · **NEEDS FIELD VALIDATION**.

## 1. Architecture summary

Approved topology (unchanged):

```
React Native + Expo → SQLite → FastAPI → Supabase PostgreSQL + PostGIS
FastAPI → Cloudinary · Redis · AI Service
Next.js → Vercel → FastAPI
```

The backend is **mid-refactor**: two structures coexist.

- **Mounted (live)** — `app/main.py` + `app/routers/*` (13 routers, 32 endpoints,
  inline SQL, **legacy 6-role** model). Served by `run.py`.
- **Layered (unmounted)** — `app/foundation.py` + `app/{api,services,models,
  repositories,core}` (route→service→repository, **9-role** model with hierarchy,
  migrations 0016–0019). Implemented and unit-tested (72 tests) but only the
  health domain is mounted.

Database: 41 tables, 19 migrations (`0001…0019`).

## 2. Implemented features (verified)

| Area | Detail |
| ---- | ------ |
| Identity / auth | Supabase JWT → JWKS (RS256, `iss`/`aud`), auto-provision `users` |
| RBAC | `require_role(...)` on mounted routers (6 legacy roles); 9-role hierarchy in layered `models/role.py` |
| Material capture | lots, lot items, image metadata (Cloudinary refs only) |
| AI (assistive) | `BaseProvider` + `NullProvider` + `ReferenceProvider`; classify/confirm/correct; confidence tiers; corrections as training candidates |
| Pricing | provenance-backed observations, contextual estimate (`null` when no data) |
| Recycler verification | expiry-aware derived status; expired excluded from matching |
| Matching | composite score (coverage × 60 + proximity), never gross price alone |
| Transactions | explicit state machine + events + audit; weights; payments (cash/upi/bank_transfer) |
| Offline sync (backend) | `POST /api/v1/sync` idempotent batch, ownership-checked |
| Offline data layer (mobile) | snake_case wire types, outbox queue, retry, sync service, in-memory store |
| Geospatial | PostGIS `ST_DWithin`/`ST_Distance` nearby search |
| Web | single "Nearby Recyclers" map page (MapLibre + OSM) |
| Cross-cutting | audit trail, idempotency middleware, in-memory rate limiting |

## 3. Partial features

| Area | What's missing |
| ---- | -------------- |
| Role model | 9 roles seeded + layered model, but **mounted routers still use 6** |
| Backend layering | services/repositories implemented + tested, but **not wired into the mounted HTTP surface** (health only) |
| Org isolation | `org_scope` defined + tested, **not applied to org-scoped endpoints** |
| AI | architecture + reference provider only; **no real model** |
| Media | signed-upload params; **untested without Cloudinary creds** |
| Offline (mobile) | data layer complete; **`expo-sqlite` adapter and screens absent** |
| i18n | `en` + `hi` only (6 locales pending) |
| Rate limiting | in-memory only; not shared across instances |
| Disputes | initiation implemented; **events/resolution pending** |
| Dataset | corrections + price observations collected; quality flags field-only; no export/training pipeline |

## 4. Remaining features (PLANNED / FUTURE)

- Mobile UI: capture / lots / sync-status screens; Supabase Auth + token storage.
- Web auth + dashboards (admin/recycler/aggregator).
- Real AI provider (OpenAI / Anthropic / self-hosted).
- Redis wiring (rate limit / cache / jobs).
- Recycler status-flip and `price_history` derivation workers.
- Escalation workflow (recycler → admin review).
- Quotes / logistics / handover endpoints (schema-ready only).
- Safety content fetch; notifications endpoint (orphan table).
- Platform analytics.
- CI/CD pipeline.

## 5. Known limitations

1. **No live database** — 54 integration tests and all PostGIS/HTTP runtime hang
   on connect; nothing is exercisable end-to-end until `DATABASE_URL` is set.
2. **Role-model drift (6 → 9)** between the mounted and layered backend layers.
3. **Two backend structures out of sync** (inline-SQL routers vs services/repositories).
4. **`org_scope` not wired** to endpoints — a real isolation gap.
5. **Web sends no auth token** to `/recycler/nearby` (which requires auth) — the
   demo returns 401.
6. **Mobile never run on device/emulator** — runtime unverified.
7. **No real AI provider** — classification is manual/reference.
8. **Cloudinary path unverified** (no credentials).
9. **README status banner is stale** ("Phase 0 — Foundation").
10. **Notifications** table has no requirement/endpoint (orphan).

## 6. Test results (verified 2026-09-28)

| Target | Command | Result |
| ------ | ------- | ------ |
| Backend unit | `.venv\Scripts\python.exe -m pytest tests/unit -q` | **72 passed** |
| Backend integration | `.venv\Scripts\python.exe -m pytest -q` | **BLOCKED** — 54 tests hang (no live DB) |
| Mobile | `npm test` | **20 passed** |
| Mobile typecheck | `npm run typecheck` | clean |
| Web build | `npm run build` | compiles + type-checks |

## 7. RTM coverage

- 59 functional + technical requirements **IMPLEMENTED**; 15 **PARTIAL**;
  8 **NOT IMPLEMENTED**; 1 **FUTURE** (83 total).
- Cross-cutting blockers: HTTP/API + PostGIS integration (no live DB);
  mobile on-device runtime; real AI provider; Cloudinary signed upload.
- See [03-requirement-traceability-matrix.md](03-requirement-traceability-matrix.md).

## 8. Security status

- **IMPLEMENTED**: Supabase JWT auth; RBAC; audit trail; idempotency; input
  validation; env-only secrets; no Aadhaar; data minimization; error sanitization.
- **PARTIAL**: org isolation (`org_scope` not wired to endpoints); rate limiting
  (in-memory only); Cloudinary signed upload (untested).
- **Open**: TLS is host-terminated (Render/Vercel/Supabase/Cloudinary) — no local
  TLS testing.

## 9. Offline status

- **IMPLEMENTED** (data layer, tested): snake_case wire contract; outbox queue;
  retry policy; sync orchestrator; idempotency keys (`KC-<E>-<YYMMDD>-<NNNNNN>`);
  offline capability map; read-only cache.
- **PARTIAL**: local SQLite DDL declared but **no `expo-sqlite` adapter**;
  no screens; no on-device runtime.
- The earlier camelCase↔snake_case mismatch is **resolved** (ADR-0029).

## 10. AI status

- **IMPLEMENTED** (tested): provider abstraction, `NullProvider` +
  `ReferenceProvider`, confidence tiers (HIGH/MEDIUM/LOW), decision logging,
  corrections-as-training-candidates, indicative valuation.
- **PARTIAL**: `quality_flags`/`detected_material_types`/`valuation_hint` fields
  exist but are not populated without a real provider.
- **NEEDS FIELD VALIDATION**: no real model (OpenAI/Anthropic/self-hosted).
- AI is **assistive by construction** — never persisted as fact without human
  confirm/correct.

## 11. Field-validation status

**NEEDS FIELD VALIDATION** across the board — the product has not been run in a
real pilot:

- Mobile on-device `expo-sqlite` + connectivity (no device/emulator run).
- Real AI provider.
- Cloudinary signed upload.
- End-to-end HTTP/PostGIS (no live DB).
- Field pilot parameters (sample size, duration, payment acceptability, service
  areas) are **placeholders** in [16-field-pilot.md](16-field-pilot.md).

## 12. Deployment status

- **Config present, not deployed**: `render.yaml` (backend), `web/vercel.json`
  (web), `.env.example` (empty placeholders). No credentials are provisioned; no
  deployment has been performed.
- **No CI/CD pipeline**; no staging environment.

## 13. SIH demo readiness checklist

> Honest verdict: **NOT demo-ready end-to-end.** No live database means the
> collector workflow (capture → classify → match → transaction → payment) has
> **never been exercised against real services**, and the mobile app has no UI.

| # | Item | Status |
| - | ---- | ------ |
| 1 | Live Supabase DB provisioned + migrations applied | ❌ Not done |
| 2 | Backend boots against the DB (`/health/ready` = 200) | ❌ Blocked (no DB) |
| 3 | Collector capture → classify → confirm/correct | ⚠️ Code+tests present; not run against live DB |
| 4 | Verified recycler matching | ⚠️ Code+tests present; PostGIS not run against live data |
| 5 | Transaction lifecycle → payment | ⚠️ Code+tests present; not run against live DB |
| 6 | Offline capture → sync round-trip | ⚠️ Data layer tested; no screens / on-device runtime |
| 7 | Mobile app runs on device/emulator | ❌ Not done |
| 8 | Web map shows nearby recyclers | ⚠️ Builds; returns 401 (no auth token sent) |
| 9 | Real AI classification | ❌ No provider configured |
| 10 | Cloudinary image upload | ❌ No credentials |
| 11 | CI/CD or reproducible build | ❌ Not done |
| 12 | README reflects as-built state | ❌ Stale ("Phase 0") |

**Minimum to reach a credible demo**:

1. Provision Supabase PostGIS + apply 19 migrations; set `DATABASE_URL`.
2. Run the 54 integration tests against it (green).
3. Set `SUPABASE_*` for JWT auth; verify `/me` and a collector flow.
4. Wire a token into the web map (or temporarily allow it unauthenticated for a
   demo build).
5. Stand up at least the capture/lots/sync-status screens in mobile.

The backend's business logic (matching, pricing, verification, transactions,
sync) is substantially built and unit-tested — but **unit tests do not equal a
working demo**, and no workflow has been validated end-to-end yet.
