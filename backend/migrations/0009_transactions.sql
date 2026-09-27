-- 0009_transactions.sql
-- Transactions (lifecycle), events, weights, handover records.

CREATE TABLE IF NOT EXISTS transactions (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key          text UNIQUE,
    lot_id                   uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    collector_id             uuid NOT NULL REFERENCES collectors(id) ON DELETE CASCADE,
    recycler_organization_id uuid REFERENCES recycler_organizations(id) ON DELETE SET NULL,
    match_id                 uuid REFERENCES matches(id) ON DELETE SET NULL,
    status                   text NOT NULL DEFAULT 'LOT_CREATED'
                             CHECK (status IN (
                               'LOT_CREATED','CLASSIFIED','QUOTED','QUOTE_ACCEPTED',
                               'PICKUP_OR_DELIVERY','WEIGHT_VERIFIED','HANDOVER_CONFIRMED',
                               'PAYMENT_RECORDED','COMPLETED')),
    currency                 text NOT NULL DEFAULT 'INR',
    agreed_price_per_kg      numeric,
    expected_weight_kg       numeric,
    final_weight_kg          numeric,
    transport_cost           numeric,
    net_earnings             numeric,
    pickup_method            text CHECK (pickup_method IN ('pickup','delivery')),
    scheduled_at             timestamptz,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transaction_events (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id uuid NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    event_type     text NOT NULL,
    from_status    text,
    to_status      text,
    actor_user_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    metadata       jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS weights (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id     uuid NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    weight_type        text NOT NULL CHECK (weight_type IN ('declared','pickup','final')),
    weight_kg          numeric NOT NULL,
    measured_at        timestamptz NOT NULL DEFAULT now(),
    measured_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    source             text NOT NULL DEFAULT 'collector'
                       CHECK (source IN ('collector','recycler','scale')),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS handover_records (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id          uuid NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    handed_over_by_user_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    received_by_user_id     uuid REFERENCES users(id) ON DELETE SET NULL,
    handed_over_at          timestamptz NOT NULL DEFAULT now(),
    signature_ref           text,
    notes                   text,
    created_at              timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_transactions_updated_at ON transactions;
CREATE TRIGGER trg_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_weights_updated_at ON weights;
CREATE TRIGGER trg_weights_updated_at
    BEFORE UPDATE ON weights
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
