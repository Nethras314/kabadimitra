-- 0013_ops.sql
-- Audit events, notifications, and sync operations (idempotency ledger).

CREATE TABLE IF NOT EXISTS audit_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id   uuid REFERENCES users(id) ON DELETE SET NULL,
    organization_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
    action          text NOT NULL,
    entity_type     text,
    entity_id       uuid,
    before          jsonb,
    after           jsonb,
    ip_address      inet,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
    type            text NOT NULL,
    title           text,
    body            text,
    is_read         boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sync_operations (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key  text NOT NULL UNIQUE,
    client_id        text,
    user_id          uuid REFERENCES users(id) ON DELETE SET NULL,
    entity_type      text,
    entity_id        uuid,
    operation        text NOT NULL CHECK (operation IN ('create','update')),
    status           text NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','applied','failed')),
    request_payload  jsonb,
    response_payload jsonb,
    error            text,
    synced_at        timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now()
);
