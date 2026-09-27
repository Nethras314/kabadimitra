-- 0006_lots.sql
-- Lots, lot items, and material images (media stored in Cloudinary).

CREATE TABLE IF NOT EXISTS lots (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key  text UNIQUE,
    collector_id     uuid NOT NULL REFERENCES collectors(id) ON DELETE CASCADE,
    organization_id  uuid REFERENCES organizations(id) ON DELETE SET NULL,
    status           text NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft','ready','synced','matched','closed')),
    title            text,
    notes            text,
    currency         text NOT NULL DEFAULT 'INR',
    pickup_location  geography(Point, 4326),
    pickup_address   text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lot_items (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id                  uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
    collector_category_id   uuid REFERENCES collector_categories(id) ON DELETE SET NULL,
    material_category_id    uuid REFERENCES material_categories(id) ON DELETE SET NULL,
    material_subcategory_id uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    kind                    text CHECK (kind IN ('equipment','recovered_material')),
    description             text,
    quantity                integer NOT NULL DEFAULT 1,
    declared_weight_kg      numeric,
    condition_id            uuid REFERENCES material_conditions(id) ON DELETE SET NULL,
    classification_source   text NOT NULL DEFAULT 'collector'
                            CHECK (classification_source IN ('collector','ai','recycler','admin')),
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS material_images (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_item_id          uuid REFERENCES lot_items(id) ON DELETE CASCADE,
    lot_id               uuid REFERENCES lots(id) ON DELETE CASCADE,
    collector_id         uuid REFERENCES collectors(id) ON DELETE SET NULL,
    cloudinary_public_id text,
    cloudinary_url       text,
    image_kind           text NOT NULL DEFAULT 'capture'
                         CHECK (image_kind IN ('capture','quality_check','handover','other')),
    is_primary           boolean NOT NULL DEFAULT false,
    mime_type            text,
    width                integer,
    height               integer,
    captured_at          timestamptz NOT NULL DEFAULT now(),
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_lots_updated_at ON lots;
CREATE TRIGGER trg_lots_updated_at
    BEFORE UPDATE ON lots
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_lot_items_updated_at ON lot_items;
CREATE TRIGGER trg_lot_items_updated_at
    BEFORE UPDATE ON lot_items
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_material_images_updated_at ON material_images;
CREATE TRIGGER trg_material_images_updated_at
    BEFORE UPDATE ON material_images
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
