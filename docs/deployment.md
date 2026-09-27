# Deployment

> Phase 9 deliverable. Hosting topology and deployment steps.

## Topology

| Component | Host | Notes |
| --------- | ---- | ----- |
| Backend (FastAPI) | Render | `render.yaml` at repo root |
| Web (Next.js) | Vercel | `web/vercel.json` (auto-detected) |
| Database | Supabase | PostgreSQL + PostGIS |
| Media | Cloudinary | signed direct upload |
| Cache/jobs | Redis | reserved; not yet wired |

## Backend (Render)

`render.yaml` (repo root) defines a Python web service rooted at `backend/`,
`pip install -r requirements.txt`, start `uvicorn app.main:app`. Set the
following env vars (Render secret store, `sync: false`):

`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWKS_URL`, `CLOUDINARY_CLOUD_NAME`,
`CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `REDIS_URL`, `AI_API_KEY`,
`BACKEND_CORS_ORIGINS`.

## Web (Vercel)

Vercel auto-detects Next.js. Set `NEXT_PUBLIC_API_URL` to the Render URL.

## Database migrations

Apply `backend/migrations/*.sql` in filename order:

```bash
node backend/migrations/run.js   # reads DATABASE_URL from .env
```

Or paste them into the Supabase SQL editor in order. PostGIS is enabled by
migration `0001_extensions.sql`.

## HTTPS

TLS is terminated at each host. The backend binds HTTP on `$PORT`; Render fronts
it with HTTPS.

## Open items

- CI/CD pipeline for tests + builds on merge.
- Redis provisioning and wiring for rate limiting / background jobs.
- Staging environment configuration.
