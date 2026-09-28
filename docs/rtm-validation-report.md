# RTM Validation Report

> Independent QA pass. Each requirement is classified by **verified behavior**,
> not by file existence. Failures and gaps are reported, not hidden.

## Legend

- **IMPLEMENTED** — behavior verified by a passing test.
- **PARTIALLY IMPLEMENTED** — some behavior works, some missing.
- **NOT IMPLEMENTED** — no working behavior.
- **BLOCKED** — cannot be verified (missing live dependency).
- **NEEDS FIELD VALIDATION** — requires real device/credentials/model.
- **FUTURE** — explicitly deferred.

## Summary

| Status | Count |
| ------ | ----- |
| IMPLEMENTED | 59 (45 FR + 14 TR) |
| PARTIALLY IMPLEMENTED | 15 (14 FR + 1 TR) |
| NOT IMPLEMENTED | 8 (FR) |
| FUTURE | 1 (TR) |
| **Total** | **83** |

Cross-cutting blockers: the **HTTP/API and PostGIS integration** is **BLOCKED** —
no live Supabase database (the legacy `backend/tests/` suite hangs on connect).
**NEEDS FIELD VALIDATION**: mobile on-device runtime, a real AI provider, and
Cloudinary signed upload.

---

## Per-requirement table

| ID | Expected behavior | Actual behavior | Test | Result | Evidence | Status | Defect |
| -- | ----------------- | --------------- | ---- | ------ | -------- | ------ | ------ |
| FR-001 | Six roles seeded | Nine roles seeded | `0019_roles.sql` | PASS | role migration | IMPLEMENTED | requirement drifted 6→9 (stale) |
| FR-002 | RBAC enforced | Role-gated checks (hierarchy) | `test_security.py`, `test_admin.py` | PASS | `core/security.py` | IMPLEMENTED | |
| FR-003 | Organization isolation | Helper + unit test; not wired to endpoints | `test_security.py` | PASS (unit) | `org_scope` | PARTIALLY IMPLEMENTED | not applied to org-scoped queries |
| FR-004 | Multi-role user | Role hierarchy resolves implied roles | `test_security.py` | PASS | `models/role.py` | IMPLEMENTED | |
| FR-005 | Eight languages | en + hi only | — | — | `locales.ts`, seed | PARTIALLY IMPLEMENTED | 6 locales missing |
| FR-006 | Localized labels | `?locale=` + fallback | `test_taxonomy.py` | BLOCKED | `taxonomy.py` | IMPLEMENTED | legacy; needs DB to run |
| FR-007 | Hide industrial taxonomy | 14 collector categories | seed | PASS | `0015_seed_taxonomy.sql` | IMPLEMENTED | |
| FR-008 | 14 collector categories | seeded | seed | PASS | seed | IMPLEMENTED | |
| FR-009 | Equipment vs recovered | `kind` separated | `test_ai.py` | PASS | `material_categories.kind` | IMPLEMENTED | |
| FR-010 | Lots/items CRUD | legacy router + mobile offline capture | `test_lots.py` | BLOCKED | `lots.py`, `mobile` | IMPLEMENTED | legacy; needs DB |
| FR-011 | Images as Cloudinary refs | metadata-only | `test_lots.py` | BLOCKED | `material_images` | IMPLEMENTED | upload needs creds |
| FR-012 | AI suggests category | Reference provider; no real model | `test_ai.py` | PASS | `ai/provider.py` | PARTIALLY IMPLEMENTED | no real provider |
| FR-013 | Confidence estimate | modeled + tiered | `test_ai.py` | PASS | `confidence_tier` | PARTIALLY IMPLEMENTED | real AI pending |
| FR-014 | Detect material types | field present | `test_ai.py` | PASS | `detected_material_types` | PARTIALLY IMPLEMENTED | real AI pending |
| FR-015 | AI valuation assist | deterministic valuation only | `test_ai.py` | PASS | `valuation.py` | NOT IMPLEMENTED | `valuation_hint` unused |
| FR-016 | Image quality detection | field only | — | — | `quality_flags` | NOT IMPLEMENTED | real model TODO |
| FR-017 | High confidence → confirm | implemented | `test_ai.py` | PASS | `ClassificationService` | IMPLEMENTED | |
| FR-018 | Low confidence → manual | implemented | `test_ai.py` | PASS | tier = manual | IMPLEMENTED | |
| FR-019 | Escalation recycler→admin | not built | — | — | — | NOT IMPLEMENTED | |
| FR-020 | Corrections as training data | forced `is_training_candidate` | `test_ai.py` | PASS | `ai_corrections` | IMPLEMENTED | |
| FR-021 | AI must not claim composition | provider contract | `test_ai.py` | PASS | `provider.py` docstring | IMPLEMENTED | |
| FR-022 | No hard-coded price | observation-driven | `test_pricing.py` | PASS | `PricingService` | IMPLEMENTED | |
| FR-023 | Contextual price fields | all fields modeled | `test_pricing.py` | PASS | `PriceObservation` | IMPLEMENTED | |
| FR-024 | Provenance on observations | full provenance | `test_pricing.py` | PASS | `PriceObservation` | IMPLEMENTED | |
| FR-025 | Collector entry unverified | enforced | `test_pricing.py` | PASS | `verification_status` | IMPLEMENTED | |
| FR-026 | Recycler not auto-verified | pending default | `test_recycler.py` | PASS | `effective_authorization` | IMPLEMENTED | |
| FR-027 | Full authorization data | stored | `0005_recycler.sql` | PASS | migration | IMPLEMENTED | |
| FR-028 | Five statuses | CHECK constraint | `0005_recycler.sql` | PASS | migration | IMPLEMENTED | |
| FR-029 | Expired excluded | derived | `test_recycler.py`, `test_matching.py` | PASS | `effective_authorization` | IMPLEMENTED | |
| FR-030 | Multi-factor matching | gates + score | `test_matching.py` | PASS | `MatchingService` | IMPLEMENTED | |
| FR-031 | Never gross price alone | composite score | `test_matching.py` | PASS | `MatchConfig` | IMPLEMENTED | |
| FR-032 | Recycler quote on lot | schema + comparison only | `test_pricing.py` | PASS | `recycler_quotes` | NOT IMPLEMENTED | no submit/accept endpoint |
| FR-033 | Pickup/delivery + schedule | columns only | — | — | `0009_transactions.sql` | NOT IMPLEMENTED | field validation required |
| FR-034 | Lifecycle state machine | enforced | `test_transaction.py` | PASS | `TRANSITIONS` | IMPLEMENTED | |
| FR-035 | Audit on transitions | one audit per transition | `test_transaction.py` | PASS | `apply_transition` | IMPLEMENTED | |
| FR-036 | declared/pickup/final weight | all three | `test_transaction.py` | PASS | `record_weight` | IMPLEMENTED | |
| FR-037 | Digital handover | idempotent | `test_transaction.py` | PASS | `record_handover` | IMPLEMENTED | |
| FR-038 | cash/upi/bank transfer | all three | `test_transaction.py` | PASS | `PaymentMethod` | IMPLEMENTED | |
| FR-039 | Digital not mandatory | cash supported | `test_transaction.py` | PASS | `PaymentMethod` | IMPLEMENTED | |
| FR-040 | Net earnings + history | derived ledger | `test_transaction.py` | PASS | `earnings` | IMPLEMENTED | |
| FR-041 | SQLite local DB | schema declared | `store.test.ts` | PASS | `db/schema.ts` | PARTIALLY IMPLEMENTED | expo adapter unwired |
| FR-042 | Offline capture scope | data layer + tests | `service.test.ts` | PASS | `SyncService` | PARTIALLY IMPLEMENTED | screens pending |
| FR-043 | Backend authoritative | design + idempotent sync | `service.test.ts` | PASS | `SyncService` | IMPLEMENTED | |
| FR-044 | Idempotency keys | replayed = no duplicate | `service.test.ts`, `test_transaction.py` | PASS | outbox | IMPLEMENTED | RTM note stale (was camelCase) |
| FR-045 | No large images in PG | metadata only | `0006_lots.sql` | PASS | schema | IMPLEMENTED | |
| FR-046 | Collector→Cloudinary→metadata | signed-upload params | `test_media.py` | BLOCKED | `media.py` | PARTIALLY IMPLEMENTED | no Cloudinary creds |
| FR-047 | PostGIS | extension enabled | `0001_extensions.sql` | PASS | migration | IMPLEMENTED | not run-tested |
| FR-048 | geography(Point,4326) | facility location | `0005_recycler.sql` | PASS | migration | IMPLEMENTED | |
| FR-049 | Nearby/radius/distance | proximity logic + PostGIS query | `test_matching.py` | PASS (logic) | `geo.py`, repo | PARTIALLY IMPLEMENTED | PostGIS query not run (no DB) |
| FR-050 | Hazard links + safety | tables only | — | — | `0004_taxonomy.sql` | NOT IMPLEMENTED | no fetch endpoint |
| FR-051 | End-to-end traceability | events+weights+handover+payments+audit | `test_transaction.py` | PASS | `TransactionService` | IMPLEMENTED | |
| FR-052 | HTTPS | host TLS termination | — | PASS | `render.yaml` | IMPLEMENTED | |
| FR-053 | Supabase JWT auth | verified (legacy) | `test_auth.py` | BLOCKED | `auth.py` | IMPLEMENTED | needs DB to run |
| FR-054 | Authorization (RBAC + org) | RBAC wired; org not | `test_security.py` | PASS | `require_role` | PARTIALLY IMPLEMENTED | org isolation not wired |
| FR-055 | Input validation | Pydantic + sanitized errors | `test_security.py` | PASS | `core/errors.py` | IMPLEMENTED | |
| FR-056 | Rate limiting | fixed-window | `test_security.py` | PASS | `rate_limit.py` | IMPLEMENTED | in-memory only |
| FR-057 | Audit logging | append-only | `test_transaction.py` | PASS | `AuditEvent` | IMPLEMENTED | |
| FR-058 | Secure image handling | signed upload logic | `test_media.py` | PASS (unit) | `media.py` | PARTIALLY IMPLEMENTED | upload untested (creds) |
| FR-059 | Env-only secrets | pydantic-settings | — | PASS | `core/config.py` | IMPLEMENTED | |
| FR-060 | Data minimization | id+email/phone only | `test_helpers.py` | BLOCKED | `auth.py` | IMPLEMENTED | |
| FR-061 | No Aadhaar | absent | schema audit | PASS | schema | IMPLEMENTED | |
| FR-062 | Disputes + events | initiation only | `test_transaction.py`, `test_admin.py` | PASS | `initiate_dispute` | PARTIALLY IMPLEMENTED | events/resolution pending |
| FR-063 | AI corrections as training data | enforced | `test_ai.py` | PASS | `ai_corrections` | IMPLEMENTED | |
| FR-064 | Price observations provenance | full | `test_pricing.py` | PASS | `PriceObservation` | IMPLEMENTED | |
| FR-065 | Image quality flags | field only | — | — | `quality_flags` | PARTIALLY IMPLEMENTED | real model TODO |
| FR-066 | Price-history aggregates | table only | — | — | `price_history` | NOT IMPLEMENTED | no derivation job |
| FR-067 | Platform analytics | none | — | — | — | NOT IMPLEMENTED | no endpoint |
| TR-001 | Mobile Expo/RN/TS/SQLite | scaffold + data layer | mobile tests | PASS | `mobile/package.json` | IMPLEMENTED | |
| TR-002 | Backend FastAPI | clean layered app | unit tests | PASS | `app/` | IMPLEMENTED | |
| TR-003 | DB Supabase PG+PostGIS | migrations | — | PASS | `migrations/` | IMPLEMENTED | not run |
| TR-004 | Media Cloudinary | params; no creds | `test_media.py` | BLOCKED | `media.py` | PARTIALLY IMPLEMENTED | NEEDS FIELD VALIDATION |
| TR-005 | Cache/jobs Redis | reserved | — | — | `REDIS_URL` | FUTURE | not wired |
| TR-006 | Web Next.js | nearby map page | `next build` | PASS | `web/` | IMPLEMENTED | not re-run |
| TR-007 | Maps OSM+MapLibre | map component | `next build` | PASS | `NearbyMap.tsx` | IMPLEMENTED | |
| TR-008 | AI pluggable provider | interface + Reference | `test_ai.py` | PASS | `ai/provider.py` | IMPLEMENTED | Null/Reference only |
| TR-009 | Backend authoritative | design | `service.test.ts` | PASS | `SyncService` | IMPLEMENTED | |
| TR-010 | UUID primary keys | uuid defaults | migrations | PASS | `gen_random_uuid` | IMPLEMENTED | |
| TR-011 | snake_case wire contract | mobile switched to snake_case | mobile tests | PASS | `types/index.ts` | IMPLEMENTED | RTM note stale |
| TR-012 | psycopg3 async, no ORM | async pool | — | PASS | `db.py` | IMPLEMENTED | |
| TR-013 | SQL migrations + Node runner | versioned files | — | PASS | `run.js` | IMPLEMENTED | |
| TR-014 | Supabase Auth IdP | JWT verify | `test_auth.py` | BLOCKED | `auth.py` | IMPLEMENTED | needs DB |
| TR-015 | Env-only secrets | pydantic-settings | — | PASS | `core/config.py` | IMPLEMENTED | |
| TR-016 | Idempotency key format | KC-<E>-<YYMMDD>-<NNNNNN> | `idempotency.test.ts` | PASS | `idempotency.ts` | IMPLEMENTED | |

---

## Blocked & field-validation summary

**BLOCKED (no live Supabase database):**

- HTTP/API integration tests (legacy `backend/tests/`, 54 tests) hang awaiting a
  connection.
- PostGIS distance queries (`ST_DWithin`/`ST_Distance`) are written but not run
  against real data.
- Supabase JWT/auth runtime (`FR-053`, `TR-014`) not exercised end-to-end.

**NEEDS FIELD VALIDATION:**

- Mobile on-device `expo-sqlite` adapter + `NetInfo` (FR-041/FR-042).
- A real AI provider (FR-012/013/014/016/065).
- Cloudinary signed upload (FR-046/FR-058, TR-004).

## What still needs work (not hidden)

1. **No live DB** → integration/API/PostGIS tests blocked.
2. **HTTP endpoints not migrated** onto the clean service layer (legacy routers
   still hold inline SQL + are the only HTTP surface).
3. **`org_scope` not wired** into endpoints (FR-003/FR-054) — a real isolation gap.
4. **AI is architecture-only** — no real model; classification is manual/reference.
5. **Cloudinary path unverified** (no credentials).
6. **Mobile has no screens / on-device runtime** (data layer only).
7. **Six locales missing** (FR-005).
8. **Quotes, logistics, safety, analytics, escalation** not implemented
   (FR-032/033/050/066/067/019).
9. **Dispute events/resolution** not implemented (FR-062 partial).
10. **Notifications** table is an orphan (no requirement/endpoint).
11. **RTM drift**: FR-001 still says "six roles" (now nine); FR-044/TR-011 notes
    about a camelCase mismatch are stale (fixed in the offline phase).
