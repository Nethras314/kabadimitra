# Security

> Phase 9 deliverable. Summarizes the security controls in place and remaining
> hardening.

## In place

- **HTTPS**: enforced by the hosts (Render, Vercel, Supabase, Cloudinary). The
  backend serves HTTP internally behind Render's TLS termination.
- **Authentication**: Supabase Auth issues JWTs; the backend verifies them
  (RS256, `iss` = `<SUPABASE_URL>/auth/v1`, `aud` = `authenticated`) against the
  project JWKS. No password handling in the backend (ADR-0015).
- **Authorization**: role-based access (`require_role`), organization isolation
  (`org_scope`), and collector ownership checks on lots/items/transactions.
- **Input validation**: Pydantic request models with `Literal` enums on every
  mutation body.
- **Rate limiting**: fixed-window per-IP middleware (`app/rate_limit.py`),
  configurable; health endpoints exempt. In-memory for single-instance.
- **Audit logging**: `audit_events` records actor, action, entity, before/after
  JSON on important mutations and state transitions.
- **Secure image handling**: images never enter PostgreSQL; Cloudinary signed
  upload + metadata-only storage (ADR-0019).
- **Secrets**: environment variables only; `.env` is git-ignored and
  `.env.example` ships empty placeholders (no secrets committed).
- **Data minimization**: auto-provisioned users store only `id` + `email`/`phone`.
- **No Aadhaar** collected or stored (FR-SEC-10).
- **RLS**: not used — the backend is the sole data-access layer (ADR-0013).

## Remaining / recommended hardening

- Redis-backed rate limiting and caching for multi-instance Render deployment.
- Secret rotation (the Supabase DB password / service key were shared in chat
  during setup).
- Rate-limit tuning per endpoint (bulk sync vs. reads).
- Secrets management via Render/Vercel/Supabase secret stores (never in
  `render.yaml`).
