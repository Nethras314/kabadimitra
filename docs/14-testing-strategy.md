# Testing Strategy

> QA phase deliverable. What is actually tested, how, and what is blocked or
> needs field validation. Updated to reflect the clean layered backend.

## Backend (FastAPI)

### Unit tests — `backend/tests/unit/` (72 tests, all passing)

Pure business logic, tested with in-memory repositories (no live database):

- **Security**: role hierarchy, `require_role`, `org_scope`, rate limiter,
  validation-error sanitization.
- **Admin**: role-gated recycler verification, expiry review, disputes, AI/price
  review, user support, audit.
- **AI**: confidence tiers (HIGH/MEDIUM/LOW), reference classifier,
  classify/confirm/correct, corrections-as-training-candidates, indicative
  valuation.
- **Pricing**: observations, historical/range, location-aware weighting,
  buyer/quote comparison, price-kind labels.
- **Recycler/matching**: `effective_authorization` (expired/suspended),
  composite-score gates (material/service area/transport/quote).
- **Transaction**: full end-to-end lifecycle, illegal transitions, idempotency
  (create/handover/payment), weights, payment methods, dispute, earnings,
  audit-event count.

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/unit -q`

### Legacy integration tests — `backend/tests/` (54 tests) — **BLOCKED**

These hit a live Supabase database via `TestClient` and **cannot run** without a
`DATABASE_URL`. They hang awaiting a connection. They are not part of the unit
run and require a Supabase test project to be provisioned.

Run (requires live DB): `cd backend && .venv\Scripts\python.exe -m pytest -q`

## Mobile (Expo)

`mobile/src/**/*.test.ts` — **20 unit tests** on the offline data layer (uuid,
idempotency-key format, outbox queue, retry, sync service: airplane mode,
reconnect, repeated sync, duplicate prevention, interrupted sync). Run under
`tsx`.

Run: `cd mobile && npm test` · Typecheck: `npm run typecheck`

## Web (Next.js)

`next build` compiles and type-checks the nearby-recycler page + MapLibre map.
Not re-run this phase (no browser/backend token).

## Specific scenarios verified

Offline lot, sync, duplicate prevention (replayed → success), AI low confidence
(manual), human correction (training candidate), expired recycler (excluded),
unsupported material (excluded), distance/proximity matching, transport cost,
price observation provenance, quote acceptance, handover, cash payment, dispute,
audit event — all covered by the unit suites above.

## Blocked / needs field validation

- **BLOCKED — no live Supabase DB**: HTTP/API integration tests, PostGIS distance
  queries (`ST_DWithin`/`ST_Distance`) against real data, and the legacy
  integration suite.
- **NEEDS FIELD VALIDATION — mobile device**: on-device `expo-sqlite` adapter and
  `NetInfo` connectivity.
- **NEEDS FIELD VALIDATION — real AI provider**: only `NullProvider` +
  `ReferenceProvider` are exercised; no real model.
- **NEEDS FIELD VALIDATION — Cloudinary**: signed upload untested (no credentials).

## Future

- CI running backend unit tests + web build on every PR.
- A dedicated Supabase test database so the legacy integration suite can run.
- E2E flow: capture → classify → match → transaction → payment.
