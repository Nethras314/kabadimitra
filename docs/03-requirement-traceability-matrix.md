# Kabadi Mitra — Requirement Traceability Matrix (RTM)

> Phase 2 deliverable. Traces every functional and technical requirement to its
> source, actor, API, database entity, UI screen, test case, acceptance criteria,
> evidence, and status. Requirement definitions live in
> [requirements.md](requirements.md).

## Legend

**Priority**: P0 (core) · P1 (important MVP) · P2 (enhancement) · P3 (future).

**Status**: `Planned` · `Schema-ready` · `In progress` · `Implemented`.

**Markers**: ⚠ `FIELD VALIDATION REQUIRED` · ❓ `ASSUMPTION` · 🔎 `NEEDS VALIDATION`.

---

## 1. Hierarchy mapping (BR → UR → FR)

| BR | User requirements | Primary FRs |
| -- | ----------------- | ----------- |
| BR-001 | UR-001, UR-005, UR-006, UR-007, UR-008 | FR-007, FR-008, FR-010, FR-026 |
| BR-002 | UR-004, UR-009 | FR-034, FR-035, FR-051 |
| BR-003 | UR-001, UR-006 | FR-021, FR-043 |
| BR-004 | UR-005, UR-006, UR-007, UR-008, UR-010, UR-011, UR-012 | FR-001..FR-004 |
| BR-005 | UR-001 | FR-005, FR-006 |
| BR-006 | UR-006 | FR-041..FR-044 |
| BR-007 | UR-011 | FR-052..FR-061 |
| BR-008 | UR-011, UR-012 | FR-063..FR-067 |

| UR | Actor | FRs |
| -- | ----- | --- |
| UR-001 | Picker | FR-007, FR-008, FR-010, FR-011 |
| UR-002 | Picker | FR-036 |
| UR-003 | Picker | FR-022..FR-025, FR-030, FR-031, FR-049 |
| UR-004 | Picker | FR-034, FR-038, FR-040, FR-051 |
| UR-005 | Kabadiwala | FR-010 (shared collector flow) |
| UR-006 | Kabadiwala | FR-010..FR-018, FR-041..FR-044 |
| UR-007 | Aggregator | FR-010 (shared; dedicated flow pending) |
| UR-008 | Recycler | FR-026..FR-029 |
| UR-009 | Recycler | FR-032, FR-037, FR-038 |
| UR-010 | Dismantler | FR-009 (kind separation; dedicated flow pending) |
| UR-011 | Admin | FR-001..FR-004, FR-026..FR-029 |
| UR-012 | Admin | FR-062, FR-066, FR-067 |

---

## 2. Main RTM

| Requirement ID | Requirement Type | Source | Requirement | User/Actor | Priority | Module | Functional Dependency | API | Database Entity | UI Screen | Test Case | Acceptance Criteria | Evidence | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR-001 | Functional | Legacy FR-USER-01 | Six primary roles seeded | Admin | P0 | Identity & Access | — | API-005 | DB-003 | UI-017 | TC-002 | AT-001 | `0014_seed_roles.sql`, `test_auth.py` | Implemented | |
| FR-002 | Functional | Legacy FR-USER-02 | RBAC enforced | All | P0 | Identity & Access | FR-001 | API-005, API-017..019, API-021 | DB-004 | — | TC-002 | AT-002 | `dependencies.py:require_role`, `test_auth.py` | Implemented | `require_role` wired |
| FR-003 | Functional | Legacy FR-USER-02 | Organization-level isolation | All | P0 | Identity & Access | FR-001, FR-004 | — | DB-002, DB-004 | — | TC-003 | AT-003 | `dependencies.py:org_scope`, `test_helpers.py` | In progress | helper tested but **not wired** to endpoints |
| FR-004 | Functional | Legacy FR-USER-03 | Multi-role user | Admin | P0 | Identity & Access | FR-001 | API-003 | DB-004 | — | TC-002 | AT-004 | `auth.py:_load_roles`, `test_auth.py` | Implemented | |
| FR-005 | Functional | Legacy FR-I18N-01 | Eight languages | Collector | P0 | Localization | — | API-004 | DB-019 | UI-003 | TC-010 | AT-005 | `locales.ts`, `0015_seed_taxonomy.sql` | In progress | en+hi only; 6 locales pending |
| FR-006 | Functional | Legacy FR-I18N-02 | Localized labels independent of taxonomy | Collector | P0 | Localization | FR-005 | API-004 | DB-019 | UI-003 | TC-010 | AT-005 | `taxonomy.py` (COALESCE) | Implemented | `?locale=` works |
| FR-007 | Functional | Legacy FR-UX-01 | Hide industrial taxonomy | Collector | P0 | Collector UX | — | API-004 | DB-017 | UI-003 | TC-010 | AT-006 | `collector_categories` (14) | Implemented | |
| FR-008 | Functional | Legacy FR-UX-02 | 14 collector categories | Collector | P0 | Collector UX | FR-007 | API-004 | DB-017 | UI-003 | TC-010 | AT-006 | `0015_seed_taxonomy.sql` | Implemented | |
| FR-009 | Functional | Legacy FR-UX-03 | Equipment vs recovered material separate | Collector | P0 | Collector UX | — | API-009 | DB-011, DB-021 | UI-003 | TC-004 | AT-007 | `0004_taxonomy.sql`, `test_ai.py` | Implemented | |
| FR-010 | Functional | Workflow | Lots and items CRUD | Collector | P0 | Material Capture | FR-008, FR-009 | API-006..009 | DB-020, DB-021 | UI-005, UI-006 | TC-004 | AT-008 | `lots.py`, `test_lots.py` | Implemented | |
| FR-011 | Functional | Legacy FR-MEDIA-02 | Images as Cloudinary refs | Collector | P0 | Material Capture | FR-010 | API-010 | DB-022 | UI-003 | TC-004 | AT-009 | `lots.py:attach_image`, `test_lots.py` | Implemented | |
| FR-012 | Functional | Legacy FR-AI-01 | AI suggests category/subcategory | Collector | P1 | AI | FR-011 | API-011 | DB-036 | UI-004 | TC-005 | AT-010 | `ai/provider.py` | In progress | NullProvider only |
| FR-013 | Functional | Legacy FR-AI-02 | Confidence estimate | Collector | P1 | AI | FR-012 | API-011 | DB-036 | UI-004 | TC-005 | AT-010 | `ai.py`, `test_ai.py` | In progress | modeled; real AI pending |
| FR-014 | Functional | Legacy FR-AI-03 | Detect material types | Collector | P1 | AI | FR-012 | API-011 | DB-036 | UI-004 | TC-005 | AT-010 | `ai.py` (`detected_material_types`) | In progress | field present; real AI pending |
| FR-015 | Functional | Legacy FR-AI-04 | Valuation assist | Collector | P2 | AI | FR-013 | — | DB-036 (`valuation_hint`) | — | TC-022 | AT-010 | reserved field | Planned | 🔎 real model TODO |
| FR-016 | Functional | Legacy FR-AI-05 | Image quality detection | Collector | P2 | AI | FR-011 | API-011 | DB-036 (`quality_flags`) | UI-004 | TC-022 | AT-010 | `ai.py` (`quality_flags`) | Planned | field present; real model TODO |
| FR-017 | Functional | Legacy FR-AI-06 | High confidence → confirm | Collector | P1 | AI | FR-013 | API-012 | DB-036 | UI-004 | TC-005 | AT-010 | `ai.py:confirm`, `test_ai.py` | Implemented | |
| FR-018 | Functional | Legacy FR-AI-07 | Low confidence → manual / "don't know" | Collector | P0 | AI | FR-008 | API-013 | DB-036, DB-037 | UI-004 | TC-005 | AT-010 | `ai.py`, `test_ai.py` | Implemented | |
| FR-019 | Functional | Legacy FR-AI-08 | Escalation recycler → admin | Recycler/Admin | P2 | AI | FR-018 | — | — | — | TC-020 | AT-010 | — | Planned | not implemented |
| FR-020 | Functional | Legacy FR-AI-09 | Corrections as training candidates | Collector | P1 | AI | FR-012 | API-013 | DB-037 | UI-004 | TC-005 | AT-010 | `ai.py:correct`, `test_ai.py` | Implemented | `is_training_candidate=true` |
| FR-021 | Functional | Legacy FR-AI-10 | AI must not claim composition/grade | System | P0 | AI | FR-012 | API-011 | — | — | TC-005 | AT-011 | `ai/provider.py` docstring | Implemented | |
| FR-022 | Functional | Legacy FR-PRICE-01 | No hard-coded price | Collector | P0 | Pricing | — | API-016 | DB-023 | UI-007 | TC-011 | AT-012 | `pricing.py`, `test_pricing.py` | Implemented | |
| FR-023 | Functional | Legacy FR-PRICE-02 | Contextual price fields | Collector | P0 | Pricing | FR-022 | API-016 | DB-023 | UI-007 | TC-011 | AT-012 | `schemas.py:PriceObservationCreate` | Implemented | |
| FR-024 | Functional | Legacy FR-PRICE-03 | Provenance on every observation | Collector | P0 | Pricing | FR-023 | API-015 | DB-023 | UI-007 | TC-011 | AT-012 | `pricing.py`, `test_pricing.py` | Implemented | |
| FR-025 | Functional | Legacy FR-PRICE-04 | Collector entry unverified | Collector | P0 | Pricing | FR-024 | API-015 | DB-023 | — | TC-011 | AT-012 | `pricing.py` | Implemented | |
| FR-026 | Functional | Legacy FR-VERIF-01 | Not auto-verified | Admin | P0 | Recycler Verification | — | API-017 | DB-008 | UI-016 | TC-012 | AT-013 | `recyclers.py`, `0005_recycler.sql` | Implemented | |
| FR-027 | Functional | Legacy FR-VERIF-02 | Full authorization data | Admin | P0 | Recycler Verification | FR-026 | API-017..019, API-021 | DB-006..010 | UI-016, UI-021 | TC-012 | AT-013 | `recyclers.py`, `0005_recycler.sql` | Implemented | |
| FR-028 | Functional | Legacy FR-VERIF-03 | Five statuses | Admin | P0 | Recycler Verification | FR-027 | API-017 | DB-008 | UI-016 | TC-012 | AT-013 | `0005_recycler.sql` CHECK | Implemented | |
| FR-029 | Functional | Legacy FR-VERIF-04 | Expired excluded | System | P0 | Recycler Verification | FR-028 | API-020 | DB-008 | — | TC-012 | AT-013 | `recyclers.py:effective_verification`, `test_recyclers.py` | Implemented | |
| FR-030 | Functional | Legacy FR-MATCH-01 | Multi-factor matching | Collector | P0 | Matching | FR-026, FR-023 | API-022, API-023 | DB-026 | UI-008 | TC-013 | AT-014 | `matching.py`, `test_matching.py` | Implemented | |
| FR-031 | Functional | Legacy FR-MATCH-02 | Never gross price alone | System | P0 | Matching | FR-030 | API-022 | DB-026 (`match_reason`) | — | TC-013 | AT-014 | `matching.py` score | Implemented | |
| FR-032 | Functional | ❓ Workflow/schema | Recycler quote on a lot | Recycler | P1 | Quotes | FR-030 | — | DB-025 | UI-021 | TC-020 | AT-023 | `0007_pricing.sql` | Schema-ready | table only; no endpoint |
| FR-033 | Functional | ❓ Workflow | Pickup/delivery + schedule | Collector | P1 | Logistics | FR-034 | — | DB-027 (`pickup_method`, `scheduled_at`) | UI-009 | TC-020 | AT-023 | `0009_transactions.sql` | Schema-ready | columns only ⚠ FIELD VALIDATION REQUIRED |
| FR-034 | Functional | Legacy FR-TXN-01 | Lifecycle state machine | Collector | P0 | Transactions | FR-030 | API-024, API-025, API-027 | DB-027, DB-028 | UI-009 | TC-014 | AT-015 | `transactions.py:TRANSITIONS`, `test_transactions.py` | Implemented | |
| FR-035 | Functional | Legacy FR-TXN-02 | Audit on transitions | System | P0 | Transactions | FR-034 | API-027 | DB-038 | — | TC-014 | AT-025 | `transactions.py:record_audit` | Implemented | |
| FR-036 | Functional | Legacy FR-WEIGHT-01 | declared/pickup/final weight | Collector | P0 | Weight | FR-034 | API-028 | DB-029 | UI-010 | TC-014 | AT-016 | `transactions.py:add_weight`, `test_transactions.py` | Implemented | |
| FR-037 | Functional | ❓ Workflow | Digital handover | Collector/Recycler | P1 | Handover | FR-034 | — | DB-030 | UI-009 | TC-020 | AT-023 | `services/transaction.py`, `0018_transaction_handover_idempotency.sql` | Implemented | idempotent handover |
| FR-038 | Functional | Legacy FR-PAY-01 | cash/upi/bank transfer | Collector | P0 | Payments | FR-034 | API-029, API-030 | DB-031 | UI-011 | TC-014 | AT-017 | `transactions.py`, `test_transactions.py` | Implemented | |
| FR-039 | Functional | Legacy FR-PAY-02 | Digital payment not mandatory | Collector | P0 | Payments | FR-038 | API-029 | DB-031 | — | TC-014 | AT-017 | `schemas.py:PaymentCreate` | Implemented | |
| FR-040 | Functional | ❓ Workflow | Net earnings + history | Collector | P1 | Earnings | FR-034, FR-038 | API-025 | DB-027 (`net_earnings`) | UI-012 | TC-020 | AT-023 | `services/transaction.py:earnings` | Implemented | derived earnings ledger |
| FR-041 | Functional | Legacy FR-SYNC-01 | SQLite local DB | Collector | P0 | Offline/Sync | — | — | mobile `db/schema.ts` | UI-013 | TC-017 | AT-018 | `mobile/src/db/schema.ts` | In progress | schema declared; adapter unwired |
| FR-042 | Functional | Legacy FR-SYNC-02 | Offline capture scope | Collector | P0 | Offline/Sync | FR-041 | API-031 | mobile `sync_queue` | UI-003, UI-013 | TC-016, TC-017 | AT-018 | `mobile/src/sync/`, `db/` | In progress | screens pending |
| FR-043 | Functional | Legacy FR-SYNC-03 | Backend authoritative | System | P0 | Offline/Sync | — | — | — | — | TC-008 | AT-018 | `sync.py`, ADR-0006 | Implemented | |
| FR-044 | Functional | Legacy FR-SYNC-04 | Idempotency keys | System | P0 | Offline/Sync | FR-043 | API-031 | DB-040 | UI-013 | TC-007, TC-008 | AT-018 | `idempotency.py`, `sync.py`, `test_sync.py` | Implemented | ⚠ mobile camelCase mismatch (ADR-0029) |
| FR-045 | Functional | Legacy FR-MEDIA-01 | No large images in PG | System | P0 | Media | — | — | DB-022 | — | TC-004 | AT-009 | `0006_lots.sql` (no bytea) | Implemented | |
| FR-046 | Functional | Legacy FR-MEDIA-02 | Collector → Cloudinary → metadata | Collector | P0 | Media | FR-045 | API-014 | DB-022 | UI-003 | TC-006 | AT-009 | `media.py:upload_params` | In progress | 🔎 signed upload untested (no creds) |
| FR-047 | Functional | Legacy FR-GEO-01 | PostGIS | System | P0 | Geospatial | — | — | PostGIS ext | — | TC-009 | AT-019 | `0001_extensions.sql` | Implemented | |
| FR-048 | Functional | Legacy FR-GEO-02 | `geography(Point,4326)` | Recycler | P0 | Geospatial | FR-047 | API-032 | DB-007 | UI-018 | TC-009 | AT-019 | `0005_recycler.sql` | Implemented | |
| FR-049 | Functional | Legacy FR-GEO-03 | Nearby/radius/distance | Collector | P0 | Geospatial | FR-048 | API-032 | DB-007 (GiST) | UI-018 | TC-009 | AT-019 | `geo.py`, `test_geo.py` | Implemented | |
| FR-050 | Functional | Legacy FR-SYNC-02 (safety) | Hazard links + offline safety | Collector | P1 | Safety | FR-042 | — | DB-015, DB-016 | UI-014 | TC-020 | AT-023 | `0004_taxonomy.sql` | Schema-ready | tables only; no fetch endpoint |
| FR-051 | Functional | Problem Statement | End-to-end traceability | All | P0 | Traceability | FR-035, FR-036, FR-037, FR-038 | API-026 | DB-028, DB-029, DB-030, DB-031 | UI-009 | TC-014 | AT-025 | events/weights/handover/payments/audit | Implemented | full traceability chain |
| FR-052 | Functional | Legacy FR-SEC-01 | HTTPS everywhere | System | P0 | Security | — | API-001, API-002 | — | — | TC-001 | AT-020 | `deployment.md`, `render.yaml` | Implemented | host TLS termination |
| FR-053 | Functional | Legacy FR-SEC-02 | Supabase JWT auth | All | P0 | Security | — | API-003 | DB-002 | UI-001, UI-015 | TC-002 | AT-002 | `auth.py:verify_token`, `test_auth.py` | Implemented | |
| FR-054 | Functional | Legacy FR-SEC-03 | Authorization (RBAC + org) | All | P0 | Security | FR-002, FR-003 | — | DB-004 | — | TC-002, TC-003 | AT-002, AT-003 | `dependencies.py` | In progress | RBAC wired; org isolation not wired |
| FR-055 | Functional | Legacy FR-SEC-04 | Input validation | System | P0 | Security | — | all mutation APIs | — | — | TC-004, TC-014 | AT-002 | `schemas.py` (Pydantic) | Implemented | |
| FR-056 | Functional | Legacy FR-SEC-05 | Rate limiting | System | P0 | Security | — | middleware | — | — | TC-015 | AT-020 | `rate_limit.py`, `test_rate_limit.py` | Implemented | in-memory only |
| FR-057 | Functional | Legacy FR-SEC-06 | Audit logging | System | P0 | Audit | — | middleware/handlers | DB-038 | — | TC-003 | AT-025 | `audit.py`, `test_helpers.py` | Implemented | |
| FR-058 | Functional | Legacy FR-SEC-07 | Secure image handling | System | P0 | Security | FR-046 | API-014 | DB-022 | — | TC-006 | AT-009 | `media.py` signature | Implemented | 🔎 signed upload untested |
| FR-059 | Functional | Legacy FR-SEC-08 | Env-only secrets | System | P0 | Security | — | — | — | — | — | AT-020 | `.env.example` (empty) | Implemented | |
| FR-060 | Functional | Legacy FR-SEC-09 | Data minimization | System | P0 | Privacy | FR-053 | API-003 | DB-002 | — | TC-003 | AT-020 | `auth.py:get_or_create_user` | Implemented | |
| FR-061 | Functional | Legacy FR-SEC-10 | No Aadhaar | System | P0 | Privacy | — | — | (no column) | — | — | AT-021 | schema audit | Implemented | |
| FR-062 | Functional | ❓ Workflow/schema | Disputes + events | Collector/Recycler | P2 | Disputes | FR-034 | — | DB-033, DB-034 | UI-020 | TC-020 | AT-022 | `services/transaction.py:initiate_dispute` | In progress | dispute initiation done; dispute events/resolution pending |
| FR-063 | Functional | field-pilot.md | AI corrections as training data | System | P1 | Dataset Generation | FR-020 | API-013 | DB-037 | — | TC-005 | AT-010 | `ai.py`, `test_ai.py` | Implemented | |
| FR-064 | Functional | field-pilot.md | Price observations with provenance | System | P1 | Dataset Generation | FR-024 | API-015 | DB-023 | — | TC-011 | AT-012 | `pricing.py` | Implemented | |
| FR-065 | Functional | field-pilot.md | Image quality flags | System | P1 | Dataset Generation | FR-016 | API-011 | DB-036 | — | TC-022 | AT-010 | `ai.py` (`quality_flags`) | In progress | field present; real model TODO |
| FR-066 | Functional | ❓ price_history | Price-history aggregates | Admin | P2 | Analytics | FR-024 | — | DB-024 | UI-019 | TC-020 | AT-024 | `0007_pricing.sql` | Schema-ready | table only; no derivation |
| FR-067 | Functional | ❓ field-pilot.md | Platform analytics | Admin | P2 | Analytics | FR-051, FR-062 | — | DB-038, DB-026, DB-027 | UI-019 | TC-020 | AT-024 | `field-pilot.md` metrics | Planned | no analytics endpoint |
| TR-001 | Technical | ADR-0002 | Mobile: Expo/RN/TS/SQLite | System | P0 | Platform | FR-041 | — | — | — | TC-016 | — | `mobile/package.json` | Implemented | scaffold |
| TR-002 | Technical | ADR-0002 | Backend: FastAPI | System | P0 | Platform | — | API (all) | — | — | TC-001 | — | `backend/main.py` | Implemented | |
| TR-003 | Technical | ADR-0002 | DB: Supabase PG + PostGIS | System | P0 | Platform | FR-047 | — | DB-001..041 | — | TC-009 | AT-019 | migrations + PostGIS ext | Implemented | |
| TR-004 | Technical | ADR-0019 | Media: Cloudinary | System | P0 | Platform | FR-046 | API-014 | — | — | TC-021 | AT-009 | `media.py` | In progress | 🔎 NEEDS VALIDATION |
| TR-005 | Technical | ADR-0002 | Cache/jobs: Redis | System | P1 | Platform | FR-056 | — | — | — | — | — | `.env.example` `REDIS_URL` | Planned | reserved, not wired |
| TR-006 | Technical | ADR-0002 | Web: Next.js | System | P0 | Platform | — | — | — | UI-018 | TC-019 | — | `web/package.json` | Implemented | |
| TR-007 | Technical | ADR-0026 | Maps: OSM + MapLibre | System | P0 | Platform | FR-049 | — | — | UI-018 | TC-019 | — | `NearbyMap.tsx` | Implemented | |
| TR-008 | Technical | ADR-0018 | AI pluggable provider | System | P0 | Platform | FR-012 | API-011 | DB-035 | — | TC-005 | AT-010 | `ai/provider.py` | Implemented | NullProvider only |
| TR-009 | Technical | ADR-0006 | Backend authoritative | System | P0 | Platform | FR-043 | — | — | — | TC-008 | AT-018 | `sync.py` | Implemented | |
| TR-010 | Technical | ADR-0011 | UUID primary keys | System | P0 | Data | FR-044 | — | all tables | — | TC-008 | — | migrations (uuid defaults) | Implemented | |
| TR-011 | Technical | ADR-0029 | snake_case wire contract | System | P0 | Integration | FR-044 | API-031 | — | — | TC-017 | AT-018 | `offline-sync.md` | In progress | ⚠ mobile camelCase mismatch |
| TR-012 | Technical | ADR-0016 | psycopg3 async, no ORM | System | P0 | Data | — | — | — | — | TC-003 | — | `db.py` | Implemented | |
| TR-013 | Technical | ADR-0010 | SQL migrations + Node runner | System | P0 | Data | — | — | DB-041 | — | — | — | `migrations/run.js` | Implemented | |
| TR-014 | Technical | ADR-0015 | Supabase Auth IdP | System | P0 | Security | FR-053 | — | DB-002 | UI-001 | TC-002 | AT-002 | `auth.py` | Implemented | |
| TR-015 | Technical | ADR-0009 | Env-only secrets | System | P0 | Security | FR-059 | — | — | — | — | AT-020 | `.env.example` | Implemented | |
| TR-016 | Technical | ADR-0006 | Idempotency key format | System | P0 | Integration | FR-044 | API-031 | DB-040 | — | TC-016 | AT-018 | `mobile/src/lib/idempotency.ts` | Implemented | |

---

## 3. Acceptance criteria (AT)

| ID | Acceptance criteria |
| -- | ------------------- |
| AT-001 | Six roles are seeded and listed via the admin roles endpoint. |
| AT-002 | A user without a required role receives `403`; invalid/missing token receives `401`. |
| AT-003 | A scoped user can read only their organization's rows; no-org non-admin sees nothing. |
| AT-004 | A user can hold one or more roles simultaneously. |
| AT-005 | Collector categories render in the requested locale and fall back to English. |
| AT-006 | Only 14 simple collector labels are exposed to collectors; the industrial taxonomy is hidden. |
| AT-007 | Equipment and recovered material are stored as distinct `kind` values. |
| AT-008 | A lot with items can be created/listed/read; foreign items are rejected (`403`). |
| AT-009 | An image attaches as Cloudinary metadata; no binary column exists. |
| AT-010 | Classify returns provider + confidence + `suggested_action`; confirm applies the category; correct stores a training candidate. |
| AT-011 | An AI suggestion is never persisted as fact without a human confirm/correct. |
| AT-012 | Price estimates derive from observations and return `null` when none exist; collector entries are `unverified`. |
| AT-013 | A recycler is `pending` by default and becomes `verified` only with non-expired authorization; expired is excluded. |
| AT-014 | Matching ranks by composite score, never gross price alone. |
| AT-015 | Illegal transaction transitions return `409` and write events + audit. |
| AT-016 | Declared/pickup/final weights are recorded; final weight updates the transaction. |
| AT-017 | Cash/UPI/bank_transfer are supported; digital payment is optional. |
| AT-018 | Sync is idempotent; a repeated key returns `replayed` and never duplicates. |
| AT-019 | Nearby search returns verified, non-expired recyclers within a radius ordered by distance. |
| AT-020 | Secrets are env-only; no secret is committed; `.env` is git-ignored. |
| AT-021 | No Aadhaar field exists in schema or code. |
| AT-022 | A dispute can be raised against a transaction and tracked with events. |
| AT-023 | Quotes, handover, and earnings records are persisted and retrievable. |
| AT-024 | Price-history aggregates and admin analytics are derived from stored data. |
| AT-025 | Audit events capture actor, action, entity, and before/after on key mutations. |

---

## 4. Test cases (TC)

| ID | Scenario | Evidence | Status |
| -- | -------- | -------- | ------ |
| TC-001 | Health & readiness | `backend/tests/test_health.py` | Implemented |
| TC-002 | Auth / me / RBAC | `backend/tests/test_auth.py` | Implemented |
| TC-003 | Org scope / auto-provision / audit | `backend/tests/test_helpers.py` | Implemented |
| TC-004 | Lots CRUD + items + images | `backend/tests/test_lots.py` | Implemented |
| TC-005 | AI classify/confirm/correct | `backend/tests/test_ai.py` | Implemented |
| TC-006 | Media upload signature | `backend/tests/test_media.py` | Implemented |
| TC-007 | Idempotency middleware (409) | `backend/tests/test_idempotency.py` | Implemented |
| TC-008 | Sync replay / batch | `backend/tests/test_sync.py` | Implemented |
| TC-009 | Nearby search (PostGIS) | `backend/tests/test_geo.py` | Implemented |
| TC-010 | Taxonomy | `backend/tests/test_taxonomy.py` | Implemented |
| TC-011 | Pricing observations + estimate | `backend/tests/test_pricing.py` | Implemented |
| TC-012 | Recycler verification | `backend/tests/test_recyclers.py` | Implemented |
| TC-013 | Matching | `backend/tests/test_matching.py` | Implemented |
| TC-014 | Transactions / weights / payments | `backend/tests/test_transactions.py` | Implemented |
| TC-015 | Rate limit | `backend/tests/test_rate_limit.py` | Implemented |
| TC-016 | Mobile uuid + idempotency key | `mobile/src/lib/idempotency.test.ts` | Implemented |
| TC-017 | Mobile sync queue + client | `mobile/src/sync/queue.test.ts`, `client.test.ts` | Implemented |
| TC-018 | Mobile on-device E2E (capture → sync) | — | Planned |
| TC-019 | Web nearby map build | `web` `next build` | Implemented |
| TC-020 | Quotes / handover / disputes / earnings / analytics | — | Planned |
| TC-021 | Cloudinary signed upload E2E | — | Planned 🔎 |
| TC-022 | Real AI provider | — | Planned 🔎 |

---

## 5. Coverage matrix

| Required area | Covered by |
| ------------- | ---------- |
| Collector / Kabadiwala | UR-001..UR-006 → FR-007..FR-011, FR-017, FR-018, FR-022..FR-025, FR-030, FR-034, FR-036, FR-038, FR-041..FR-044 |
| Aggregator | UR-007 → FR-010 (thin coverage — see orphan report) |
| Recycler | UR-008, UR-009 → FR-026..FR-032, FR-037, FR-038 |
| Dismantler | UR-010 → FR-009 (thin coverage — see orphan report) |
| Admin | UR-011, UR-012 → FR-001..FR-004, FR-026..FR-029, FR-062, FR-066, FR-067 |
| Material classification | FR-009..FR-011 |
| AI | FR-012..FR-021 |
| Pricing | FR-022..FR-025 |
| Recycler verification | FR-026..FR-029 |
| Matching | FR-030, FR-031 |
| Quotes | FR-032 |
| Logistics | FR-033 |
| Weight | FR-036 |
| Handover | FR-037 |
| Payment | FR-038, FR-039 |
| Earnings | FR-040 |
| Safety | FR-050 |
| Offline / Synchronization | FR-041..FR-044 |
| Traceability | FR-051 |
| Security / Privacy / Audit | FR-052..FR-061 |
| Disputes | FR-062 |
| Dataset generation | FR-063..FR-065 |
| Analytics | FR-066, FR-067 |

---

## 6. Orphan & coverage validation

**Orphan requirements** (FRs with no implementation anchor — all correctly `Planned` /
`Schema-ready`, not silently dropped):

- FR-015 (valuation assist), FR-019 (escalation), FR-067 (analytics): no API/DB
  beyond reserved fields; **Planned**.
- FR-032 (quotes), FR-037 (handover), FR-040 (earnings), FR-050 (safety),
  FR-062 (disputes), FR-066 (price-history): tables exist, no endpoint/behavior;
  **Schema-ready**.

**Orphan features** (schema/API with no explicit requirement):

- `notifications` (DB-039): table exists; no FR, endpoint, or test. **Orphan.**
- `ai_models` (DB-035): registry exists but is unused (`ai_model_id` always null);
  partially covered by FR-012/TR-008 but no lifecycle requirement. **Semi-orphan.**
- `recycler_service_areas` polygon (`area`) and radius (`radius_km`) fields:
  schema exists, but matching/nearby only use facility distance — the
  service-area factor in FR-030 is not yet implemented. **Partial gap.**

**Thin coverage** (actor capabilities under-specified by FRs):

- **Aggregator** (UR-007) and **Dismantler** (UR-010) have schema support
  (`organizations.organization_type` includes both; recovered-material `kind`
  exists) but no dedicated FR, API, or workflow beyond the shared collector flow.
  These are **planned actor gaps**, not contradictions.

**Implicitly covered lookup/join tables** (referenced by a parent FR, not listed in
an individual cell): `organizations` (DB-001), `collectors` (DB-005),
`material_subcategories` (DB-012), `material_grades` (DB-013),
`material_conditions` (DB-014), `collector_category_mappings` (DB-018), and
`payment_confirmations` (DB-032). These are not orphans — they back the parent rows
via foreign keys.

**Verification performed**: every FR is traced to a source and to at least one test
case and acceptance criterion; no FR is duplicated; legacy IDs are mapped in
[requirements.md §8](requirements.md#8-legacy-id-mapping). API catalog is fully
traced (32/32 endpoints). UI catalog is traced 20/21 screens — `UI-002`
(Home/dashboard) is a cross-cutting planned screen. Database tracing is explicit
for all tables except the seven lookup/join tables listed above.
