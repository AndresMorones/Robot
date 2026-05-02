-- Batch 1 — happy path (15 calls, 10 bookings)
-- Generated for dashboard demo — covers 2026-01-01 to 2026-04-30
-- 10 booked + 5 no_match; sentiment ~10 pos / 4 neu / 1 neg; CHS high

-- === STATEMENT BREAK ===
INSERT INTO calls_log (created_at, call_id, mc_number, carrier_name, callback_phone, lane_origin, lane_dest, call_outcome, sentiment, case_health_score, audit_remarks, notes, duration_seconds, extract_input_tokens, extract_output_tokens, extract_reasoning_tokens, chs_input_tokens, chs_output_tokens) VALUES
('2026-01-06 14:23:11+00', 'e4b81234-aa11-4f2a-9c3d-1234567890ab', '559010', 'Lonestar Freight LLC', 'web', 'Dallas, TX', 'Atlanta, GA', 'booked', 'positive', 94, 'Smooth booking after one counter — confirmed dock hours and PU appointment.', 'Prefers dry van, no-touch only', 312, 1280, 195, 60, 445, 125),
('2026-01-14 19:47:33+00', 'a7c93d12-bb22-4e1b-8d4c-2345678901bc', '781234', 'Pacific Coast Carriers', 'web', 'Los Angeles, CA', 'Phoenix, AZ', 'booked', 'positive', 91, 'Carrier accepted first offer at posted rate — clean handoff to dispatch.', '', 248, 1140, 165, 40, 410, 105),
('2026-01-22 16:12:08+00', 'b8d04e23-cc33-4a2c-9e5d-3456789012cd', '612099', 'Midwest Express Trucking', 'web', 'Chicago, IL', 'Indianapolis, IN', 'booked', 'positive', 89, 'Booked at $750 after carrier asked for $50 more — accepted same round.', 'Reefer 34F preferred', 295, 1320, 210, 75, 460, 140),
('2026-01-29 21:34:55+00', 'c9e15f34-dd44-4b3d-af6e-4567890123de', '488355', 'Atlantic Logistics Inc', 'web', 'Newark, NJ', 'Boston, MA', 'no_match', 'neutral', 78, 'No loads in lane today — carrier polite, asked us to call back tomorrow.', 'Wants NJ-MA short hauls', 168, 920, 125, 25, 340, 90),
('2026-02-05 15:08:42+00', 'd0f26045-ee55-4c4e-b07f-5678901234ef', '921007', 'Southern Cross Transport', 'web', 'Houston, TX', 'Memphis, TN', 'booked', 'positive', 96, 'One-shot accept at $1,650 — carrier praised quick load match.', '', 224, 1060, 155, 35, 395, 100),
('2026-02-13 18:55:19+00', 'e1037156-ff66-4d5f-c180-6789012345f0', '745210', 'Mountain West Hauling Co', 'web', 'Salt Lake City, UT', 'Sacramento, CA', 'booked', 'positive', 88, 'Booked after two counters — settled at $2,150 within target band.', 'Owner-operator, single truck', 358, 1410, 235, 95, 485, 155),
('2026-02-21 13:29:04+00', 'f2148267-aa77-4e60-d291-78901234560a', '333892', 'Great Lakes Freight', 'web', 'Detroit, MI', 'Cleveland, OH', 'no_match', 'positive', 82, 'No matching load in DET-CLE corridor — carrier appreciated honest answer.', 'Short haul specialist', 142, 880, 115, 20, 325, 85),
('2026-02-27 20:16:37+00', '03259378-bb88-4f71-e3a2-89012345671b', '156477', 'Delta Trucking Services', 'web', 'Atlanta, GA', 'Tampa, FL', 'booked', 'neutral', 85, 'Booked at $1,425 after one counter — carrier was matter-of-fact, no friction.', '', 271, 1195, 175, 55, 425, 115),
('2026-03-04 17:43:22+00', '14360489-cc99-4082-f4b3-90123456782c', '891055', 'Sunrise Carriers LLC', 'web', 'Phoenix, AZ', 'Long Beach, CA', 'booked', 'positive', 93, 'Quick booking — accepted posted rate, asked about recurring lane volume.', 'Interested in dedicated runs', 218, 1085, 160, 45, 405, 110),
('2026-03-12 14:01:58+00', '2547159a-dd00-4193-058c-a1234567893d', '244031', 'Eagle Eye Logistics', 'web', 'Kansas City, MO', 'Minneapolis, MN', 'no_match', 'neutral', 75, 'Lane requested not in tonight''s board — carrier patient, will retry.', '', 156, 935, 130, 30, 350, 92),
('2026-03-20 22:38:11+00', '365826ab-ee11-42a4-169d-b2345678904e', '670918', 'Buckeye Transport Co', 'web', 'Cleveland, OH', 'Pittsburgh, PA', 'booked', 'positive', 90, 'Booked at $625 — carrier mentioned regional preference, logged for future.', 'PA/OH regional only', 264, 1170, 180, 50, 430, 118),
('2026-03-28 16:24:46+00', '47693bbc-ff22-43b5-27ae-c3456789015f', '405287', 'Plains Express', 'web', 'Dallas, TX', 'Joliet, IL', 'booked', 'positive', 95, 'Booked at $2,275 after light counter — carrier confirmed driver ready.', '', 341, 1385, 225, 85, 470, 148),
('2026-04-04 13:52:29+00', '587a4ccd-aa33-44c6-38bf-d4567890126a', '583311', 'Cascade Freight Lines', 'web', 'Sacramento, CA', 'Salt Lake City, UT', 'no_match', 'negative', 71, 'Carrier frustrated about repeated empty searches — handled professionally, ended cleanly.', 'Has called twice this week', 198, 985, 145, 40, 365, 98),
('2026-04-15 19:18:53+00', '698b5dde-bb44-45d7-49c0-e5678901237b', '119804', 'Ironclad Transport', 'web', 'Charlotte, NC', 'Atlanta, GA', 'booked', 'positive', 92, 'One-counter book at $895 — carrier asked smart questions about delivery window.', '', 287, 1245, 188, 65, 440, 122),
('2026-04-26 15:46:07+00', '79c06eef-cc55-46e8-5ad1-f6789012348c', '776622', 'Heartland Carriers', 'web', 'Indianapolis, IN', 'Detroit, MI', 'no_match', 'neutral', 80, 'No loads matched IN-MI tonight — carrier asked about morning availability.', 'Will call back AM', 174, 950, 135, 30, 355, 95)
;

-- === STATEMENT BREAK ===
INSERT INTO bookings (created_at, call_id, mc_number, load_id, apply_rate) VALUES
('2026-01-06 14:27:45+00', 'e4b81234-aa11-4f2a-9c3d-1234567890ab', '559010', 'LOAD-0003', 1875.00),
('2026-01-14 19:51:12+00', 'a7c93d12-bb22-4e1b-8d4c-2345678901bc', '781234', 'LOAD-0008', 985.00),
('2026-01-22 16:16:33+00', 'b8d04e23-cc33-4a2c-9e5d-3456789012cd', '612099', 'LOAD-0012', 750.00),
('2026-02-05 15:11:58+00', 'd0f26045-ee55-4c4e-b07f-5678901234ef', '921007', 'LOAD-0017', 1650.00),
('2026-02-13 18:59:44+00', 'e1037156-ff66-4d5f-c180-6789012345f0', '745210', 'LOAD-0021', 2150.00),
('2026-02-27 20:20:09+00', '03259378-bb88-4f71-e3a2-89012345671b', '156477', 'LOAD-0026', 1425.00),
('2026-03-04 17:46:51+00', '14360489-cc99-4082-f4b3-90123456782c', '891055', 'LOAD-0030', 875.00),
('2026-03-20 22:42:28+00', '365826ab-ee11-42a4-169d-b2345678904e', '670918', 'LOAD-0034', 625.00),
('2026-03-28 16:28:17+00', '47693bbc-ff22-43b5-27ae-c3456789015f', '405287', 'LOAD-0040', 2275.00),
('2026-04-15 19:22:36+00', '698b5dde-bb44-45d7-49c0-e5678901237b', '119804', 'LOAD-0045', 895.00)
;
