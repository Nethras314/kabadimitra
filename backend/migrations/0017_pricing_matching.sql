-- 0017_pricing_matching.sql
-- Add unit + confidence to price observations and pickup capability to recyclers.
-- Additive only — preserves existing data.

ALTER TABLE price_observations ADD COLUMN IF NOT EXISTS unit text;
ALTER TABLE price_observations ADD COLUMN IF NOT EXISTS confidence numeric NOT NULL DEFAULT 1.0;
ALTER TABLE recycler_organizations ADD COLUMN IF NOT EXISTS pickup_available boolean NOT NULL DEFAULT false;
