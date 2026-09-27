-- 0011_disputes.sql
-- Disputes and dispute events.

CREATE TABLE IF NOT EXISTS disputes (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id   uuid NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    raised_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    reason           text NOT NULL,
    status           text NOT NULL DEFAULT 'open'
                     CHECK (status IN ('open','under_review','resolved','closed')),
    resolution       text,
    resolved_at      timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dispute_events (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dispute_id     uuid NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
    event_type     text NOT NULL,
    actor_user_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    note           text,
    created_at     timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_disputes_updated_at ON disputes;
CREATE TRIGGER trg_disputes_updated_at
    BEFORE UPDATE ON disputes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
