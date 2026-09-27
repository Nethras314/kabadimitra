-- 0003_collectors.sql
-- Collector profiles (picker / kabadiwala).

CREATE TABLE IF NOT EXISTS collectors (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          uuid REFERENCES users(id) ON DELETE SET NULL,
    organization_id  uuid REFERENCES organizations(id) ON DELETE SET NULL,
    collector_type   text NOT NULL CHECK (collector_type IN ('picker','kabadiwala')),
    display_name     text NOT NULL,
    phone            text,
    city             text,
    state            text,
    postal_code      text,
    primary_language text NOT NULL DEFAULT 'hi',
    status           text NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active','inactive','suspended')),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_collectors_updated_at ON collectors;
CREATE TRIGGER trg_collectors_updated_at
    BEFORE UPDATE ON collectors
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
