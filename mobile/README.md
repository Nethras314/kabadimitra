# Kabadi Mitra — Mobile (Expo / React Native)

Offline-first collector app. The backend is authoritative; this app captures
material locally (SQLite) and syncs when connectivity returns.

> **Status: Phase 7 foundation.** The offline data layer is implemented and
> unit-tested; UI screens and on-device runtime are not yet built/verified.

## Layout

```
mobile/
├── App.tsx                  # entry (placeholder)
├── app.json                  # Expo config (Android-first)
├── src/
│   ├── types/                # entity + sync types (mirror backend contract)
│   ├── lib/                  # uuid + idempotency-key generators (pure)
│   ├── sync/                 # outbox queue + sync client (pure)
│   ├── api/                  # backend fetch wrapper
│   ├── db/                   # local SQLite schema
│   └── i18n/                 # 8 locales (en + hi seeded)
└── src/**/*.test.ts          # unit tests (node:test)
```

## Run

```bash
cd mobile
npm install          # installs Expo + deps
npm start            # expo start (device/emulator)
```

## Test (no device required)

The data layer is pure TypeScript (no Expo imports), so it runs under Node:

```bash
npx tsx --test src/lib/idempotency.test.ts src/sync/queue.test.ts src/sync/client.test.ts
```

## Key decisions

- **Client-generated UUIDs** (`src/lib/uuid.ts`) and **idempotency keys**
  (`src/lib/idempotency.ts`, format `KC-<ENTITY>-<YYMMDD>-<NNNNNN>`) match the
  backend `/api/v1/sync` contract.
- The outbox queue + sync client replay idempotently — a `replayed` result is
  success, not a duplicate.
- Local SQLite mirrors the collector-editable entities (`lots`, `lot_items`) plus
  a `sync_queue` outbox.

## Not yet implemented

- Capture / lots / sync-status screens.
- Supabase Auth wiring and token storage.
- SQLite persistence adapter (schema is defined; native `expo-sqlite` calls and
  the on-device runtime are unverified).
- Full 8-language translation content (only English + Hindi seeded).
