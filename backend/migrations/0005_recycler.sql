-- 0005_recycler.sql
-- Recycler organizations, facilities, authorizations, acceptance, service areas.

CREATE TABLE IF NOT EXISTS recycler_organizations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     uuid NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
    gstin               text,
    registration_number text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recycler_facilities (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recycler_organization_id  uuid NOT NULL REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    name                      text NOT NULL,
    address_line              text,
    city                      text,
    state                     text,
    postal_code               text,
    location                  geography(Point, 4326),
    is_active                 boolean NOT NULL DEFAULT true,
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recycler_facilities_location
    ON recycler_facilities USING gist (location);

CREATE TABLE IF NOT EXISTS recycler_authorizations (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recycler_organization_id uuid NOT NULL REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    authorization_number     text NOT NULL,
    issuing_authority        text,
    authorization_type       text,
    issue_date               date,
    expiry_date              date,
    verification_source      text,
    verification_date        timestamptz,
    status                   text NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('verified','pending','expiring','expired','suspended')),
    document_url             text,
    notes                    text,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recycler_material_acceptance (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recycler_organization_id uuid NOT NULL REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    material_category_id     uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    material_subcategory_id  uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    is_accepted              boolean NOT NULL DEFAULT true,
    notes                    text,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now(),
    UNIQUE (recycler_organization_id, material_category_id, material_subcategory_id)
);

CREATE TABLE IF NOT EXISTS recycler_service_areas (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recycler_organization_id uuid NOT NULL REFERENCES recycler_organizations(id) ON DELETE CASCADE,
    name                     text NOT NULL,
    radius_km                numeric NOT NULL DEFAULT 0,
    center                   geography(Point, 4326),
    area                     geography(Polygon, 4326),
    is_active                boolean NOT NULL DEFAULT true,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_recycler_organizations_updated_at ON recycler_organizations;
CREATE TRIGGER trg_recycler_organizations_updated_at
    BEFORE UPDATE ON recycler_organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_recycler_facilities_updated_at ON recycler_facilities;
CREATE TRIGGER trg_recycler_facilities_updated_at
    BEFORE UPDATE ON recycler_facilities
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_recycler_authorizations_updated_at ON recycler_authorizations;
CREATE TRIGGER trg_recycler_authorizations_updated_at
    BEFORE UPDATE ON recycler_authorizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_recycler_material_acceptance_updated_at ON recycler_material_acceptance;
CREATE TRIGGER trg_recycler_material_acceptance_updated_at
    BEFORE UPDATE ON recycler_material_acceptance
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_recycler_service_areas_updated_at ON recycler_service_areas;
CREATE TRIGGER trg_recycler_service_areas_updated_at
    BEFORE UPDATE ON recycler_service_areas
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
