-- 0024_price_history_unique.sql
-- The history derivation job upserts on (category, region, period_start). That
-- requires a matching unique constraint, which the original table lacks.
-- Without it, ON CONFLICT fails and trends can never be refreshed.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_price_history_bucket'
    ) THEN
        ALTER TABLE price_history
            ADD CONSTRAINT uq_price_history_bucket
            UNIQUE (material_category_id, region, period_start);
    END IF;
END $$;
