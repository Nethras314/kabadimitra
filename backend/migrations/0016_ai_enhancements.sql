-- 0016_ai_enhancements.sql
-- Add alternative predictions and denormalized model metadata to ai_decisions so
-- each decision is a self-contained audit record (model, version, prediction,
-- confidence, alternatives). Additive only — preserves existing data.

ALTER TABLE ai_decisions ADD COLUMN IF NOT EXISTS provider text;
ALTER TABLE ai_decisions ADD COLUMN IF NOT EXISTS model_name text;
ALTER TABLE ai_decisions ADD COLUMN IF NOT EXISTS model_version text;
ALTER TABLE ai_decisions ADD COLUMN IF NOT EXISTS alternatives jsonb;
