-- 0004_taxonomy.sql
-- Material taxonomy (backend, detailed) + collector-facing categories + i18n.
-- Equipment and recovered material are represented separately via `kind`.

CREATE TABLE IF NOT EXISTS material_categories (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code       text NOT NULL UNIQUE,
    name       text NOT NULL, -- canonical English label
    kind       text NOT NULL CHECK (kind IN ('equipment','recovered_material')),
    parent_id  uuid REFERENCES material_categories(id) ON DELETE SET NULL,
    sort_order integer NOT NULL DEFAULT 0,
    is_active  boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS material_subcategories (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    material_category_id uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    code                 text NOT NULL,
    name                 text NOT NULL,
    sort_order           integer NOT NULL DEFAULT 0,
    is_active            boolean NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (material_category_id, code)
);

CREATE TABLE IF NOT EXISTS material_grades (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        text NOT NULL UNIQUE,
    name        text NOT NULL,
    description text,
    sort_order  integer NOT NULL DEFAULT 0,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS material_conditions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        text NOT NULL UNIQUE,
    name        text NOT NULL,
    sort_order  integer NOT NULL DEFAULT 0,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS material_hazards (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        text NOT NULL UNIQUE,
    name        text NOT NULL,
    description text,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS material_hazard_links (
    material_category_id uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    material_hazard_id   uuid NOT NULL REFERENCES material_hazards(id) ON DELETE CASCADE,
    PRIMARY KEY (material_category_id, material_hazard_id)
);

-- Collector-facing simple categories (mirrors the approved 14-label list).
CREATE TABLE IF NOT EXISTS collector_categories (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code       text NOT NULL UNIQUE,
    name       text NOT NULL,
    sort_order integer NOT NULL DEFAULT 0,
    is_active  boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Maps each collector-facing category to one or more backend categories.
CREATE TABLE IF NOT EXISTS collector_category_mappings (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    collector_category_id   uuid NOT NULL REFERENCES collector_categories(id) ON DELETE CASCADE,
    material_category_id    uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    material_subcategory_id uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    created_at              timestamptz NOT NULL DEFAULT now(),
    UNIQUE (collector_category_id, material_category_id, material_subcategory_id)
);

-- Generic localization store for taxonomy labels and other translatable text.
CREATE TABLE IF NOT EXISTS translations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type text NOT NULL, -- e.g. collector_category, material_category, role
    entity_id   uuid NOT NULL,
    field       text NOT NULL, -- e.g. 'name'
    locale      text NOT NULL, -- hi, en, mr, ta, te, ml, kn, bn
    value       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (entity_type, entity_id, field, locale)
);

DROP TRIGGER IF EXISTS trg_material_categories_updated_at ON material_categories;
CREATE TRIGGER trg_material_categories_updated_at
    BEFORE UPDATE ON material_categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_material_subcategories_updated_at ON material_subcategories;
CREATE TRIGGER trg_material_subcategories_updated_at
    BEFORE UPDATE ON material_subcategories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_material_grades_updated_at ON material_grades;
CREATE TRIGGER trg_material_grades_updated_at
    BEFORE UPDATE ON material_grades
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_material_conditions_updated_at ON material_conditions;
CREATE TRIGGER trg_material_conditions_updated_at
    BEFORE UPDATE ON material_conditions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_material_hazards_updated_at ON material_hazards;
CREATE TRIGGER trg_material_hazards_updated_at
    BEFORE UPDATE ON material_hazards
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_collector_categories_updated_at ON collector_categories;
CREATE TRIGGER trg_collector_categories_updated_at
    BEFORE UPDATE ON collector_categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_translations_updated_at ON translations;
CREATE TRIGGER trg_translations_updated_at
    BEFORE UPDATE ON translations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
