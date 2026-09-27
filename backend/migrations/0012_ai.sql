-- 0012_ai.sql
-- Pluggable AI: models, decisions, and corrections (feedback/training candidates).

CREATE TABLE IF NOT EXISTS ai_models (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider   text NOT NULL,
    model_name text NOT NULL,
    version    text,
    task       text NOT NULL CHECK (task IN ('classification','quality','valuation')),
    is_active  boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_decisions (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_model_id             uuid REFERENCES ai_models(id) ON DELETE SET NULL,
    lot_item_id             uuid REFERENCES lot_items(id) ON DELETE SET NULL,
    material_image_id       uuid REFERENCES material_images(id) ON DELETE SET NULL,
    predicted_category_id   uuid REFERENCES material_categories(id) ON DELETE SET NULL,
    predicted_subcategory_id uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    confidence              numeric NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    detected_material_types jsonb,
    quality_flags           jsonb,
    valuation_hint          jsonb,
    status                  text NOT NULL DEFAULT 'suggested'
                            CHECK (status IN ('suggested','confirmed','corrected','rejected')),
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_corrections (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_decision_id           uuid NOT NULL REFERENCES ai_decisions(id) ON DELETE CASCADE,
    corrected_category_id    uuid REFERENCES material_categories(id) ON DELETE SET NULL,
    corrected_subcategory_id uuid REFERENCES material_subcategories(id) ON DELETE SET NULL,
    corrected_by_user_id     uuid REFERENCES users(id) ON DELETE SET NULL,
    correction_type          text NOT NULL
                             CHECK (correction_type IN ('category','subcategory','grade','condition','other')),
    is_training_candidate    boolean NOT NULL DEFAULT true,
    note                     text,
    created_at               timestamptz NOT NULL DEFAULT now()
);
