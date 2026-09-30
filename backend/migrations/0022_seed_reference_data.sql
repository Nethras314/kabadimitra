-- 0022_seed_reference_data.sql
-- Demonstration dataset: authorized recyclers and price observations.
--
-- IMPORTANT / HONESTY NOTE
-- The organizations below are FICTIONAL reference data used to make the price
-- board, trends, matching and estimates demonstrable. They are NOT real
-- registered recyclers and must be replaced with verified records before any
-- field use. Authorization numbers here are placeholders.
-- Prices are realistic ORDER-OF-MAGNITUDE values for Maharashtra scrap markets
-- in 2026; they are seed references, not live market quotes. Every observation
-- is stored with full provenance (source + verification status) so the
-- distinction is never lost.
--
-- Replace with real data via: recycler onboarding API (admin) + price
-- observation ingestion, then delete this file's rows.

-- =============================================================================
-- Reference organizations / recyclers (Maharashtra)
-- =============================================================================
INSERT INTO organizations (id, name, organization_type, status, city, state, postal_code, contact_phone)
VALUES
    ('80000000-0000-0000-0000-000000000001', 'Pune Green Metal Recycling', 'recycler', 'active', 'Pune', 'Maharashtra', '411001', '+9198000000001'),
    ('80000000-0000-0000-0000-000000000002', 'Nagpur E-Waste Solutions', 'recycler', 'active', 'Nagpur', 'Maharashtra', '440001', '+9198000000002'),
    ('80000000-0000-0000-0000-000000000003', 'Nashik Tech Scrap Pvt Ltd', 'recycler', 'active', 'Nashik', 'Maharashtra', '422001', '+9198000000003'),
    ('80000000-0000-0000-0000-000000000004', 'Aurangabad Circular Metals', 'recycler', 'active', 'Aurangabad', 'Maharashtra', '431001', '+9198000000004'),
    ('80000000-0000-0000-0000-000000000005', 'Kolhapur Clean Scrap', 'recycler', 'active', 'Kolhapur', 'Maharashtra', '416001', '+9198000000005'),
    -- A suspended recycler: must be excluded from matching.
    ('80000000-0000-0000-0000-000000000006', 'Unverified Scrap Traders (reference)', 'recycler', 'active', 'Pune', 'Maharashtra', '411002', '+9198000000006')
ON CONFLICT (id) DO NOTHING;

INSERT INTO recycler_organizations (id, organization_id, gstin, registration_number)
VALUES
    ('81000000-0000-0000-0000-000000000001', '80000000-0000-0000-0000-000000000001', '27AAACP9999A1Z5', 'MH/PUNE/REC/2019/0001'),
    ('81000000-0000-0000-0000-000000000002', '80000000-0000-0000-0000-000000000002', '27AAACQ8888B1Z6', 'MH/NAG/REC/2020/0002'),
    ('81000000-0000-0000-0000-000000000003', '80000000-0000-0000-0000-000000000003', '27AAACR7777C1Z7', 'MH/NSK/REC/2018/0003'),
    ('81000000-0000-0000-0000-000000000004', '80000000-0000-0000-0000-000000000004', '27AAACS6666D1Z8', 'MH/AUR/REC/2021/0004'),
    ('81000000-0000-0000-0000-000000000005', '80000000-0000-0000-0000-000000000005', '27AAACT5555E1Z9', 'MH/KOL/REC/2022/0005'),
    ('81000000-0000-0000-0000-000000000006', '80000000-0000-0000-0000-000000000006', NULL, NULL)
ON CONFLICT (organization_id) DO NOTHING;

-- Facilities with real coordinates (city centres) so geospatial search works.
INSERT INTO recycler_facilities (id, recycler_organization_id, name, address_line, city, state, postal_code, location)
VALUES
    ('82000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000001', 'Pune Green Metal Recycling - Unit 1', 'MIDC Bhosari', 'Pune', 'Maharashtra', '411026', ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326)),
    ('82000000-0000-0000-0000-000000000002', '81000000-0000-0000-0000-000000000002', 'Nagpur E-Waste Solutions', 'Butibori MIDC', 'Nagpur', 'Maharashtra', '441035', ST_SetSRID(ST_MakePoint(79.0882, 21.1458), 4326)),
    ('82000000-0000-0000-0000-000000000003', '81000000-0000-0000-0000-000000000003', 'Nashik Tech Scrap', 'Ambad MIDC', 'Nashik', 'Maharashtra', '422010', ST_SetSRID(ST_MakePoint(73.8735, 20.0110), 4326)),
    ('82000000-0000-0000-0000-000000000004', '81000000-0000-0000-0000-000000000004', 'Aurangabad Circular Metals', 'Chikalthana MIDC', 'Aurangabad', 'Maharashtra', '431001', ST_SetSRID(ST_MakePoint(75.3436, 19.8762), 4326)),
    ('82000000-0000-0000-0000-000000000005', '81000000-0000-0000-0000-000000000005', 'Kolhapur Clean Scrap', 'GIDC Kupoli', 'Kolhapur', 'Maharashtra', '416005', ST_SetSRID(ST_MakePoint(74.2313, 16.7050), 4326))
ON CONFLICT (id) DO NOTHING;

-- Authorizations. The last recycler is suspended/unverified and must never
-- appear in matching results (FR-VERIF-04).
INSERT INTO recycler_authorizations (id, recycler_organization_id, authorization_number, issuing_authority, authorization_type, issue_date, expiry_date, verification_source, verification_date, status)
VALUES
    ('83000000-0000-0000-0000-000000000001', '81000000-0000-0000-0000-000000000001', 'CPCB/REF/2019/0001', 'CPCB (reference)', 'EPR recycler authorization', DATE '2019-06-01', DATE '2029-05-31', 'seed-reference', now(), 'verified'),
    ('83000000-0000-0000-0000-000000000002', '81000000-0000-0000-0000-000000000002', 'CPCB/REF/2020/0002', 'CPCB (reference)', 'EPR recycler authorization', DATE '2020-08-15', DATE '2030-08-14', 'seed-reference', now(), 'verified'),
    ('83000000-0000-0000-0000-000000000003', '81000000-0000-0000-0000-000000000003', 'CPCB/REF/2018/0003', 'CPCB (reference)', 'EPR recycler authorization', DATE '2018-03-10', DATE '2028-03-09', 'seed-reference', now(), 'verified'),
    -- Expiring soon: demonstrates the "expiring" concept and the near-deadline warning.
    ('83000000-0000-0000-0000-000000000004', '81000000-0000-0000-0000-000000000004', 'CPCB/REF/2021/0004', 'CPCB (reference)', 'EPR recycler authorization', DATE '2021-01-20', (CURRENT_DATE + INTERVAL '45 days')::date, 'seed-reference', now(), 'verified'),
    -- EXPIRED: must be excluded from matching.
    ('83000000-0000-0000-0000-000000000005', '81000000-0000-0000-0000-000000000005', 'CPCB/REF/2022/0005', 'CPCB (reference)', 'EPR recycler authorization', DATE '2022-02-01', DATE '2025-01-31', 'seed-reference', now(), 'expired'),
    -- Suspended / never authorized. Has a placeholder reference so the
    -- authorization_number NOT NULL constraint holds; status keeps it out of
    -- matching.
    ('83000000-0000-0000-0000-000000000006', '81000000-0000-0000-0000-000000000006', 'NONE/UNVERIFIED', NULL, NULL, NULL, NULL, NULL, NULL, 'suspended')
ON CONFLICT (id) DO NOTHING;

-- Material acceptance
INSERT INTO recycler_material_acceptance (recycler_organization_id, material_category_id, is_accepted)
VALUES
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', true), -- tv_monitor
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000009', true), -- pcb
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000010', true), -- cable_wire
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000011', true), -- copper
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000014', true), -- mixed_metal
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000019', true), -- lead_acid_battery
    ('81000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000020', true), -- lithium cells
    ('81000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000009', true), -- pcb
    ('81000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000010', true), -- cable_wire
    ('81000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000011', true), -- copper
    ('81000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000020', true),
    ('81000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000006', true), -- motor
    ('81000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000011', true),
    ('81000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000018', true), -- ferrite magnet
    ('81000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000009', true),
    ('81000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000001', true), -- tv_monitor
    ('81000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000021', true), -- crt glass
    ('81000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000014', true)
ON CONFLICT (recycler_organization_id, material_category_id, material_subcategory_id) DO NOTHING;

-- Service areas
INSERT INTO recycler_service_areas (recycler_organization_id, name, radius_km, center)
VALUES
    ('81000000-0000-0000-0000-000000000001', 'Pune Western', 60, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326)),
    ('81000000-0000-0000-0000-000000000002', 'Vidarbha', 80, ST_SetSRID(ST_MakePoint(79.0882, 21.1458), 4326)),
    ('81000000-0000-0000-0000-000000000003', 'Nashik', 55, ST_SetSRID(ST_MakePoint(73.8735, 20.0110), 4326)),
    ('81000000-0000-0000-0000-000000000004', 'Marathwada', 60, ST_SetSRID(ST_MakePoint(75.3436, 19.8762), 4326))
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Price observations
-- Spread over ~90 days so trends are real, not fabricated. Verified rows drive
-- the trusted average; unverified collector entries are present on purpose so
-- the provenance distinction is visible in the UI.
-- =============================================================================
INSERT INTO price_observations
    (material_category_id, grade_id, location, city, state, observed_price_per_kg, currency, buyer_type, source, weight_kg, verification_status, observed_at, notes)
VALUES
    -- PCB: rising trend ~120 -> 150 over 90 days
    ('20000000-0000-0000-0000-000000000009', '40000000-0000-0000-0000-000000000001', ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 120, 'INR', 'recycler', 'market', 50, 'verified', now() - INTERVAL '90 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000009', '40000000-0000-0000-0000-000000000001', ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 130, 'INR', 'recycler', 'market', 40, 'verified', now() - INTERVAL '60 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000009', '40000000-0000-0000-0000-000000000001', ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 140, 'INR', 'recycler', 'market', 60, 'verified', now() - INTERVAL '30 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000009', '40000000-0000-0000-0000-000000000001', ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 150, 'INR', 'recycler', 'market', 45, 'verified', now() - INTERVAL '2 days', 'Reference seed'),
    -- Unverified collector entry (lower) - shows why provenance matters
    ('20000000-0000-0000-0000-000000000009', NULL, NULL, 'Pune', 'Maharashtra', 95, 'INR', 'aggregator', 'collector_entry', 20, 'unverified', now() - INTERVAL '1 day', 'Collector reported'),

    -- Cable / wire: flat ~90
    ('20000000-0000-0000-0000-000000000010', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 88, 'INR', 'recycler', 'market', 100, 'verified', now() - INTERVAL '80 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000010', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 92, 'INR', 'recycler', 'market', 120, 'verified', now() - INTERVAL '40 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000010', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 90, 'INR', 'recycler', 'market', 80, 'verified', now() - INTERVAL '1 day', 'Reference seed'),

    -- Copper: rising 260 -> 300
    ('20000000-0000-0000-0000-000000000011', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 260, 'INR', 'recycler', 'market', 30, 'verified', now() - INTERVAL '90 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000011', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 285, 'INR', 'recycler', 'market', 25, 'verified', now() - INTERVAL '30 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000011', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 300, 'INR', 'recycler', 'market', 35, 'verified', now() - INTERVAL '1 day', 'Reference seed'),

    -- Aluminium ~165
    ('20000000-0000-0000-0000-000000000012', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 165, 'INR', 'recycler', 'market', 60, 'verified', now() - INTERVAL '30 days', 'Reference seed'),
    -- Steel ~32
    ('20000000-0000-0000-0000-000000000013', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 32, 'INR', 'recycler', 'market', 200, 'verified', now() - INTERVAL '20 days', 'Reference seed'),
    -- Mixed metal ~55
    ('20000000-0000-0000-0000-000000000014', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 55, 'INR', 'recycler', 'market', 150, 'verified', now() - INTERVAL '25 days', 'Reference seed'),
    -- Lead-acid battery ~55
    ('20000000-0000-0000-0000-000000000019', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 55, 'INR', 'recycler', 'market', 40, 'verified', now() - INTERVAL '15 days', 'Reference seed'),
    -- Lithium cells ~120
    ('20000000-0000-0000-0000-000000000020', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 120, 'INR', 'recycler', 'market', 15, 'verified', now() - INTERVAL '10 days', 'Reference seed'),
    -- CRT glass ~8
    ('20000000-0000-0000-0000-000000000021', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 8, 'INR', 'recycler', 'market', 25, 'verified', now() - INTERVAL '12 days', 'Reference seed'),
    -- Motor ~220
    ('20000000-0000-0000-0000-000000000006', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 220, 'INR', 'recycler', 'market', 20, 'verified', now() - INTERVAL '18 days', 'Reference seed'),
    -- Ferrite magnet ~75
    ('20000000-0000-0000-0000-000000000018', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 75, 'INR', 'recycler', 'market', 10, 'verified', now() - INTERVAL '22 days', 'Reference seed'),
    -- ABS plastic ~35
    ('20000000-0000-0000-0000-000000000015', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 35, 'INR', 'recycler', 'market', 80, 'verified', now() - INTERVAL '35 days', 'Reference seed'),
    -- TV / monitor whole ~450
    ('20000000-0000-0000-0000-000000000001', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 450, 'INR', 'recycler', 'market', 30, 'verified', now() - INTERVAL '28 days', 'Reference seed'),
    -- Computer / laptop ~900
    ('20000000-0000-0000-0000-000000000002', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 900, 'INR', 'recycler', 'market', 15, 'verified', now() - INTERVAL '32 days', 'Reference seed'),
    -- Mobile electronics ~3000
    ('20000000-0000-0000-0000-000000000003', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 3000, 'INR', 'recycler', 'market', 5, 'verified', now() - INTERVAL '26 days', 'Reference seed'),
    -- Lamp ~15
    ('20000000-0000-0000-0000-000000000005', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 15, 'INR', 'recycler', 'market', 20, 'verified', now() - INTERVAL '34 days', 'Reference seed'),
    -- Printer ~350
    ('20000000-0000-0000-0000-000000000004', NULL, ST_SetSRID(ST_MakePoint(73.8478, 18.5204), 4326), 'Pune', 'Maharashtra', 350, 'INR', 'recycler', 'market', 12, 'verified', now() - INTERVAL '29 days', 'Reference seed'),

    -- Nagpur (different city) for location-specific board
    ('20000000-0000-0000-0000-000000000011', NULL, ST_SetSRID(ST_MakePoint(79.0882, 21.1458), 4326), 'Nagpur', 'Maharashtra', 295, 'INR', 'recycler', 'market', 25, 'verified', now() - INTERVAL '3 days', 'Reference seed'),
    ('20000000-0000-0000-0000-000000000010', NULL, ST_SetSRID(ST_MakePoint(79.0882, 21.1458), 4326), 'Nagpur', 'Maharashtra', 94, 'INR', 'recycler', 'market', 90, 'verified', now() - INTERVAL '4 days', 'Reference seed')
ON CONFLICT DO NOTHING;
