-- 0008_matching.sql
-- Matches between a lot and a recycler organization, with scoring factors.

CREATE TABLE IF NOT EXISTS matches (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id                   uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    recycler_organization_id uuid NOT NULL REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    score                    numeric,
    match_reason             jsonb NOT NULL DEFAULT '{}'::jsonb,
    distance_km              numeric,
    transport_cost           numeric,
    expected_net_earnings    numeric,
    status                   text NOT NULL DEFAULT 'proposed'
                             CHECK (status IN ('proposed','shown','accepted','rejected')),
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_matches_updated_at ON matches;
CREATE TRIGGER trg_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
