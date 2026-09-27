# API Design

> Phase 2 deliverable. Describes the REST API surface, conventions, auth model,
> and cross-cutting concerns. This is the **Phase 2 core**; domain endpoints
> (lots, matching, transactions, payments) arrive in later phases.

## 1. Conventions

- Base path: `/api/v1`.
- JSON request/response bodies; UTF-8.
- Errors use a consistent shape:
  `{"detail": "<message>"}` (FastAPI default) — extended later if needed.
- Dates are ISO-8601 `timestamptz`.

## 2. Authentication & authorization

- **Identity provider**: Supabase Auth. The client obtains a Supabase access
  token; the backend verifies it against the project JWKS
  (`SUPABASE_JWKS_URL`), checking `alg=RS256`, `iss=<SUPABASE_URL>/auth/v1`, and
  `aud=authenticated`. (ADR-0015.)
- The JWT `sub` maps to our `users.id`. On first authenticated request the
  backend **auto-provisions** a minimal `users` row from the token's
  `email`/`phone` (idempotent).
- **RBAC**: a `require_role("platform_admin", ...)` dependency checks the
  principal's roles (from `user_roles` → `roles`). Missing role → `403`.
- **Organization isolation**: `org_scope(principal)` returns a SQL filter that
  scopes queries to the principal's organization; `platform_admin` sees all, a
  scoped user sees only their org, a user with no org sees nothing. Applied to
  org-scoped resources in Phase 3+.
- No Aadhaar is collected or stored (FR-SEC-10).

## 3. Endpoints (Phase 2)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| GET | `/health` | none | liveness probe |
| GET | `/health/ready` | none | readiness (DB `SELECT 1`) |
| GET | `/api/v1/me` | required | current principal: roles, org, locale |
| GET | `/api/v1/taxonomy/collector-categories` | required | collector taxonomy, `?locale=hi|en|…` |
| GET | `/api/v1/admin/roles` | `platform_admin` | list roles (RBAC demo) |

## 4. Idempotency

Mutating requests (`POST`/`PUT`/`PATCH`) may carry an `Idempotency-Key` header
(e.g. `KC-LOT-260926-000482`). The key is recorded in `sync_operations` (unique
constraint); a repeated key returns `409` and is never processed twice. This
guarantees offline sync cannot create duplicate lots/transactions. Full
response-replay + entity mapping is Phase 6.

## 5. Audit

`record_audit(...)` writes `audit_events` (actor, organization, action, entity,
before/after JSON, IP). Wired to important state transitions as those endpoints
land (transaction lifecycle in Phase 5).

## 6. Validation & security

- Input validation via Pydantic (FastAPI). Minimal in Phase 2 (no mutation
  bodies yet); applied as endpoints land.
- Secrets from environment; never in code or the repo.
- Rate limiting and full security hardening are Phase 9.

## 7. Open items

- Request-body schemas and mutation endpoints (Phase 3: lots/items/images).
- Error-code taxonomy and i18n of error messages (Phase 7).
- API versioning strategy if breaking changes arise (currently single `/v1`).
