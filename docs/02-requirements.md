# Kabadi Mitra — Requirements Specification

> Phase 2 deliverable. Complete, traceable requirements for Kabadi Mitra, derived
> from the approved architecture and the problem statement. Every requirement is
> traceable through the hierarchy in the
> [Requirement Traceability Matrix](requirement-traceability-matrix.md).

---

## 1. How to read this document

Requirements are organized in a strict traceability chain:

```
Problem Statement
  -> Business Requirement (BR)
    -> User Requirement (UR)
      -> Functional Requirement (FR)
        -> Technical Requirement (TR)
          -> API -> Database -> UI -> Test Case -> Acceptance Criteria
            -> Evidence -> Status
```

- **BR** = why the product exists (business goal).
- **UR** = what a specific actor needs (capability).
- **FR** = what the system does (behavior), the traceable core.
- **TR** = how it is built (technology/architecture constraint).
- **API / DB / UI / TC / AT** = reference catalogs the FRs point into.

### 1.1 ID scheme

| Prefix | Meaning |
| ------ | ------- |
| `BR-` | Business Requirement |
| `UR-` | User Requirement |
| `FR-` | Functional Requirement |
| `TR-` | Technical Requirement |
| `API-` | API endpoint |
| `DB-` | Database entity (table) |
| `UI-` | UI screen |
| `TC-` | Test case |
| `AT-` | Acceptance criteria |

> **ID scheme change.** This document renumbers the previous namespaced IDs
> (`FR-USER-01`, `FR-AI-01`, …) to flat sequential IDs (`FR-001`, `FR-002`, …).
> The [legacy mapping](#8-legacy-id-mapping) preserves traceability to earlier
> documents that still cite the old IDs. Nothing is deleted.

### 1.2 Priority

| Priority | Meaning |
| -------- | ------- |
| **P0** | Core system cannot function without it |
| **P1** | Important MVP capability |
| **P2** | Enhancement |
| **P3** | Future |

### 1.3 Status

| Status | Meaning |
| ------ | ------- |
| **Planned** | Captured, not started (no schema/code) |
| **Schema-ready** | Data model exists and is verified; behavior/API not built |
| **In progress** | Partial implementation; remaining work deferred |
| **Implemented** | Code exists and has been validated (not asserted without inspection) |

### 1.4 Markers

- **FIELD VALIDATION REQUIRED** — needs field-level rules/validation.
- **ASSUMPTION** — an assumption was made and must be confirmed.
- **NEEDS VALIDATION** — cannot yet be verified (external dependency).

---

## 2. Problem statement

Informal e-waste collectors (pickers and *kabadiwalas*) and authorized recyclers
operate with no shared, trustworthy record of a transaction. A collector's
physical pickup is informal, opaque, and price-asymmetric: material is captured
without a traceable record, prices are negotiated without transparent context,
and recycler legitimacy is not verifiable by the collector.

Kabadi Mitra turns a collector's physical pickup into a **traceable,
price-transparent, and verifiable transaction** — from material capture through
payment and earnings history. It is a **collector-first** digital bridge that
lowers the barrier between informal collectors and authorized recyclers while
keeping the **backend authoritative** and **AI assistive** (never a substitute
for human confirmation on uncertain classifications).

---

## 3. Business requirements (BR)

| ID | Requirement |
| -- | ----------- |
| BR-001 | Provide a digital bridge between informal collectors and authorized recyclers. |
| BR-002 | Make every transaction traceable, price-transparent, and verifiable end-to-end. |
| BR-003 | Keep the backend authoritative and AI strictly assistive (never authoritative). |
| BR-004 | Serve the six e-waste value-chain roles: Picker, Kabadiwala, Aggregator, Recycler, Dismantler, Platform Admin. |
| BR-005 | Deliver a collector-first experience in eight languages (Hindi, English, Marathi, Tamil, Telugu, Malayalam, Kannada, Bengali). |
| BR-006 | Operate offline-first so collectors in low-connectivity areas can work and sync later. |
| BR-007 | Enforce security, privacy, and audit by default; do not collect Aadhaar in the MVP. |
| BR-008 | Capture feedback data (classifications, corrections, prices, image-quality flags) to enable dataset generation and analytics. |

---

## 4. User requirements (UR)

Each user requirement states the actor, the need, and the value.

| ID | Actor | User requirement |
| -- | ----- | ---------------- |
| UR-001 | Picker / Waste Collector | Capture material with a photo and a simple category so I can record a pickup without knowing the industrial taxonomy. |
| UR-002 | Picker / Waste Collector | Record weights (declared / pickup / final) so the transaction reflects the actual material. |
| UR-003 | Picker / Waste Collector | See a contextual price estimate and matched verified recyclers so I can choose where to sell. |
| UR-004 | Picker / Waste Collector | Track transactions, payments, and earnings history so I know what I have earned. |
| UR-005 | Kabadiwala | Operate as a collection point that consolidates material from pickers so I can sell in bulk. |
| UR-006 | Kabadiwala | Use the same capture, classify, and offline-sync flow as a picker so my operation works offline. |
| UR-007 | Aggregator | Consolidate material from multiple collectors so I can route it to recyclers/dismantlers. |
| UR-008 | Recycler | Be onboarded with verified authorization and declare accepted materials so collectors can find and trust me. |
| UR-009 | Recycler | Quote on lots, receive/deliver material, and record payment so transactions are transparent. |
| UR-010 | Dismantler | Record equipment broken down into recovered material so recovered material is tracked separately. |
| UR-011 | Platform Admin | Verify recyclers and manage roles so only authorized parties operate on the platform. |
| UR-012 | Platform Admin | Review disputes and view analytics so I can govern and improve the platform. |

---

## 5. Functional requirements (FR)

Functional requirements are grouped by module. Each entry lists the requirement,
the primary actor, priority, and dependency on other FRs. The full
traceability (API / database / UI / test / acceptance / evidence / status) is in
the [RTM](requirement-traceability-matrix.md).

### 5.1 Identity & access (RBAC)

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-001 | Support a nine-role model: collector, kabadiwala, aggregator, recycler, dismantler, support, operations_admin, data_ai_admin, super_admin. | Admin | P0 | — |

> **Role-model drift (verified)**: the requirements originally specified six roles
> (`picker`, `kabadiwala`, `aggregator`, `recycler`, `dismantler`,
> `platform_admin`). Migration `0019_roles.sql` renames `picker → collector` and
> `platform_admin → super_admin`, and adds `support`, `operations_admin`,
> `data_ai_admin` — giving **nine** roles. The layered `app/models/role.py`
> implements all nine with a hierarchy. The **mounted** HTTP routers still use the
> legacy six codes. This is a partial/in-transition state, tracked in the RTM as
> FR-001 **PARTIAL**.
| FR-002 | Enforce role-based access control so a user can act only within granted roles. | All | P0 | FR-001 |
| FR-003 | Enforce organization-level data isolation so a scoped user sees only their organization's data. | All | P0 | FR-001 |
| FR-004 | Allow a user to hold one or more roles via a user-role mapping. | Admin | P0 | FR-001 |

### 5.2 Localization & collector UX

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-005 | Support eight languages for collector-facing content. | Collector | P0 | — |
| FR-006 | Localize collector-facing labels independently of the backend industrial taxonomy. | Collector | P0 | FR-005 |
| FR-007 | Do not expose the complex industrial taxonomy to collectors. | Collector | P0 | — |
| FR-008 | Provide exactly the 14 approved collector categories (TV/Monitor, Computer/Laptop, Mobile/Electronics, PCB/Board, Cable/Wire, Battery, Motor, Magnet, Plastic, Metal, Lamp, Printer, Other, "I don't know"). | Collector | P0 | FR-007 |
| FR-009 | Represent equipment and recovered material as separate kinds. | Collector | P0 | — |

### 5.3 Material capture

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-010 | Create and manage a digital lot and its items (title, notes, pickup location/address). | Collector | P0 | FR-008, FR-009 |
| FR-011 | Attach images to lot items as Cloudinary references (never binary in PostgreSQL). | Collector | P0 | FR-010 |

### 5.4 AI & classification

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-012 | AI suggests a material category and subcategory. | Collector | P1 | FR-011 |
| FR-013 | AI estimates a classification confidence. | Collector | P1 | FR-012 |
| FR-014 | AI detects supported visual material types. | Collector | P1 | FR-012 |
| FR-015 | AI assists valuation. | Collector | P2 | FR-013 |
| FR-016 | AI detects image-quality issues. | Collector | P2 | FR-011 |
| FR-017 | High confidence (>= threshold): AI suggestion is offered for collector confirmation. | Collector | P1 | FR-013 |
| FR-018 | Low confidence: collector manually selects a category or "I don't know". | Collector | P0 | FR-008 |
| FR-019 | Escalation path when necessary: recycler review, then admin review. | Recycler/Admin | P2 | FR-018 |
| FR-020 | Store collector corrections as feedback/training candidates, never auto-ground-truth. | Collector | P1 | FR-012 |
| FR-021 | AI must NOT claim exact metal content, chemical composition, certified hazardousness, or lab-grade grade from an ordinary photo. | System | P0 | FR-012 |

### 5.5 Pricing

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-022 | Provide no single hard-coded price per material. | Collector | P0 | — |
| FR-023 | Model price contextually: material, grade, location, date/time, buyer, weight, transport, source, verification. | Collector | P0 | FR-022 |
| FR-024 | Attach provenance to every price observation. | Collector | P0 | FR-023 |
| FR-025 | Treat collector-entered buyer prices as observations (unverified), not authoritative market prices. | Collector | P0 | FR-024 |

### 5.6 Recycler verification

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-026 | A recycler is never auto-verified; it starts `pending`. | Admin | P0 | — |
| FR-027 | Store full authorization data: organization, facility, authorization number, issuing authority, type, issue/expiry dates, verification source/date, accepted materials, service area, status. | Admin | P0 | FR-026 |
| FR-028 | Enforce five verification statuses: verified, pending, expiring, expired, suspended. | Admin | P0 | FR-027 |
| FR-029 | Exclude a recycler with expired authorization from matching. | System | P0 | FR-028 |

### 5.7 Matching

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-030 | Match a lot to recyclers on authorization, material acceptance, service area, distance, and pickup/transport factors. | Collector | P0 | FR-026, FR-023 |
| FR-031 | Never rank recyclers by gross price alone. | System | P0 | FR-030 |

### 5.8 Quotes

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-032 | A recycler submits a quote on a lot with price, grade, terms, status, and validity. | Recycler | P1 | FR-030 |

### 5.9 Logistics

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-033 | Track pickup or delivery method and a scheduled time for a transaction. | Collector | P1 | FR-034 |

### 5.10 Transactions

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-034 | Enforce the transaction lifecycle state machine (LOT_CREATED → CLASSIFIED → QUOTED → QUOTE_ACCEPTED → PICKUP_OR_DELIVERY → WEIGHT_VERIFIED → HANDOVER_CONFIRMED → PAYMENT_RECORDED → COMPLETED). | Collector | P0 | FR-030 |
| FR-035 | Record audit events on important state transitions. | System | P0 | FR-034 |

### 5.11 Weight

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-036 | Support declared, pickup, and final (recycler-accepted) weight. | Collector | P0 | FR-034 |

### 5.12 Handover

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-037 | Record a digital handover between collector and recycler. | Collector/Recycler | P1 | FR-034 |

### 5.13 Payments

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-038 | Support Cash, UPI, and Bank transfer payment methods. | Collector | P0 | FR-034 |
| FR-039 | Digital payment is not mandatory. | Collector | P0 | FR-038 |

### 5.14 Earnings

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-040 | Record net earnings per transaction and expose an earnings history. | Collector | P1 | FR-034, FR-038 |

### 5.15 Offline & synchronization

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-041 | Use SQLite as the local working database on the mobile client. | Collector | P0 | — |
| FR-042 | Support offline capture: material capture, lot creation, weight entry, cached price info, safety content, draft transactions, and payment recording. | Collector | P0 | FR-041 |
| FR-043 | Keep the backend authoritative over business logic and data. | System | P0 | — |
| FR-044 | Use idempotency keys so repeated sync requests never create duplicates. | System | P0 | FR-043 |

### 5.16 Media

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-045 | Do not store large images in PostgreSQL. | System | P0 | — |
| FR-046 | Enforce the flow: collector → Cloudinary → public ID / secure URL → PostgreSQL metadata. | Collector | P0 | FR-045 |

### 5.17 Geospatial

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-047 | Use PostGIS for spatial storage and queries. | System | P0 | — |
| FR-048 | Store recycler facility location as `geography(Point, 4326)`. | Recycler | P0 | FR-047 |
| FR-049 | Support nearby recycler search, service radius, and distance calculation. | Collector | P0 | FR-048 |

### 5.18 Safety

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-050 | Associate material hazards (e.g., lithium, lead, mercury) with categories and make safety content available offline. | Collector | P1 | FR-042 |

### 5.19 Traceability

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-051 | Provide end-to-end traceability via immutable events, weights, payments, and handover records. | All | P0 | FR-035, FR-036, FR-037, FR-038 |

### 5.20 Security, privacy & audit

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-052 | Enforce HTTPS everywhere. | System | P0 | — |
| FR-053 | Authenticate via Supabase Auth (JWT verified against JWKS). | All | P0 | — |
| FR-054 | Enforce authorization (RBAC + organization isolation + ownership). | All | P0 | FR-002, FR-003 |
| FR-055 | Validate all request input. | System | P0 | — |
| FR-056 | Rate-limit requests where appropriate. | System | P0 | — |
| FR-057 | Record an append-only audit trail for important mutations. | System | P0 | — |
| FR-058 | Handle images securely (signed upload, metadata-only storage). | System | P0 | FR-046 |
| FR-059 | Store secrets only in environment variables; never in code or the repo. | System | P0 | — |
| FR-060 | Minimize data collection (e.g., auto-provisioned users store only id + email/phone). | System | P0 | — |
| FR-061 | Do not collect or store Aadhaar in the MVP. | System | P0 | — |

### 5.21 Disputes

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-062 | Allow a dispute to be raised against a transaction and record dispute events. | Collector/Recycler | P2 | FR-034 |

### 5.22 Dataset generation

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-063 | Collect AI corrections as training candidates for future model training. | System | P1 | FR-020 |
| FR-064 | Collect price observations with full provenance to seed the pricing engine. | System | P1 | FR-024 |
| FR-065 | Collect image-quality flags to tune the AI quality detector. | System | P1 | FR-016 |

### 5.23 Analytics

| ID | Requirement | Actor | Priority | Depends on |
| -- | ----------- | ----- | -------- | ---------- |
| FR-066 | Derive and store price-history aggregates (period averages, min/max, sample count). | Admin | P2 | FR-024 |
| FR-067 | Expose platform analytics for governance (activity, matches, transactions, disputes). | Admin | P2 | FR-051, FR-062 |

---

## 6. Technical requirements (TR)

| ID | Requirement | Depends on |
| -- | ----------- | ---------- |
| TR-001 | Mobile: React Native + Expo + TypeScript + SQLite (Android-first). | — |
| TR-002 | Backend: FastAPI + Python (REST). | — |
| TR-003 | Database: Supabase PostgreSQL + PostGIS. | — |
| TR-004 | Media: Cloudinary (signed direct upload). | — |
| TR-005 | Cache/jobs: Redis. | — |
| TR-006 | Web: Next.js + TypeScript. | — |
| TR-007 | Maps: OpenStreetMap + MapLibre GL. | — |
| TR-008 | AI: pluggable provider interface (`BaseProvider`), default `none`. | — |
| TR-009 | Backend is authoritative; clients are not the source of truth. | — |
| TR-010 | UUID primary keys for all entities so clients can generate IDs offline. | — |
| TR-011 | Canonical API wire contract is snake_case; clients serialize accordingly. | — |
| TR-012 | Data access via psycopg3 async with hand-written SQL (no ORM). | — |
| TR-013 | Migrations: plain SQL applied by the Node/`pg` runner, tracked in `schema_migrations`. | — |
| TR-014 | Identity: Supabase Auth (JWT, RS256, `iss`/`aud` verified against JWKS). | — |
| TR-015 | Secrets via environment variables only. | — |
| TR-016 | Idempotency-key format: `KC-<ENTITY>-<YYMMDD>-<NNNNNN>`. | — |

---

## 7. Reference catalogs

### 7.1 API endpoints

| ID | Method | Path | Auth | Maps to |
| -- | ------ | ---- | ---- | ------- |
| API-001 | GET | `/health` | none | FR-052 |
| API-002 | GET | `/health/ready` | none | FR-052 |
| API-003 | GET | `/api/v1/me` | required | FR-053 |
| API-004 | GET | `/api/v1/taxonomy/collector-categories?locale=` | required | FR-006, FR-008 |
| API-005 | GET | `/api/v1/admin/roles` | platform_admin | FR-001, FR-002 |
| API-006 | POST | `/api/v1/lots` | collector | FR-010 |
| API-007 | GET | `/api/v1/lots` | collector | FR-010 |
| API-008 | GET | `/api/v1/lots/{id}` | collector | FR-010 |
| API-009 | POST | `/api/v1/lots/{id}/items` | collector | FR-010 |
| API-010 | POST | `/api/v1/lots/{id}/items/{item_id}/images` | collector | FR-011 |
| API-011 | POST | `/api/v1/lot-items/{item_id}/classify` | collector | FR-012, FR-013, FR-014 |
| API-012 | POST | `/api/v1/ai-decisions/{id}/confirm` | collector | FR-017 |
| API-013 | POST | `/api/v1/ai-decisions/{id}/correct` | collector | FR-018, FR-020 |
| API-014 | GET | `/api/v1/media/upload-params` | required | FR-046 |
| API-015 | POST | `/api/v1/price-observations` | required | FR-024 |
| API-016 | GET | `/api/v1/pricing/estimate` | required | FR-022, FR-023 |
| API-017 | POST | `/api/v1/recycler/organizations` | platform_admin/recycler | FR-027 |
| API-018 | GET | `/api/v1/recycler/organizations` | platform_admin | FR-027 |
| API-019 | GET | `/api/v1/recycler/organizations/{id}` | platform_admin | FR-027 |
| API-020 | GET | `/api/v1/recycler/verified` | required | FR-028, FR-029 |
| API-021 | POST | `/api/v1/recycler/organizations/{id}/acceptance` | platform_admin | FR-027 |
| API-022 | POST | `/api/v1/lots/{id}/matches` | collector | FR-030, FR-031 |
| API-023 | GET | `/api/v1/lots/{id}/matches` | collector | FR-030 |
| API-024 | POST | `/api/v1/lots/{id}/transactions` | collector | FR-034 |
| API-025 | GET | `/api/v1/transactions/{id}` | collector | FR-034, FR-040 |
| API-026 | GET | `/api/v1/transactions/{id}/events` | collector | FR-051 |
| API-027 | POST | `/api/v1/transactions/{id}/transition` | collector | FR-034, FR-035 |
| API-028 | POST | `/api/v1/transactions/{id}/weights` | collector | FR-036 |
| API-029 | POST | `/api/v1/transactions/{id}/payments` | collector | FR-038 |
| API-030 | POST | `/api/v1/payments/{id}/confirm` | collector | FR-038 |
| API-031 | POST | `/api/v1/sync` | collector | FR-042, FR-044 |
| API-032 | GET | `/api/v1/recycler/nearby` | required | FR-048, FR-049 |

> **Planned (no endpoint yet — schema-ready):** quotes, handover, disputes,
> earnings history, notifications, safety/hazard fetch, and analytics. These map
> to FR-032, FR-037, FR-040, FR-050, FR-062, FR-066, FR-067 and are recorded as
> "schema-ready" in the RTM.

### 7.2 Database entities

| ID | Table | ID | Table |
| -- | ----- | -- | ----- |
| DB-001 | organizations | DB-022 | material_images |
| DB-002 | users | DB-023 | price_observations |
| DB-003 | roles | DB-024 | price_history |
| DB-004 | user_roles | DB-025 | recycler_quotes |
| DB-005 | collectors | DB-026 | matches |
| DB-006 | recycler_organizations | DB-027 | transactions |
| DB-007 | recycler_facilities | DB-028 | transaction_events |
| DB-008 | recycler_authorizations | DB-029 | weights |
| DB-009 | recycler_material_acceptance | DB-030 | handover_records |
| DB-010 | recycler_service_areas | DB-031 | payments |
| DB-011 | material_categories | DB-032 | payment_confirmations |
| DB-012 | material_subcategories | DB-033 | disputes |
| DB-013 | material_grades | DB-034 | dispute_events |
| DB-014 | material_conditions | DB-035 | ai_models |
| DB-015 | material_hazards | DB-036 | ai_decisions |
| DB-016 | material_hazard_links | DB-037 | ai_corrections |
| DB-017 | collector_categories | DB-038 | audit_events |
| DB-018 | collector_category_mappings | DB-039 | notifications |
| DB-019 | translations | DB-040 | sync_operations |
| DB-020 | lots | DB-041 | schema_migrations |
| DB-021 | lot_items | | |

### 7.3 UI screens

| ID | Screen | Client | Status |
| -- | ------ | ------ | ------ |
| UI-001 | Login / auth | Mobile | Planned |
| UI-002 | Home / dashboard | Mobile | Planned |
| UI-003 | Material capture (photo + category) | Mobile | Planned |
| UI-004 | Classification confirm/correct | Mobile | Planned |
| UI-005 | Lot list | Mobile | Planned |
| UI-006 | Lot detail (items) | Mobile | Planned |
| UI-007 | Price estimate | Mobile | Planned |
| UI-008 | Recycler match list | Mobile | Planned |
| UI-009 | Transaction lifecycle | Mobile | Planned |
| UI-010 | Weight entry | Mobile | Planned |
| UI-011 | Payment entry | Mobile | Planned |
| UI-012 | Earnings history | Mobile | Planned |
| UI-013 | Sync status / offline queue | Mobile | Planned |
| UI-014 | Safety content | Mobile | Planned |
| UI-015 | Admin login | Web | Planned |
| UI-016 | Recycler verification | Web | Planned |
| UI-017 | Role / user management | Web | Planned |
| UI-018 | Nearby recycler map | Web | Implemented |
| UI-019 | Analytics dashboard | Web | Planned |
| UI-020 | Dispute review | Web | Planned |
| UI-021 | Recycler onboarding | Web | Planned |

---

## 8. Legacy ID mapping

Prior documents cite namespaced IDs. This mapping preserves traceability.

| Legacy | New | | Legacy | New |
| ------ | --- | - | ------ | --- |
| FR-USER-01 | FR-001 | | FR-VERIF-03 | FR-028 |
| FR-USER-02 | FR-002, FR-003 | | FR-VERIF-04 | FR-029 |
| FR-USER-03 | FR-004 | | FR-MATCH-01 | FR-030 |
| FR-I18N-01 | FR-005 | | FR-MATCH-02 | FR-031 |
| FR-I18N-02 | FR-006 | | FR-TXN-01 | FR-034 |
| FR-UX-01 | FR-007 | | FR-TXN-02 | FR-035 |
| FR-UX-02 | FR-008 | | FR-WEIGHT-01 | FR-036 |
| FR-UX-03 | FR-009 | | FR-PAY-01 | FR-038 |
| FR-AI-01 | FR-012 | | FR-PAY-02 | FR-039 |
| FR-AI-02 | FR-013 | | FR-SYNC-01 | FR-041 |
| FR-AI-03 | FR-014 | | FR-SYNC-02 | FR-042 |
| FR-AI-04 | FR-015 | | FR-SYNC-03 | FR-043 |
| FR-AI-05 | FR-016 | | FR-SYNC-04 | FR-044 |
| FR-AI-06 | FR-017 | | FR-MEDIA-01 | FR-045 |
| FR-AI-07 | FR-018 | | FR-MEDIA-02 | FR-046 |
| FR-AI-08 | FR-019 | | FR-GEO-01 | FR-047 |
| FR-AI-09 | FR-020 | | FR-GEO-02 | FR-048 |
| FR-AI-10 | FR-021 | | FR-GEO-03 | FR-049 |
| FR-PRICE-01 | FR-022 | | FR-SEC-01 | FR-052 |
| FR-PRICE-02 | FR-023 | | FR-SEC-02 | FR-053 |
| FR-PRICE-03 | FR-024 | | FR-SEC-03 | FR-054 |
| FR-PRICE-04 | FR-025 | | FR-SEC-04 | FR-055 |
| FR-VERIF-01 | FR-026 | | FR-SEC-05 | FR-056 |
| FR-VERIF-02 | FR-027 | | FR-SEC-06 | FR-057 |
| FR-SEC-07 | FR-058 | | FR-SEC-08 | FR-059 |
| FR-SEC-09 | FR-060 | | FR-SEC-10 | FR-061 |
| NFR-01 | TR-001 | | NFR-02 | TR-009 |
| NFR-03 | FR-021 | | NFR-05 | (decision-log) |

> `NFR-04` (reuse existing code, work incrementally) is a process principle
> carried forward as guidance, not a single traceable requirement.
