-- 0020_safety_content.sql
-- Safety guidance content. The spec requires pictorial and/or audio guidance on
-- hazardous practices (burning, opening batteries/CRTs). This is a first-class
-- content module, not an afterthought: informal collectors are the most exposed
-- workers in the informal e-waste chain.
--
-- Content is served per-locale (en/hi/mr) and is safe to cache offline.

CREATE TABLE IF NOT EXISTS safety_topics (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code          text NOT NULL UNIQUE,      -- e.g. 'no_open_burning'
    title         text NOT NULL,             -- canonical English title
    severity      text NOT NULL DEFAULT 'high'
                  CHECK (severity IN ('critical', 'high', 'medium', 'info')),
    sort_order    integer NOT NULL DEFAULT 0,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Localized body text for a topic.
CREATE TABLE IF NOT EXISTS safety_topic_i18n (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id     uuid NOT NULL REFERENCES safety_topics(id) ON DELETE CASCADE,
    locale       text NOT NULL CHECK (locale IN ('en', 'hi', 'mr', 'ta', 'te', 'ml', 'kn', 'bn')),
    title        text NOT NULL,
    short_text   text,                        -- one line, for low-literacy UI
    do_text      text,                        -- "do this" (safe practice)
    dont_text    text,                        -- "never do this" (hazard)
    audio_url    text,                        -- pre-recorded voice asset (Cloudinary)
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (topic_id, locale)
);

-- Pictogram/icon key resolved to an asset by the client (icon font or PNG set).
-- Kept separate so translations do not have to change when an asset changes.
CREATE TABLE IF NOT EXISTS safety_pictograms (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id      uuid NOT NULL REFERENCES safety_topics(id) ON DELETE CASCADE,
    kind          text NOT NULL CHECK (kind IN ('do', 'dont')),
    icon_key      text NOT NULL,              -- client icon identifier
    alt_text_key  text,                       -- accessibility label key
    sort_order    integer NOT NULL DEFAULT 0,
    UNIQUE (topic_id, kind, icon_key)
);

-- Which hazards a collector should be warned about given what is in the lot.
-- Ties the safety module to the taxonomy so warnings are contextual.
CREATE TABLE IF NOT EXISTS safety_topic_category_links (
    topic_id              uuid NOT NULL REFERENCES safety_topics(id) ON DELETE CASCADE,
    material_category_id  uuid NOT NULL REFERENCES material_categories(id) ON DELETE CASCADE,
    PRIMARY KEY (topic_id, material_category_id)
);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_safety_topics_updated_at ON safety_topics;
CREATE TRIGGER trg_safety_topics_updated_at
    BEFORE UPDATE ON safety_topics
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_safety_topic_i18n_updated_at ON safety_topic_i18n;
CREATE TRIGGER trg_safety_topic_i18n_updated_at
    BEFORE UPDATE ON safety_topic_i18n
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
