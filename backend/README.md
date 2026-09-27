# Kabadi Mitra — Backend (FastAPI)

Authoritative REST API for Kabadi Mitra. Verifies Supabase Auth JWTs, enforces
RBAC and organization isolation, records audit events, and guards mutating
requests with idempotency keys.

## Setup

Requires Python 3.13+ (use the `py -3` launcher on Windows).

```bash
cd backend
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Create the repo-root `.env` (git-ignored) with `DATABASE_URL` and the Supabase
variables — see `../.env.example`.

## Run (development)

On **Windows**, uvicorn forces `ProactorEventLoop`, which psycopg async cannot
use, so use the bundled entrypoint:

```bash
.venv\Scripts\python.exe run.py
```

On **Linux / Render** (production), the default loop works fine:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Test

```bash
.venv\Scripts\python.exe -m pytest -q
```

Tests use FastAPI's TestClient with the live Supabase database (integration) and
override the auth dependency with a fake principal (no Supabase login needed).

## Layout

```
backend/
├── app/
│   ├── main.py          # FastAPI app + lifespan (DB pool)
│   ├── config.py        # env-driven settings
│   ├── db.py            # async connection pool + get_db dependency
│   ├── auth.py          # JWT verify + principal resolution
│   ├── dependencies.py  # require_role, org_scope
│   ├── audit.py         # audit-event writer
│   ├── idempotency.py   # Idempotency-Key middleware
│   ├── schemas.py       # Pydantic models
│   ├── loops.py         # Windows selector-loop factory
│   └── routers/         # health, auth (me), taxonomy, admin
├── migrations/          # Phase 1 SQL migrations + Node runner
├── tests/
└── run.py               # Windows dev entrypoint
```

## API surface (Phases 2–6)

| Method | Path | Auth | Notes |
| ------ | ---- | ---- | ----- |
| GET | `/health` | none | liveness |
| GET | `/health/ready` | none | DB ping |
| GET | `/api/v1/me` | required | current principal (auto-provisions user) |
| GET | `/api/v1/taxonomy/collector-categories?locale=` | required | localized collector taxonomy |
| GET | `/api/v1/admin/roles` | `platform_admin` | RBAC-guarded |
| POST | `/api/v1/lots` | collector | create lot |
| GET | `/api/v1/lots` | collector | list collector's lots |
| GET | `/api/v1/lots/{id}` | collector | lot detail |
| POST | `/api/v1/lots/{id}/items` | collector | add item |
| POST | `/api/v1/lots/{id}/items/{item_id}/images` | collector | attach image (Cloudinary metadata) |
| POST | `/api/v1/lot-items/{item_id}/classify` | collector | AI classify (pluggable) |
| POST | `/api/v1/ai-decisions/{id}/confirm` | collector | confirm AI suggestion |
| POST | `/api/v1/ai-decisions/{id}/correct` | collector | correct (training candidate) |
| GET | `/api/v1/media/upload-params` | required | Cloudinary signed-upload params |
| POST | `/api/v1/price-observations` | required | record a price observation |
| GET | `/api/v1/pricing/estimate` | required | contextual price estimate |
| POST | `/api/v1/recycler/organizations` | `platform_admin`/`recycler` | onboard recycler |
| GET | `/api/v1/recycler/organizations` | `platform_admin` | list recyclers |
| GET | `/api/v1/recycler/organizations/{id}` | `platform_admin` | recycler detail + status |
| GET | `/api/v1/recycler/verified` | required | verified non-expired recyclers |
| POST | `/api/v1/recycler/organizations/{id}/acceptance` | `platform_admin` | set accepted materials |
| POST | `/api/v1/lots/{id}/matches` | collector | generate ranked matches |
| GET | `/api/v1/lots/{id}/matches` | collector | list matches |
| POST | `/api/v1/lots/{id}/transactions` | collector | create transaction |
| GET | `/api/v1/transactions/{id}` | collector | transaction detail |
| GET | `/api/v1/transactions/{id}/events` | collector | lifecycle events |
| POST | `/api/v1/transactions/{id}/transition` | collector | advance lifecycle state |
| POST | `/api/v1/transactions/{id}/weights` | collector | record weight |
| POST | `/api/v1/transactions/{id}/payments` | collector | record payment |
| POST | `/api/v1/payments/{id}/confirm` | collector | confirm payment |
| POST | `/api/v1/sync` | collector | batch idempotent offline sync |
| GET | `/api/v1/recycler/nearby` | required | nearby recyclers (PostGIS) |

Auth is a `Authorization: Bearer <supabase-jwt>` header. Mutating requests should
send an `Idempotency-Key` header (e.g. `KC-LOT-260926-000482`); duplicate keys
receive `409` and are never re-processed.
