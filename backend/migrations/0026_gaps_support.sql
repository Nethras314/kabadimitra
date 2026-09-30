-- 0026_gaps_support.sql
-- Supporting structures for: safety audio assets, AI escalation, dispute
-- resolution workflow, and dataset validation. Additive only.

-- ------------------------------------------------------------------ audio
-- Pre-recorded voice guidance. We store the asset reference, not the bytes;
-- audio lives in Cloudinary like every other media object.
CREATE TABLE IF NOT EXISTS safety_audio_assets (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id      uuid NOT NULL REFERENCES safety_topics(id) ON DELETE CASCADE,
    locale        text NOT NULL CHECK (locale IN ('en','hi','mr','ta','te','ml','kn','bn')),
    cloudinary_public_id text NOT NULL,
    cloudinary_url text NOT NULL,
    duration_seconds numeric,
    voice         text,                  -- narrator/voice label for auditing
    is_complete   boolean NOT NULL DEFAULT false,  -- false until reviewed
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (topic_id, locale)
);

-- ------------------------------------------------------------------ escalation
-- Escalation of uncertain AI classifications: recycler reviews first, then
-- admin. Kept separate from ai_decisions so the review trail is auditable and
-- a decision is never overwritten in place.
CREATE TABLE IF NOT EXISTS ai_escalations (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id        uuid NOT NULL REFERENCES ai_decisions(id) ON DELETE CASCADE,
    lot_item_id        uuid REFERENCES lot_items(id) ON DELETE CASCADE,
    stage              text NOT NULL DEFAULT 'recycler'
                       CHECK (stage IN ('recycler', 'admin', 'resolved', 'rejected')),
    reason             text,               -- why escalation was needed
    raised_by_user_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    resolved_category_id uuid REFERENCES material_categories(id) ON DELETE SET NULL,
    resolution         text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    resolved_at        timestamptz,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_escalations_stage
    ON ai_escalations (stage, created_at DESC);

-- ------------------------------------------------------------------ disputes
-- Dispute workflow needs a reason code (for analytics) and an assignment so a
-- dispute has an owner. Existing disputes keep working; these are nullable.
ALTER TABLE disputes
    ADD COLUMN IF NOT EXISTS reason_code text;
ALTER TABLE disputes
    ADD COLUMN IF NOT EXISTS assigned_to_user_id uuid REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE disputes
    ADD COLUMN IF NOT EXISTS category text
        CHECK (category IS NULL OR category IN
               ('price', 'weight', 'quality', 'payment', 'damage', 'other'));

-- ------------------------------------------------------------------ notifications
-- Delivery channel. 'in_app' is always written; push is optional and only
-- attempted when a push token is registered, so a missing APNs/FCM setup never
-- loses the notification.
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS channel text NOT NULL DEFAULT 'in_app'
        CHECK (channel IN ('in_app', 'push', 'sms'));
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS entity_type text;
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS entity_id uuid;
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS read_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON notifications (user_id, is_read, created_at DESC);

-- ------------------------------------------------------------------ validation
-- Dataset quality findings. The validation job writes here so data problems
-- are visible rather than silently accepted.
CREATE TABLE IF NOT EXISTS dataset_validation_runs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset      text NOT NULL,          -- price | recycler | material | transaction
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    rows_scanned integer NOT NULL DEFAULT 0,
    issues_found integer NOT NULL DEFAULT 0,
    status       text NOT NULL DEFAULT 'running'
                 CHECK (status IN ('running', 'passed', 'failed', 'warning')),
    summary      jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS dataset_validation_issues (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       uuid NOT NULL REFERENCES dataset_validation_runs(id) ON DELETE CASCADE,
    dataset      text NOT NULL,
    severity     text NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    code         text NOT NULL,
    entity_type  text,
    entity_id    uuid,
    message      text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_validation_issues_run
    ON dataset_validation_issues (run_id, severity);

DROP TRIGGER IF EXISTS trg_ai_escalations_updated_at ON ai_escalations;
CREATE TRIGGER trg_ai_escalations_updated_at
    BEFORE UPDATE ON ai_escalations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
