-- 0018_transaction_handover_idempotency.sql
-- Add an idempotency key to handover records so repeated handover sync requests
-- cannot create duplicate records. Additive only.

ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS idempotency_key text;
CREATE UNIQUE INDEX IF NOT EXISTS uq_handover_records_idempotency_key
    ON handover_records (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
