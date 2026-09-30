-- 0023_handover_reference.sql
-- A verifiable handover needs a first-class, unique, human-readable reference.
-- Previously the reference would have had to be smuggled into `notes`, which is
-- not queryable and not constrained. Additive only.

ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS reference_code text;
CREATE UNIQUE INDEX IF NOT EXISTS uq_handover_records_reference_code
    ON handover_records (reference_code)
    WHERE reference_code IS NOT NULL;

-- Whether the recycler has independently confirmed receipt.
ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS confirmed_at timestamptz;
ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS confirmed_by_user_id uuid
    REFERENCES users(id) ON DELETE SET NULL;

-- Weight at the moment of handover, so the record is self-contained even if the
-- transaction is later amended.
ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS weight_kg numeric;
ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS latitude numeric;
ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS longitude numeric;
ALTER TABLE handover_records ADD COLUMN IF NOT EXISTS photo_count integer NOT NULL DEFAULT 0;
