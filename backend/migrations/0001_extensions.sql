-- 0001_extensions.sql
-- Enable required extensions and shared helper functions.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Trigger helper: keep `updated_at` fresh on UPDATE.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
