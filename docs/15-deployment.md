# Deployment

> Deployment-readiness deliverable. Target topology, environment variables, and
> connectivity verification. No secrets are committed; no automatic deployment
> is performed (credentials are not provisioned in this repository).

## 1. Topology

| Component | Host | Entrypoint / config |
| --------- | ---- | ------------------- |
| Backend (FastAPI) | Render | `render.yaml` (root), `uvicorn app.main:app` |
| Web (Next.js) | Vercel | `web/vercel.json` (auto-detected) |
| Database | Supabase | PostgreSQL + PostGIS |
| Images | Cloudinary | signed direct upload |
| Cache/jobs | Redis | reserved; not yet wired into rate limiting |
| Mobile | Expo / Android | EAS build + `EXPO_PUBLIC_API_URL` |

```
Mobile (Expo) ──HTTPS──> FastAPI (Render)
Web (Next.js/Vercel) ──HTTPS──> FastAPI (Render)
FastAPI ──> Supabase PostgreSQL/PostGIS
FastAPI ──> Cloudinary (signed upload)
FastAPI ──> Redis (cache/jobs, optional)
FastAPI ──> AI service (pluggable)
```

## 2. Health & readiness

| Endpoint | Purpose | Note |
| -------- | ------- | ---- |
| `GET /health` | liveness | always `200` when the process is up |
| `GET /health/ready` | readiness | pings the database; `503` when `DATABASE_URL` is unset/unreachable |

Render uses `/health` for liveness; `/health/ready` is the readiness probe.

## 3. Environment variables (no secrets shown)

All values are empty placeholders in `.env.example`; production values live in
each host's secret store.

| Category | Variables |
| -------- | --------- |
| DATABASE | `DATABASE_URL`, `DATABASE_URL_DIRECT`, `DATABASE_POOL_URL` |
| SUPABASE | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWKS_URL` |
| CLOUDINARY | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_SECURE_URL_PREFIX` |
| REDIS | `REDIS_URL` |
| AI | `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL`, `AI_CONFIDENCE_THRESHOLD`, `AI_REVIEW_THRESHOLD` |
| AUTH | `JWT_AUDIENCE`, `JWT_ISSUER_SUFFIX` |
| CORS | `BACKEND_CORS_ORIGINS` |
| FRONTEND | `FRONTEND_URL` |

> **Note**: `BACKEND_CORS_ORIGINS` is the canonical CORS variable; the
> `cors_origins` setting reads it via a `validation_alias`. `FRONTEND_URL` is the
> Vercel URL (for redirects/links, not yet consumed).

## 4. Service configuration

### Render (backend)

`render.yaml` builds `backend/` (`pip install -r requirements.txt`) and starts
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set the secret vars in the
Render dashboard (not committed).

### Vercel (web)

Vercel auto-detects Next.js. Set `NEXT_PUBLIC_API_URL` to the Render service URL,
and `NEXT_PUBLIC_MAPLIBRE_TOKEN` (or use OSM tiles, no token).

### Supabase (database)

Enable PostGIS (migration `0001_extensions.sql`) and apply migrations in order:

```bash
node backend/migrations/run.js   # reads DATABASE_URL
```

or paste `backend/migrations/*.sql` into the Supabase SQL editor in filename order.

### Cloudinary

Provision an account; set the three `CLOUDINARY_*` secrets. The backend issues
signed-upload parameters at `GET /api/v1/media/upload-params`.

### Redis

Set `REDIS_URL`. Rate limiting currently uses in-memory counters; wire Redis
before scaling the backend horizontally.

### AI service

Set `AI_PROVIDER` (default `none` = manual classification). For a real provider,
set `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` and register the provider in
`app/ai/`.

## 5. Connectivity verification matrix

| Link | Verification |
| ---- | ------------ |
| Frontend → Backend | `NEXT_PUBLIC_API_URL`/`EXPO_PUBLIC_API_URL` point at Render; `BACKEND_CORS_ORIGINS` includes the Vercel origin |
| Backend → Database | `DATABASE_URL` set; `GET /health/ready` returns `200` |
| Backend → Cloudinary | `CLOUDINARY_*` set; `GET /api/v1/media/upload-params` returns `200` (not `503`) |
| Backend → Redis | `REDIS_URL` set; future: rate limiter/cache uses it |
| Backend → AI service | `AI_PROVIDER` set; classify returns a non-empty prediction |

These are configuration checks, not automatic deploy steps. **No deployment is
performed** here (no credentials are present).

## 6. Security notes

- No `.env` with secrets is committed; only `.env.example` (empty placeholders).
- TLS terminates at Render/Vercel/Supabase/Cloudinary.
- Secrets live in each host's secret store, never in `render.yaml`/`vercel.json`.

## 7. Open items

- CI/CD pipeline (backend unit tests + web build on PR).
- Redis wiring for multi-instance rate limiting.
- A staging environment.
- Migrating the HTTP entrypoint from `app.main:app` (legacy) to the clean
  layered `app.foundation:app` as domains are wired.
