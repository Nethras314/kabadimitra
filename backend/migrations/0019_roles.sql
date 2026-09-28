-- 0019_roles.sql
-- Align the role model with the 9-role target: rename picker -> collector and
-- platform_admin -> super_admin, and add support / operations_admin / data_ai_admin.

UPDATE roles SET code = 'collector', name = 'Collector' WHERE code = 'picker';
UPDATE roles SET code = 'super_admin', name = 'Super Admin' WHERE code = 'platform_admin';

INSERT INTO roles (code, name, description) VALUES
    ('support',           'Support',           'User/customer support staff'),
    ('operations_admin',  'Operations Admin',  'Manages recycler verification, disputes, and operations'),
    ('data_ai_admin',     'Data/AI Admin',     'Reviews AI decisions and price observations')
ON CONFLICT (code) DO NOTHING;
