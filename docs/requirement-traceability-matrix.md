# Requirement Traceability Matrix (RTM)

> Tracks each requirement to its source area and the phase in which it will be
> implemented. **Status is never advanced without inspecting/verifying the
> implementation.**

Status legend:

- **Planned** — captured, not started.
- **In progress** — partial implementation exists; remaining work is deferred.
- **Schema-ready** — data model exists and is verified in the live database;
  behavior/API not yet built.
- **Implemented** — code exists and has been validated (not asserted without
  inspection).

| ID | Area | Phase | Status |
| -- | ---- | ----- | ------ |
| FR-USER-01 | Users & roles | 2 | Implemented (roles seeded; RBAC endpoint) |
| FR-USER-02 | Users & roles | 2 | Implemented (`require_role` + `org_scope`, tested) |
| FR-USER-03 | Users & roles | 2 | Implemented (multi-role `user_roles` loaded into principal) |
| FR-I18N-01 | Localization | 7 | In progress (8 locales scaffolded; en+hi seeded) |
| FR-I18N-02 | Localization | 7 | In progress (collector categories en+hi; backend `?locale=`) |
| FR-UX-01 | Collector UX | 7 | In progress (simple collector categories defined) |
| FR-UX-02 | Collector UX | 7 | In progress (14 collector categories defined) |
| FR-UX-03 | Collector UX | 3 | Implemented (`kind` captured on items; applied from category on confirm/correct) |
| FR-AI-01 | AI | 3 | In progress (classify endpoints + `ai_decisions`; real provider TODO) |
| FR-AI-02 | AI | 3 | In progress (confidence modeled + returned; real AI TODO) |
| FR-AI-03 | AI | 3 | In progress (`detected_material_types` field; real detection TODO) |
| FR-AI-04 | AI | 3 | Planned (valuation assist — Phase 4) |
| FR-AI-05 | AI | 3 | In progress (`quality_flags` field + provider hook; real model TODO) |
| FR-AI-06 | AI | 3 | In progress (confirm flow + threshold logic; real AI TODO) |
| FR-AI-07 | AI | 3 | Implemented (manual/"I don't know" path works end-to-end) |
| FR-AI-08 | AI | 5 | Planned (recycler/admin review escalation) |
| FR-AI-09 | AI | 3 | Implemented (corrections stored as training candidates, tested) |
| FR-AI-10 | AI | 3 | Implemented (provider contract forbids exact-composition claims) |
| FR-PRICE-01 | Pricing | 4 | Implemented (no hard-coded price; observation-driven) |
| FR-PRICE-02 | Pricing | 4 | Implemented (contextual fields modeled) |
| FR-PRICE-03 | Pricing | 4 | Implemented (provenance: source, user, buyer, location) |
| FR-PRICE-04 | Pricing | 4 | Implemented (collector_entry is `unverified`) |
| FR-VERIF-01 | Recycler verification | 4 | Implemented (default `pending`; not auto-verified) |
| FR-VERIF-02 | Recycler verification | 4 | Implemented (authorization fields via onboarding) |
| FR-VERIF-03 | Recycler verification | 4 | Implemented (5 statuses enforced) |
| FR-VERIF-04 | Recycler verification | 4 | Implemented (expired excluded from `/recycler/verified`, tested) |
| FR-MATCH-01 | Matching | 5 | Implemented (authorization + acceptance + distance + score) |
| FR-MATCH-02 | Matching | 5 | Implemented (composite score, never gross price) |
| FR-TXN-01 | Transactions | 5 | Implemented (state machine with legal transitions) |
| FR-TXN-02 | Transactions | 5 | Implemented (transitions create events + audit) |
| FR-WEIGHT-01 | Weight | 5 | Implemented (declared/pickup/final) |
| FR-PAY-01 | Payment | 5 | Implemented (cash/upi/bank_transfer) |
| FR-PAY-02 | Payment | 5 | Implemented (digital payment not mandatory) |
| FR-SYNC-01 | Offline sync | 7 | In progress (local SQLite schema defined; native wiring pending) |
| FR-SYNC-02 | Offline sync | 7 | In progress (sync queue + client + backend; capture/safety/price-cache screens pending) |
| FR-SYNC-03 | Offline sync | 6 | Implemented (backend authoritative) |
| FR-SYNC-04 | Offline sync | 6 | Implemented (idempotent replay, no duplicates, tested) |
| FR-MEDIA-01 | Media | 3 | Implemented (Cloudinary refs only; no binary columns) |
| FR-MEDIA-02 | Media | 3 | In progress (metadata storage done; signed upload needs Cloudinary creds) |
| FR-GEO-01 | Geospatial | 8 | Implemented (PostGIS used for nearby search) |
| FR-GEO-02 | Geospatial | 8 | Implemented (`geography(Point,4326)` + distance calc) |
| FR-GEO-03 | Geospatial | 8 | Implemented (nearby search + radius + distance, tested) |
| FR-SEC-01 | Security | 9 | Implemented (TLS via Render/Vercel/Supabase, documented) |
| FR-SEC-02 | Security | 2 | Implemented (Supabase JWT verification) |
| FR-SEC-03 | Security | 2 | Implemented (RBAC + org isolation + collector ownership) |
| FR-SEC-04 | Security | 2 | Implemented (Pydantic validation on all request bodies) |
| FR-SEC-05 | Security | 9 | Implemented (rate limiting middleware, tested) |
| FR-SEC-06 | Security | 2 | Implemented (`record_audit` wired to capture/classification) |
| FR-SEC-07 | Security | 3 | Implemented (signed upload + URL-only storage; no binary in DB) |
| FR-SEC-08 | Security | 0 | Implemented (no secrets committed; `.env.example` only) |
| FR-SEC-09 | Security | 2 | Implemented (minimal auto-provision; documented) |
| FR-SEC-10 | Security | 2 | Implemented (no Aadhaar field in schema or backend) |
| NFR-01 | Non-functional | 7 | In progress (Android config; app not yet device-verified) |
| NFR-02 | Non-functional | 2 | Implemented (backend authoritative) |
| NFR-03 | Non-functional | 3 | Implemented (AI is advisory; corrections are feedback, not ground truth) |
| NFR-04 | Non-functional | all | In progress (adhered to in Phases 0–9) |
| NFR-05 | Non-functional | 0 | Implemented (decision-log.md) |

## Phase status

- **Phase 0 — Foundation**: complete.
- **Phase 1 — Database**: complete (PostGIS schema + seed taxonomy, verified).
- **Phase 2 — Backend core**: complete (auth, RBAC, org isolation, audit, idempotency).
- **Phase 3 — Material capture + AI**: complete (lots/items/images, pluggable
  classification with confirm/correct, Cloudinary metadata). Real AI provider and
  Cloudinary credentials are external TODOs.
- **Phase 4 — Pricing + recycler verification**: complete (provenance-backed
  observations, contextual estimate, expiry-aware recycler verification).
- **Phase 5 — Matching + transactions**: complete (composite-score matching,
  transaction lifecycle state machine, weights, payments).
- **Phase 6 — Offline sync**: complete (batch idempotent sync endpoint with
  replay; client SQLite schema deferred to Phase 7).
- **Phase 7 — Mobile**: foundation complete (Expo scaffold + offline data layer,
  unit-tested). Screens, Supabase auth, and on-device runtime are not yet built.
- **Phase 8 — Web + geospatial**: complete (PostGIS nearby search endpoint +
  Next.js dashboard with MapLibre/OSM map; app builds cleanly).
- **Phase 9 — Security + deployment**: complete (rate limiting, CORS, deployment
  configs, security/deployment/testing/field-pilot docs).
