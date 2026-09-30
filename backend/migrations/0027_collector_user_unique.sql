-- 0027_collector_user_unique.sql
-- `collectors.user_id` is logically one-to-one (one collector profile per
-- user) but had no unique constraint, so `ON CONFLICT (user_id)` upserts failed
-- with SQLSTATE 42P10. Found while provisioning the first real accounts.
--
-- This is also a data-integrity fix: without it, duplicate collector profiles
-- could be created for the same user, and collector resolution would be
-- ambiguous.

-- 1. De-duplicate if any already exist: keep the oldest per user.
DELETE FROM collectors c
USING collectors d
WHERE c.user_id = d.user_id
  AND c.id > d.id;

-- 2. Enforce uniqueness going forward.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_collectors_user_id'
    ) THEN
        ALTER TABLE collectors
            ADD CONSTRAINT uq_collectors_user_id UNIQUE (user_id);
    END IF;
END $$;

-- The ON CONFLICT (user_id) upserts used in application code now have a
-- matching arbiter index.
CREATE UNIQUE INDEX IF NOT EXISTS uq_collectors_user_id_idx
    ON collectors (user_id);
