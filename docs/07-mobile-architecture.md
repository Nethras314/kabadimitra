# Mobile Architecture

> Expo / React Native client. This document describes the **as-built** mobile
> state: an offline-first **data layer** that is implemented and unit-tested, and
> a **UI layer that does not yet exist**.

## 1. Stack

| Concern | Choice |
| ------- | ------ |
| Framework | React Native 0.76.5 |
| Toolchain | Expo SDK 52 |
| Language | TypeScript 5.6 |
| Local DB | SQLite (via `expo-sqlite` — **declared, not yet wired**) |
| Sync | Outbox queue + idempotent `POST /api/v1/sync` |
| i18n | Static locale map (`en` + `hi` only) |
| Tests | `tsx --test` (Node `node:test`), pure TypeScript |

`app.json` declares the `expo-sqlite` plugin; `package.json` declares
`expo-sqlite ~15.0.0`. No navigation library is installed.

## 2. Directory layout (as-built)

```
mobile/
├── App.tsx                    # placeholder screen (title/subtitle only)
├── app.json                   # Expo config (name, slug, expo-sqlite plugin)
└── src/
    ├── types/index.ts         # snake_case wire + local entity types
    ├── api/client.ts          # SyncApi -> POST /api/v1/sync
    ├── db/
    │   ├── schema.ts          # SQLITE_SCHEMA DDL (declared, unused)
    │   └── store.ts           # LocalStore interface + InMemoryStore
    ├── sync/
    │   ├── queue.ts           # SyncQueue (outbox over pending_operations)
    │   ├── retry.ts           # RetryPolicy + ExponentialBackoff
    │   └── service.ts         # SyncService orchestrator
    ├── cache/cache.ts         # read-only local cache (materials/prices/safety)
    ├── offline/capabilities.ts# offline vs online capability map
    ├── i18n/locales.ts        # SUPPORTED_LOCALES (8) + en/hi content
    └── lib/
        ├── uuid.ts            # dependency-free UUID v4
        ├── idempotency.ts     # KC-<ENTITY>-<YYMMDD>-<NNNNNN>
        └── connectivity.ts    # Connectivity interface + impls
```

## 3. Design principles

1. **Data layer is pure TypeScript** — no Expo/React imports, so it is testable
   under Node (ADR-0025).
2. **Interface-driven persistence** — `SyncService`/`SyncQueue` depend on the
   `LocalStore` and `SyncApi` interfaces, not on `expo-sqlite` or `fetch`. The
   reference implementation is `InMemoryStore`; an `expo-sqlite` adapter is the
   intended on-device implementation but **has not been written**.
3. **Backend authoritative** — the device works locally but the backend is the
   source of truth; sync uses idempotency keys (ADR-0006, ADR-0024).
4. **snake_case wire contract** — `src/types/index.ts` mirrors the backend
   `/api/v1/sync` schema exactly (`idempotency_key`, `entity_type`, `entity_id`,
   `lot_id`, …), so no key-mapping layer is required (ADR-0029).

## 4. Data layer (implemented)

### 4.1 Types — `src/types/index.ts`

`SyncOperation`, `SyncResult`, `SyncResponse`, `EntityType`, and local entities
(`Lot`, `LotItem`, `LotImage`, `WeightRecord`, `CollectorProfile`,
`PendingOperation`) are **all snake_case**, matching the backend contract.

### 4.2 Local schema — `src/db/schema.ts`

`SQLITE_SCHEMA` declares nine tables:

- Working data: `lots`, `lot_items`, `lot_images`, `weights`
- Outbox: `pending_operations`
- Read-only cache: `materials`, `cached_prices`, `safety_content`
- Identity cache: `collector_profile`

**Status: PLANNED (adapter missing).** The DDL string is defined but never
executed; no `expo-sqlite` adapter exists.

### 4.3 Store — `src/db/store.ts`

`LocalStore` interface + `InMemoryStore` (Maps). **IMPLEMENTED** (tested).

### 4.4 Outbox — `src/sync/queue.ts`

`SyncQueue` stages local work before it reaches the backend: `enqueue`,
`pending`, `markSynced`, `markFailed`, `retryFailed`. **IMPLEMENTED** (tested).

### 4.5 Retry — `src/sync/retry.ts`

`ExponentialBackoff` (`maxAttempts=3`, `baseDelayMs=1000`, `factor=2`);
`shouldRetry` = `failed && attempts < maxAttempts`. **IMPLEMENTED** (tested).
Note: `delayMs` is defined but not invoked by the sync service yet.

### 4.6 Sync orchestrator — `src/sync/service.ts`

`SyncService.createLot()`/`addItem()` (offline capture), `flush()` (POST pending
ops, no-op when offline), `sync()`, `status()`, `reconcile()` (`applied` and
`replayed` both treated as success). **IMPLEMENTED** (tested).

### 4.7 API client — `src/api/client.ts`

`ApiClient.post()` serializes `{ operations }` directly (snake_case) to
`POST {baseUrl}/api/v1/sync`. Adds `Authorization: Bearer` only if a `getToken()`
callback supplies a token (default `null`). **IMPLEMENTED** (tested).

### 4.8 Offline capability map — `src/offline/capabilities.ts`

Explicitly partitions capabilities into `OFFLINE_SUPPORTED` and
`ONLINE_REQUIRED` (see [08-offline-sync.md](08-offline-sync.md) §2).
**IMPLEMENTED**.

## 5. UI layer (missing)

`App.tsx` is a placeholder rendering a static title/subtitle. There are **no
screens, no navigation, no components**, and no Supabase Auth / token storage.
All capture screens, sync-status UI, and auth wiring are **PLANNED**.

## 6. i18n

`SUPPORTED_LOCALES` declares 8 locales; only `en` and `hi` have content.
**PARTIAL** (6 locales pending).

## 7. Status

| Area | Status |
| ---- | ------ |
| Wire types (snake_case) | IMPLEMENTED |
| Outbox queue / retry / sync service | IMPLEMENTED |
| In-memory store | IMPLEMENTED |
| `expo-sqlite` adapter | PLANNED (not written) |
| Screens / navigation | PLANNED |
| Supabase Auth + token storage | PLANNED |
| i18n (en + hi) | PARTIAL |

## 8. Validation

- `npm test` — 20 tests, all passing (idempotency key format, outbox lifecycle,
  retry policy, sync service end-to-end incl. airplane mode / duplicate
  prevention / interrupted sync).
- `npm run typecheck` — clean.
- **NEEDS FIELD VALIDATION** — the app has never run on a device/emulator; the
  `expo-sqlite` adapter and `NetInfo`/`ReachabilityConnectivity` path are
  unverified at runtime.
