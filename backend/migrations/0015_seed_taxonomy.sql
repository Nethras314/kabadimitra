-- 0015_seed_taxonomy.sql
-- Initial reference taxonomy: collector-facing categories, backend material
-- categories/subcategories, grades, conditions, hazards, and the mapping between
-- them. This is reference/demo data (not exhaustive) and is idempotent.

-- =============================================================================
-- Collector-facing categories (simple, 14 labels)
-- =============================================================================
INSERT INTO collector_categories (id, code, name, sort_order) VALUES
    ('10000000-0000-0000-0000-000000000001', 'tv_monitor',        'TV / Monitor',           1),
    ('10000000-0000-0000-0000-000000000002', 'computer_laptop',   'Computer / Laptop',      2),
    ('10000000-0000-0000-0000-000000000003', 'mobile_electronics','Mobile / Electronics',   3),
    ('10000000-0000-0000-0000-000000000004', 'pcb_board',         'PCB / Board',            4),
    ('10000000-0000-0000-0000-000000000005', 'cable_wire',        'Cable / Wire',           5),
    ('10000000-0000-0000-0000-000000000006', 'battery',           'Battery',                6),
    ('10000000-0000-0000-0000-000000000007', 'motor',             'Motor',                  7),
    ('10000000-0000-0000-0000-000000000008', 'magnet',            'Magnet',                 8),
    ('10000000-0000-0000-0000-000000000009', 'plastic',           'Plastic',                9),
    ('10000000-0000-0000-0000-000000000010', 'metal',             'Metal',                 10),
    ('10000000-0000-0000-0000-000000000011', 'lamp',              'Lamp',                  11),
    ('10000000-0000-0000-0000-000000000012', 'printer',           'Printer',               12),
    ('10000000-0000-0000-0000-000000000013', 'other',             'Other',                 13),
    ('10000000-0000-0000-0000-000000000014', 'dont_know',         'I don''t know',         14)
ON CONFLICT (code) DO NOTHING;

-- =============================================================================
-- Backend material categories (detailed; equipment vs recovered_material)
-- =============================================================================
INSERT INTO material_categories (id, code, name, kind, sort_order) VALUES
    -- Equipment
    ('20000000-0000-0000-0000-000000000001', 'tv_monitor',           'TV / Monitor',            'equipment',          1),
    ('20000000-0000-0000-0000-000000000002', 'computer_laptop',      'Computer / Laptop',       'equipment',          2),
    ('20000000-0000-0000-0000-000000000003', 'mobile_electronics',   'Mobile / Electronics',    'equipment',          3),
    ('20000000-0000-0000-0000-000000000004', 'printer',              'Printer',                 'equipment',          4),
    ('20000000-0000-0000-0000-000000000005', 'lamp',                 'Lamp',                    'equipment',          5),
    ('20000000-0000-0000-0000-000000000006', 'motor_equipment',      'Motor (whole)',           'equipment',          6),
    ('20000000-0000-0000-0000-000000000007', 'battery_equipment',    'Battery (whole)',         'equipment',          7),
    ('20000000-0000-0000-0000-000000000008', 'other_equipment',      'Other equipment',         'equipment',          8),
    -- Recovered material
    ('20000000-0000-0000-0000-000000000009', 'pcb',                  'PCB / Circuit Board',     'recovered_material',  9),
    ('20000000-0000-0000-0000-000000000010', 'cable_wire',           'Cable / Wire',            'recovered_material', 10),
    ('20000000-0000-0000-0000-000000000011', 'copper',               'Copper',                  'recovered_material', 11),
    ('20000000-0000-0000-0000-000000000012', 'aluminium',            'Aluminium',               'recovered_material', 12),
    ('20000000-0000-0000-0000-000000000013', 'steel',                'Steel / Iron',            'recovered_material', 13),
    ('20000000-0000-0000-0000-000000000014', 'mixed_metal',          'Mixed Metal',             'recovered_material', 14),
    ('20000000-0000-0000-0000-000000000015', 'plastic_abs',          'ABS Plastic',             'recovered_material', 15),
    ('20000000-0000-0000-0000-000000000016', 'plastic_mixed',        'Mixed Plastic',           'recovered_material', 16),
    ('20000000-0000-0000-0000-000000000017', 'copper_winding',       'Copper Winding',          'recovered_material', 17),
    ('20000000-0000-0000-0000-000000000018', 'ferrite_magnet',       'Ferrite Magnet',          'recovered_material', 18),
    ('20000000-0000-0000-0000-000000000019', 'lead_acid_battery',    'Lead-Acid Battery',       'recovered_material', 19),
    ('20000000-0000-0000-0000-000000000020', 'lithium_battery_cells','Lithium Battery Cells',   'recovered_material', 20),
    ('20000000-0000-0000-0000-000000000021', 'glass_crt',            'CRT Glass',               'recovered_material', 21),
    ('20000000-0000-0000-0000-000000000022', 'e_plastic',            'E-waste Plastic (FR)',    'recovered_material', 22)
ON CONFLICT (code) DO NOTHING;

-- =============================================================================
-- Material subcategories (representative subset)
-- =============================================================================
INSERT INTO material_subcategories (id, material_category_id, code, name, sort_order) VALUES
    ('30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'crt',      'CRT',      1),
    ('30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'lcd_led',  'LCD / LED', 2),
    ('30000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000002', 'desktop',  'Desktop',   1),
    ('30000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000002', 'laptop',   'Laptop',    2),
    ('30000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000003', 'smartphone',   'Smartphone',    1),
    ('30000000-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000003', 'feature_phone','Feature phone', 2),
    ('30000000-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000009', 'high_grade', 'High grade',  1),
    ('30000000-0000-0000-0000-000000000008', '20000000-0000-0000-0000-000000000009', 'mid_grade',  'Mid grade',   2),
    ('30000000-0000-0000-0000-000000000009', '20000000-0000-0000-0000-000000000009', 'low_grade',  'Low grade',   3),
    ('30000000-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000010', 'copper_wire',    'Copper wire',    1),
    ('30000000-0000-0000-0000-000000000011', '20000000-0000-0000-0000-000000000010', 'aluminium_wire', 'Aluminium wire', 2),
    ('30000000-0000-0000-0000-000000000012', '20000000-0000-0000-0000-000000000010', 'mixed_wire',     'Mixed wire',     3),
    ('30000000-0000-0000-0000-000000000013', '20000000-0000-0000-0000-000000000011', 'bright_copper', 'Bright copper', 1),
    ('30000000-0000-0000-0000-000000000014', '20000000-0000-0000-0000-000000000011', 'burnt_copper',  'Burnt copper',  2),
    ('30000000-0000-0000-0000-000000000015', '20000000-0000-0000-0000-000000000015', 'abs_white',  'ABS (white)',   1),
    ('30000000-0000-0000-0000-000000000016', '20000000-0000-0000-0000-000000000015', 'abs_colored','ABS (colored)', 2),
    ('30000000-0000-0000-0000-000000000017', '20000000-0000-0000-0000-000000000017', 'motor_winding','Motor winding', 1)
ON CONFLICT (material_category_id, code) DO NOTHING;

-- =============================================================================
-- Material grades, conditions, hazards
-- =============================================================================
INSERT INTO material_grades (id, code, name, description, sort_order) VALUES
    ('40000000-0000-0000-0000-000000000001', 'grade_a', 'A',     'High purity / quality',        1),
    ('40000000-0000-0000-0000-000000000002', 'grade_b', 'B',     'Standard quality',             2),
    ('40000000-0000-0000-0000-000000000003', 'grade_c', 'C',     'Lower quality',                3),
    ('40000000-0000-0000-0000-000000000004', 'mixed',   'Mixed', 'Mixed grades',                 4),
    ('40000000-0000-0000-0000-000000000005', 'low',     'Low',   'Low / contaminated',            5)
ON CONFLICT (code) DO NOTHING;

INSERT INTO material_conditions (id, code, name, sort_order) VALUES
    ('50000000-0000-0000-0000-000000000001', 'new',     'New',     1),
    ('50000000-0000-0000-0000-000000000002', 'used',    'Used',    2),
    ('50000000-0000-0000-0000-000000000003', 'damaged', 'Damaged', 3),
    ('50000000-0000-0000-0000-000000000004', 'mixed',   'Mixed',   4),
    ('50000000-0000-0000-0000-000000000005', 'unknown', 'Unknown', 5)
ON CONFLICT (code) DO NOTHING;

INSERT INTO material_hazards (id, code, name, description) VALUES
    ('60000000-0000-0000-0000-000000000001', 'lithium_battery',  'Contains lithium battery', 'Risk of thermal runaway'),
    ('60000000-0000-0000-0000-000000000002', 'crt_lead',         'CRT leaded glass',        'Leaded glass in cathode-ray tubes'),
    ('60000000-0000-0000-0000-000000000003', 'mercury',          'Contains mercury',        'Mercury in lamps / switches'),
    ('60000000-0000-0000-0000-000000000004', 'lead_acid',        'Lead-acid electrolyte',   'Sulphuric acid / lead'),
    ('60000000-0000-0000-0000-000000000005', 'flame_retardant',  'Flame-retardant plastics','Brominated flame retardants'),
    ('60000000-0000-0000-0000-000000000006', 'capacitor',        'Contains capacitors',     'May hold residual charge')
ON CONFLICT (code) DO NOTHING;

INSERT INTO material_hazard_links (material_category_id, material_hazard_id) VALUES
    ('20000000-0000-0000-0000-000000000019', '60000000-0000-0000-0000-000000000004'), -- lead_acid_battery -> lead_acid
    ('20000000-0000-0000-0000-000000000020', '60000000-0000-0000-0000-000000000001'), -- lithium cells -> lithium
    ('20000000-0000-0000-0000-000000000021', '60000000-0000-0000-0000-000000000002'), -- CRT glass -> leaded glass
    ('20000000-0000-0000-0000-000000000005', '60000000-0000-0000-0000-000000000003'), -- lamp -> mercury
    ('20000000-0000-0000-0000-000000000022', '60000000-0000-0000-0000-000000000005'), -- e_plastic -> FR
    ('20000000-0000-0000-0000-000000000009', '60000000-0000-0000-0000-000000000006')  -- pcb -> capacitor
ON CONFLICT (material_category_id, material_hazard_id) DO NOTHING;

-- =============================================================================
-- Collector category -> backend category mapping
-- =============================================================================
INSERT INTO collector_category_mappings (collector_category_id, material_category_id) VALUES
    ('10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001'), -- tv_monitor
    ('10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000002'), -- computer_laptop
    ('10000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000003'), -- mobile_electronics
    ('10000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000009'), -- pcb_board -> pcb
    ('10000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000010'), -- cable_wire
    ('10000000-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000019'), -- battery -> lead-acid
    ('10000000-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000020'), -- battery -> lithium cells
    ('10000000-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000006'), -- motor -> motor_equipment
    ('10000000-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000017'), -- motor -> copper_winding
    ('10000000-0000-0000-0000-000000000008', '20000000-0000-0000-0000-000000000018'), -- magnet -> ferrite_magnet
    ('10000000-0000-0000-0000-000000000009', '20000000-0000-0000-0000-000000000015'), -- plastic -> abs
    ('10000000-0000-0000-0000-000000000009', '20000000-0000-0000-0000-000000000016'), -- plastic -> mixed
    ('10000000-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000011'), -- metal -> copper
    ('10000000-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000012'), -- metal -> aluminium
    ('10000000-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000013'), -- metal -> steel
    ('10000000-0000-0000-0000-000000000010', '20000000-0000-0000-0000-000000000014'), -- metal -> mixed_metal
    ('10000000-0000-0000-0000-000000000011', '20000000-0000-0000-0000-000000000005'), -- lamp
    ('10000000-0000-0000-0000-000000000012', '20000000-0000-0000-0000-000000000004'), -- printer
    ('10000000-0000-0000-0000-000000000013', '20000000-0000-0000-0000-000000000008')  -- other -> other_equipment
ON CONFLICT (collector_category_id, material_category_id, material_subcategory_id) DO NOTHING;

-- =============================================================================
-- Hindi translations for collector-facing categories (demonstrates i18n).
-- Remaining locales (mr, ta, te, ml, kn, bn) are Phase 7 content work.
-- =============================================================================
INSERT INTO translations (entity_type, entity_id, field, locale, value) VALUES
    ('collector_category', '10000000-0000-0000-0000-000000000001', 'name', 'hi', 'टीवी / मॉनिटर'),
    ('collector_category', '10000000-0000-0000-0000-000000000002', 'name', 'hi', 'कंप्यूटर / लैपटॉप'),
    ('collector_category', '10000000-0000-0000-0000-000000000003', 'name', 'hi', 'मोबाइल / इलेक्ट्रॉनिक्स'),
    ('collector_category', '10000000-0000-0000-0000-000000000004', 'name', 'hi', 'पीसीबी / बोर्ड'),
    ('collector_category', '10000000-0000-0000-0000-000000000005', 'name', 'hi', 'केबल / तार'),
    ('collector_category', '10000000-0000-0000-0000-000000000006', 'name', 'hi', 'बैटरी'),
    ('collector_category', '10000000-0000-0000-0000-000000000007', 'name', 'hi', 'मोटर'),
    ('collector_category', '10000000-0000-0000-0000-000000000008', 'name', 'hi', 'चुंबक'),
    ('collector_category', '10000000-0000-0000-0000-000000000009', 'name', 'hi', 'प्लास्टिक'),
    ('collector_category', '10000000-0000-0000-0000-000000000010', 'name', 'hi', 'धातु'),
    ('collector_category', '10000000-0000-0000-0000-000000000011', 'name', 'hi', 'लैंप'),
    ('collector_category', '10000000-0000-0000-0000-000000000012', 'name', 'hi', 'प्रिंटर'),
    ('collector_category', '10000000-0000-0000-0000-000000000013', 'name', 'hi', 'अन्य'),
    ('collector_category', '10000000-0000-0000-0000-000000000014', 'name', 'hi', 'मुझे नहीं पता')
ON CONFLICT (entity_type, entity_id, field, locale) DO NOTHING;
