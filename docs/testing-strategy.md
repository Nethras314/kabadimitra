# Testing Strategy

> Phase 9 deliverable. What is tested, how, and what is not yet verified.

## Backend (FastAPI)

`backend/tests/` — **54 pytest tests**, integration against the live Supabase
database (with per-test cleanup), auth overridden with fake principals.

Coverage: auth/RBAC, org scope, collector ownership, lots/items/images,
AI classify/confirm/correct (training candidates), pricing observations +
estimate, recycler verification (expiry-aware), matching (verified/acceptance/
distance), transaction lifecycle (legal transitions + events), weights,
payments + confirmation, offline sync idempotent replay, PostGIS nearby search,
rate limiting, and media signature.

Run: `cd backend && .venv\Scripts\python.exe -m pytest -q`

## Mobile (Expo)

`mobile/src/**/*.test.ts` — **6 unit tests** on the pure data layer (UUID,
idempotency-key format, sync queue, sync client), run under Node via `tsx`.
TypeScript typecheck of the data layer is clean.

Run: `cd mobile && npx tsx --test src/lib/idempotency.test.ts src/sync/queue.test.ts src/sync/client.test.ts`

## Web (Next.js)

`next build` compiles and type-checks the app (route + map component).

Run: `cd web && npm run build`

## Not yet verified

- Mobile on-device runtime (needs an Android emulator/device).
- Cloudinary upload path (needs real credentials).
- Real AI provider (only `NullProvider` tested).
- Browser map rendering (needs a running backend + Supabase token + browser).
- Rate limiting under a real multi-instance load (in-memory only).

## Future

- CI running backend pytest + web `next build` on every PR.
- E2E flow tests (capture → classify → match → transaction → payment).
