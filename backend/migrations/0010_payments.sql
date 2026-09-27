-- 0010_payments.sql
-- Payments and payment confirmations. Digital payment is optional.

CREATE TABLE IF NOT EXISTS payments (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key       text UNIQUE,
    transaction_id        uuid NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    amount                numeric NOT NULL,
    currency              text NOT NULL DEFAULT 'INR',
    method                text NOT NULL CHECK (method IN ('cash','upi','bank_transfer')),
    status                text NOT NULL DEFAULT 'recorded'
                          CHECK (status IN ('recorded','confirmed','disputed')),
    payer_organization_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
    payee_user_id         uuid REFERENCES users(id) ON DELETE SET NULL,
    reference             text,
    recorded_at           timestamptz NOT NULL DEFAULT now(),
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payment_confirmations (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id           uuid NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    confirmed_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    confirmation_source  text,
    confirmed_at         timestamptz NOT NULL DEFAULT now(),
    created_at           timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_payments_updated_at ON payments;
CREATE TRIGGER trg_payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
