-- 0025_matching_enrichment.sql
-- The spec requires matching on nine factors; the first implementation used only
-- two (material coverage + proximity). This adds the data needed for the rest:
-- pickup availability, service-area coverage, reliability history, and a
-- transport-cost basis. Additive only.

-- ---------------------------------------------------------------- recycler ops
-- How a recycler serves collectors: do they collect, or must the collector
-- deliver? And is the facility accepting material right now?
ALTER TABLE recycler_organizations
    ADD COLUMN IF NOT EXISTS pickup_available boolean NOT NULL DEFAULT true;
ALTER TABLE recycler_organizations
    ADD COLUMN IF NOT EXISTS accepts_walkins boolean NOT NULL DEFAULT true;
-- Own- fleet transport offered to collectors, if any.
ALTER TABLE recycler_organizations
    ADD COLUMN IF NOT EXISTS provides_pickup boolean NOT NULL DEFAULT false;
ALTER TABLE recycler_organizations
    ADD COLUMN IF NOT EXISTS transport_rate_per_km numeric;

-- ---------------------------------------------------------------- reliability
-- Denormalised reliability snapshot, recomputed from completed transactions.
-- Kept as a table (not just a view) so scoring stays a single indexed read and
-- so history can be retained when transactions are archived.
CREATE TABLE IF NOT EXISTS recycler_reliability (
    recycler_organization_id uuid PRIMARY KEY
        REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    completed_transactions integer NOT NULL DEFAULT 0,
    disputed_transactions integer NOT NULL DEFAULT 0,
    avg_days_to_payment numeric,
    on_time_rate numeric,           -- 0..1, share of handovers confirmed same day
    acceptance_rate numeric,        -- 0..1, share of quotes accepted
    score                           numeric, -- 0..100, computed; see refresh job
    computed_at                     timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- matches
-- Factor breakdown so a collector-facing explanation can be rendered, and so
-- ranking is auditable rather than a black box.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS in_service_area boolean;
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS pickup_available boolean;
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS quote_price_per_kg numeric;
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS transport_cost numeric;
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS reliability_score numeric;
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS net_earnings numeric;

-- Recomputed by the scoring job, not by hand.
ALTER TABLE recycler_reliability
    DROP CONSTRAINT IF EXISTS chk_reliability_score;
ALTER TABLE recycler_reliability
    ADD CONSTRAINT chk_reliability_score
    CHECK (score IS NULL OR (score >= 0 AND score <= 100));

-- Index for the scoring/refresh path.
CREATE INDEX IF NOT EXISTS idx_reliability_computed
    ON recycler_reliability (computed_at);
