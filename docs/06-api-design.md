# Kabadi Mitra — API Design

> Phase 4 deliverable. Full REST API design for the FastAPI backend, mapped to
> the Phase 2 [Requirement Traceability Matrix](requirement-traceability-matrix.md)
> and the [database design](database-design.md).

---

## 1. Architecture & layering

The backend is authoritative (FR-043, TR-009). Business logic lives in the
**service layer**; database access lives in the **repository layer**; route
handlers are thin and only translate HTTP ↔ service calls. This is the target
structure:

```
backend/
├── app/
│   ├── api/              # thin route handlers + DI (deps) — no business logic
│   │   ├── deps.py
│   │   └── routers/      # health, auth, lots, ai, pricing, recyclers, ...
│   ├── core/             # config, db, security (auth), errors, logging
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── security.py
│   │   └── errors.py
│   ├── models/           # (future) ORM/DB models — currently DB-first, no ORM
│   ├── schemas/          # Pydantic request/response models (per domain)
│   ├── services/         # business logic
│   ├── repositories/     # data access (SQL)
│   ├── workers/          # background jobs (Redis) — reserved
│   ├── ai/               # pluggable AI providers (interface only this phase)
│   └── main.py           # app factory: lifespan, middleware, router registration
└── tests/
```

**Request flow**: `route (api/)` → `service (services/)` → `repository
(repositories/)` → Postgres. Routes never contain SQL; repositories never contain
business rules.

> **Migration note**: the current `app/` uses a flatter layout (domain logic
> co-located in `app/routers/`). This design is the target; the existing 13
> routers are preserved and will be migrated into the layered structure module
> by module in later phases. The foundation (`app/foundation.py`) demonstrates
> the target pattern end-to-end on the health domain.

---

## 2. Conventions

| Concern | Convention |
| ------- | ---------- |
| Base path | `/api/v1/` (health is `/health`, `/health/ready`) |
| Wire format | JSON; snake_case field names (ADR-0029) |
| Dates | ISO-8601 `timestamptz` |
| Errors | consistent envelope (see §3) |
| Idempotency | `Idempotency-Key` header on mutations; batch sync uses per-op keys |
| Versioning | single `/v1`; break on a new major only |
| Secrets | environment variables only (FR-059) |

---

## 3. Error model

Every error returns a consistent JSON envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Lot not found",
    "details": { "lot_id": "..." }
  }
}
```

| HTTP | code | Meaning |
| ---- | ---- | ------- |
| 400 | `bad_request` | malformed input / business rule |
| 401 | `unauthorized` | missing/invalid token |
| 403 | `forbidden` | insufficient role or not the owner |
| 404 | `not_found` | resource missing |
| 409 | `conflict` | state conflict (illegal transition, duplicate idempotency key, already processed) |
| 422 | `validation_error` | request body fails schema validation |
| 429 | `rate_limited` | rate limit exceeded |
| 503 | `service_unavailable` | dependency (DB, Cloudinary) not configured/ready |

A central `core/errors.py` defines `AppError` and subclasses
(`NotFoundError`, `ConflictError`, `ForbiddenError`, …) and registers exception
handlers so routes return a uniform shape (FR-055).

---

## 4. Authentication & authorization

- **Authentication** (FR-053, TR-014): Supabase Auth. Clients send
  `Authorization: Bearer <supabase-jwt>`; the backend verifies RS256 against the
  project JWKS and checks `iss`/`aud`. The JWT `sub` maps to `users.id`, which is
  auto-provisioned on first login (FR-060).
- **Principal** (FR-002, FR-004): the verified token is resolved into a
  `Principal(sub, user_id, roles, organization_id, preferred_locale)`.
- **Authorization** (FR-054): `require_role(*codes)` for RBAC and collector
  ownership checks (`require_collector`) scope every mutation. Organization
  isolation (`org_scope`, FR-003) is the target for all org-scoped reads.

---

## 5. Endpoint catalog

Legend: **Auth** = `none` | `required` | `collector` | role list.
**Idempotency** = `optional` (header) | `required` (batch key) | `—`.

### 5.1 Health & readiness

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/health` | liveness | none | — | — | `HealthOut{status,service}` | — | — | — | — | FR-052 |
| GET | `/health/ready` | readiness (DB ping) | none | — | — | `HealthOut` | — | 503 if DB unavailable | — | — | FR-052 |

### 5.2 Authentication / identity

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/api/v1/me` | current principal | required | — | — | `MeOut{user_id,sub,roles,organization_id,preferred_locale}` | — | 401 | — | users, user_roles, roles | FR-002, FR-004, FR-053 |

### 5.3 Collectors

Collector identity is auto-provisioned (`collectors` row) on first authenticated
collector action via `require_collector` (UR-001..UR-006). No standalone
collector CRUD endpoint is exposed in the MVP; the collector profile is created
and resolved through the lot/sync flows.

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| (internal) | `require_collector` | resolve/create collector profile | required | `picker`/`kabadiwala` | — | collector id | — | 403 | — | collectors | UR-001..006, FR-010 |

### 5.4 Materials (taxonomy)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/api/v1/taxonomy/collector-categories?locale=` | 14 localized collector categories | required | — | `locale` (default `en`) | `CollectorCategoryOut[]{id,code,name,sort_order}` | locale in 8 supported | 401 | — | collector_categories, translations | FR-005..008 |

### 5.5 Lots

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/lots` | create lot | collector | `picker`/`kabadiwala` | `LotCreate{title?,notes?,latitude?,longitude?,pickup_address?}` | `201 LotOut{id,collector_id,status,title,notes,pickup_address,created_at}` | lat/lng in range | 401,403,422 | optional | lots, audit_events | FR-010, FR-044 |
| GET | `/api/v1/lots` | list own lots | collector | `picker`/`kabadiwala` | — | `LotOut[]` | — | 401,403 | — | lots | FR-010 |
| GET | `/api/v1/lots/{lot_id}` | lot detail | collector | owner | — | `LotOut` | UUID | 401,403,404 | — | lots | FR-010 |
| POST | `/api/v1/lots/{lot_id}/items` | add item | collector | owner | `LotItemCreate{collector_category_id?,material_category_id?,material_subcategory_id?,kind?,description?,quantity,declared_weight_kg?,condition_id?,classification_source}` | `201 LotItemOut` | kind ∈ equipment/recovered_material | 401,403,404,422 | optional | lot_items, audit_events | FR-009, FR-010 |

### 5.6 Images

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/lots/{lot_id}/items/{item_id}/images` | attach image (Cloudinary ref) | collector | owner | `MaterialImageCreate{cloudinary_public_id,cloudinary_url,image_kind?,is_primary?,mime_type?,width?,height?}` | `201 MaterialImageOut` | image_kind enum | 401,403,404,422 | optional | material_images | FR-011, FR-045, FR-046 |
| GET | `/api/v1/media/upload-params` | Cloudinary signed-upload params | required | — | — | `{cloud_name,api_key,timestamp,signature}` | — | 401, 503 (unconfigured) | — | — | FR-046 |

### 5.7 AI classification (assistive — no advanced AI this phase)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/lot-items/{item_id}/classify` | run provider, persist suggestion | collector | owner | `ClassifyRequest{image_id?}` | `ClassifyOut{decision_id,provider,confidence,predicted_category_id?,predicted_subcategory_id?,suggested_action,detected_material_types?,quality_flags}` | — | 401,403,404 | optional | ai_decisions, audit_events | FR-012..016, FR-021 |
| POST | `/api/v1/ai-decisions/{decision_id}/confirm` | collector confirms | collector | owner | — | `{status:"confirmed"}` | — | 401,403,404,409 | optional | ai_decisions, lot_items, audit_events | FR-017 |
| POST | `/api/v1/ai-decisions/{decision_id}/correct` | collector corrects | collector | owner | `CorrectRequest{corrected_category_id?,corrected_subcategory_id?,correction_type,note?}` | `{status:"corrected"}` | correction_type enum | 401,403,404,409 | optional | ai_corrections, lot_items, audit_events | FR-018, FR-020, FR-063 |

> Provider contract: `BaseProvider.classify(item, image_id) → ClassificationResult`.
> Default `AI_PROVIDER=none` returns an empty suggestion (manual). Real providers
> are **not** implemented this phase.

### 5.8 Pricing

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/api/v1/pricing/estimate?material_category_id=&grade_id=&city=&days=` | contextual aggregate | required | — | query params | `PricingEstimateOut{material_category_id,currency,summary,observations[]}` | days 1..365 | 401,422 | — | price_observations | FR-022, FR-023 |

### 5.9 Price observations

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/price-observations` | record observation | required | — | `PriceObservationCreate{material_category_id,material_subcategory_id?,grade_id?,latitude?,longitude?,city?,state?,observed_price_per_kg,currency,buyer_type?,buyer_organization_id?,source,weight_kg?,transport_cost?,observed_at?,notes?}` | `201 PriceObservationOut` | source enum, price > 0 | 401,422 | optional | price_observations, audit_events | FR-024, FR-025, FR-064 |

### 5.10 Recycler verification

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/recycler/organizations` | onboard recycler | required | `platform_admin`/`recycler` | `RecyclerOrganizationCreate{name,gstin?,registration_number?,facility_name?,facility_latitude?,facility_longitude?,authorization_number?,issuing_authority?,authorization_type?,issue_date?,expiry_date?,verification_source?,status}` | `201 RecyclerOrganizationOut` | status enum | 401,403,422 | optional | organizations, recycler_organizations, recycler_facilities, recycler_authorizations | FR-026, FR-027 |
| GET | `/api/v1/recycler/organizations` | list all | required | `platform_admin` | — | `RecyclerOrganizationOut[]` | — | 401,403 | — | recycler_organizations, organizations | FR-027 |
| GET | `/api/v1/recycler/organizations/{recycler_id}` | detail + effective status | required | `platform_admin` | — | `RecyclerOrganizationOut` | UUID | 401,403,404 | — | recycler_organizations, recycler_authorizations | FR-027, FR-028 |
| GET | `/api/v1/recycler/verified` | verified, non-expired recyclers | required | — | — | `RecyclerOrganizationOut[]` | — | 401 | — | recycler_organizations, recycler_authorizations | FR-028, FR-029 |
| POST | `/api/v1/recycler/organizations/{recycler_id}/acceptance` | set accepted materials | required | `platform_admin` | `MaterialAcceptanceCreate{material_category_id,is_accepted}` | `{status:"ok"}` | UUID | 401,403,404 | optional | recycler_material_acceptance | FR-027, FR-030 |

### 5.11 Recycler search (geospatial)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/api/v1/recycler/nearby?lat=&lng=&radius_km=&material_category_id=` | nearby verified recyclers | required | — | query params | `NearbyRecyclerOut[]{id,name,distance_km,latitude,longitude}` | radius 1..500 | 401,422 | — | recycler_facilities, recycler_authorizations, recycler_material_acceptance | FR-048, FR-049 |

### 5.12 Matching

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/lots/{lot_id}/matches` | generate ranked matches | collector | owner | — | `MatchOut[]{id,lot_id,recycler_organization_id,recycler_name,score,distance_km,status}` | lot has classified materials | 400,401,403,404 | optional | matches, recycler_organizations, recycler_facilities, recycler_material_acceptance | FR-030, FR-031 |
| GET | `/api/v1/lots/{lot_id}/matches` | list matches | collector | owner | — | `MatchOut[]` | — | 401,403,404 | — | matches | FR-030 |

### 5.13 Quotes (schema-ready — not yet implemented)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/lots/{lot_id}/quotes` | recycler submits quote | required | `recycler` | `{price_per_kg?,total_price?,grade_id?,terms?,valid_until?}` | `201 {id,status:"submitted",...}` | price > 0 | 401,403,404,422 | optional | recycler_quotes | FR-032 |
| GET | `/api/v1/lots/{lot_id}/quotes` | list quotes | collector | owner | — | quote list | — | 401,403,404 | — | recycler_quotes | FR-032 |
| POST | `/api/v1/quotes/{quote_id}/accept` | collector accepts quote | collector | owner | — | `{status:"accepted"}` | — | 401,403,404,409 | optional | recycler_quotes, transactions | FR-032 |

### 5.14 Transactions

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/lots/{lot_id}/transactions` | create transaction | collector | owner | `TransactionCreate{match_id?,recycler_organization_id?}` | `201 TransactionOut` | — | 401,403,404,422 | optional | transactions, transaction_events | FR-034, FR-044 |
| GET | `/api/v1/transactions/{transaction_id}` | detail | collector | owner | — | `TransactionOut{id,lot_id,collector_id,recycler_organization_id,match_id,status,currency,final_weight_kg,net_earnings,created_at}` | UUID | 401,403,404 | — | transactions | FR-034, FR-040 |
| GET | `/api/v1/transactions/{transaction_id}/events` | lifecycle events | collector | owner | — | `TransactionEventOut[]{id,event_type,from_status,to_status,created_at}` | UUID | 401,403,404 | — | transaction_events | FR-035, FR-051 |
| POST | `/api/v1/transactions/{transaction_id}/transition` | advance state | collector | owner | `TransitionRequest{to_status}` | `TransactionOut` | to_status ∈ legal next states | 401,403,404,409 | optional | transactions, transaction_events, audit_events | FR-034, FR-035 |

### 5.15 Weight

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/transactions/{transaction_id}/weights` | record weight | collector | owner | `WeightCreate{weight_type,weight_kg,source}` | `201 WeightOut` | weight_type enum, weight_kg > 0 | 401,403,404,422 | optional | weights, transactions | FR-036 |

### 5.16 Handover (schema-ready — not yet implemented)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/transactions/{transaction_id}/handover` | record handover | required | transaction parties | `{received_by_user_id?,signature_ref?,notes?}` | `201 {id,handed_over_at}` | — | 401,403,404 | optional | handover_records | FR-037, FR-051 |

### 5.17 Payments

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/transactions/{transaction_id}/payments` | record payment | collector | owner | `PaymentCreate{method,amount,reference?}` | `201 PaymentOut` | method enum, amount > 0 | 401,403,404,422 | optional | payments, audit_events | FR-038, FR-044 |
| POST | `/api/v1/payments/{payment_id}/confirm` | confirm payment | collector | owner | — | `{status:"confirmed"}` | UUID | 401,403,404 | optional | payment_confirmations, payments | FR-038 |

### 5.18 Disputes (schema-ready — not yet implemented)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/transactions/{transaction_id}/disputes` | raise dispute | required | transaction parties | `{reason}` | `201 {id,status:"open"}` | reason required | 401,403,404,422 | optional | disputes | FR-062 |
| GET | `/api/v1/disputes/{dispute_id}` | dispute detail | required | party/admin | — | dispute + events | UUID | 401,403,404 | — | disputes, dispute_events | FR-062 |
| POST | `/api/v1/disputes/{dispute_id}/events` | add dispute event | required | party/admin | `{event_type,note?}` | `201 event` | — | 401,403,404 | optional | dispute_events | FR-062 |

### 5.19 Notifications (schema-ready — not yet implemented)

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/api/v1/notifications?unread_only=` | list notifications | required | own | — | `{id,type,title,body,is_read,created_at}[]` | — | 401 | — | notifications | FR-051, FR-062 ⚠ NEEDS VALIDATION |
| POST | `/api/v1/notifications/{id}/read` | mark read | required | own | — | `{status:"read"}` | UUID | 401,404 | — | notifications | FR-051, FR-062 |

### 5.20 Offline synchronization

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| POST | `/api/v1/sync` | batch idempotent sync | collector | `picker`/`kabadiwala` | `SyncRequest{operations:[{idempotency_key,entity_type,id,payload}]}` | `SyncResponse{results:[{idempotency_key,entity_id,status,error}]}` | entity_type ∈ lot/lot_item/transaction/weight/payment | 401,403,422 | required (per-op key) | sync_operations, lots, lot_items, transactions, weights, payments | FR-042, FR-044, TR-016 |

Supported `entity_type`: `lot`, `lot_item`, `transaction`, `weight`, `payment`.
Each op commits independently; a repeated key returns `status: "replayed"` with
the original `entity_id`.

### 5.21 Admin

| Method | Path | Purpose | Auth | Authorization | Request | Response | Validation | Errors | Idempotency | Tables | RTM |
| ------ | ---- | ------- | ---- | ------------- | ------- | -------- | ---------- | ------ | ----------- | ------ | --- |
| GET | `/api/v1/admin/roles` | list roles | required | `platform_admin` | — | `RoleOut[]{id,code,name,description}` | — | 401,403 | — | roles | FR-001, FR-002 |
| GET | `/api/v1/audit-events?entity_type=&entity_id=` | list audit trail | required | `platform_admin` | query filters | `audit_events[]` | — | 401,403 | — | audit_events | FR-057 |

### 5.22 Audit

Audit is a cross-cutting concern (FR-057), not a standalone domain: important
mutations write `audit_events` (actor, action, entity, before/after JSON). The
only audit endpoint is the admin read in §5.21.

---

## 6. Cross-cutting requirements

| Concern | Implementation | RTM |
| ------- | -------------- | --- |
| Rate limiting | fixed-window middleware (in-memory; Redis for scale) | FR-056 |
| CORS | origin allow-list from `BACKEND_CORS_ORIGINS` | FR-052 |
| Validation | Pydantic on every request body/query | FR-055 |
| Secrets | env-only (`Settings` via pydantic-settings) | FR-059 |
| No Aadhaar | absent from all schemas | FR-061 |

---

## 7. Implementation status

**Implemented (existing `app/routers/`)**: health, me, taxonomy, roles, lots,
items, images, classify/confirm/correct, upload-params, price-observations,
estimate, recycler (CRUD + verified + acceptance), nearby, matches, transactions,
events, transition, weights, payments, confirm, sync.

**Schema-ready / planned (no endpoint yet)**: quotes, handover, disputes,
notifications, earnings history, audit-events read.

**Foundation (this phase)**: `app/foundation.py` demonstrates the layered
health domain (route → service → repository) and the error/exception-handling
envelope; it is the template the remaining domains migrate onto.
