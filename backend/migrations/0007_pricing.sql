-- 0007_pricing.sql
-- Price observations (provenance-backed), derived history, recycler quotes.

CREATE TABLE IF NOT EXISTS price_observations (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    material_category_id    uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    material_subcategory_id uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    grade_id                uuid REFERENCES material_grades(id) ON DELETE SET NULL,
    location                geography(Point, 4326),
    city                    text,
    state                   text,
    observed_price_per_kg   numeric NOT NULL,
    currency                text NOT NULL DEFAULT 'INR',
    buyer_type              text CHECK (buyer_type IN ('recycler','aggregator','other')),
    buyer_organization_id   uuid REFERENCES organizations(id) ON DELETE SET NULL,
    source                  text NOT NULL
                            CHECK (source IN ('collector_entry','recycler_quote','market','verification')),
    source_user_id          uuid REFERENCES users(id) ON DELETE SET NULL,
    weight_kg               numeric,
    transport_cost          numeric,
    verification_status     text NOT NULL DEFAULT 'unverified'
                            CHECK (verification_status IN ('unverified','verified')),
    observed_at             timestamptz NOT NULL DEFAULT now(),
    notes                   text,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS price_history (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    material_category_id    uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    material_subcategory_id uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    region                  text,
    period_start            date NOT NULL,
    period_end              date NOT NULL,
    average_price_per_kg    numeric,
    min_price_per_kg        numeric,
    max_price_per_kg        numeric,
    sample_count            integer NOT NULL DEFAULT 0,
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recycler_quotes (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recycler_organization_id uuid NOT NULL REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    lot_id                   uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    price_per_kg             numeric,
    total_price              numeric,
    currency                 text NOT NULL DEFAULT 'INR',
    grade_id                 uuid REFERENCES material_grades(id) ON DELETE SET NULL,
    terms                    text,
    status                   text NOT NULL DEFAULT 'submitted'
                             CHECK (status IN ('draft','submitted','accepted','rejected','expired')),
    valid_until              timestamptz,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_price_observations_updated_at ON price_observations;
CREATE TRIGGER trg_price_observations_updated_at
    BEFORE UPDATE ON price_observations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_recycler_quotes_updated_at ON recycler_quotes;
CREATE TRIGGER trg_recycler_quotes_updated_at
    BEFORE UPDATE ON recycler_quotes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
