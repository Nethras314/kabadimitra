-- 0014_seed_roles.sql
-- Seed the six primary roles. Idempotent.

INSERT INTO roles (code, name, description) VALUES
    ('picker',         'Picker / Waste Collector', 'Informal collector who captures material on the ground'),
    ('kabadiwala',     'Kabadiwala',               'Local scrap dealer / collection point operator'),
    ('aggregator',     'Aggregator',               'Consolidates material from multiple collectors'),
    ('recycler',       'Recycler',                 'Authorized recycling facility'),
    ('dismantler',     'Dismantler',               'Breaks down equipment into recovered material'),
    ('platform_admin', 'Platform Admin',           'System administrator')
ON CONFLICT (code) DO NOTHING;
