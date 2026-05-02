-- Batch 3: Mixed Quality & Edge Cases (15 calls, 8 bookings)
-- 5 booked rough-negotiation (CHS 60-78), 4 no_match (CHS 45-65),
-- 3 abandoned flagged (CHS 20-45), 3 booked perfect (CHS 95-100)
-- Date spread: Jan 1 2026 -> Apr 30 2026 (one ~every 8 days)

INSERT INTO calls_log (
  created_at, call_id, mc_number, carrier_name, callback_phone,
  fmcsa_eligibility_failure_reason, lane_origin, lane_dest,
  call_outcome, sentiment, case_health_score, audit_remarks, notes,
  duration_seconds,
  extract_input_tokens, extract_output_tokens, extract_reasoning_tokens,
  chs_input_tokens, chs_output_tokens
) VALUES
-- 1. BOOKED rough (neutral) — Jan 3
('2026-01-03 14:22:08+00', 'a1f2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d', '391022', 'Crossroads Freight Inc', 'web',
  NULL, 'Dallas, TX', 'Atlanta, GA',
  'booked', 'neutral', 72,
  'Agent opened with rate $250 below loadboard — carrier audibly frustrated, said "you''re wasting my time." Recovered after 4 rounds but tone stayed cold through booking confirmation.',
  'Booked despite rocky open',
  342, 1180, 215, 95, 520, 165),

-- 2. NO_MATCH fumble (negative) — Jan 11
('2026-01-11 09:48:33+00', 'b2a3c4d5-6f7e-4b8c-9d0e-1f2a3b4c5d6e', '805544', 'Liberty Bell Logistics', 'web',
  NULL, 'Philadelphia, PA', 'Boston, MA',
  'no_match', 'negative', 52,
  'Agent searched wrong destination state twice — carrier corrected "I said Mass, not Maine." Lost trust before search even returned results.',
  'Geo confusion',
  198, 920, 168, 60, 410, 140),

-- 3. ABANDONED flagged (negative) — Jan 19
('2026-01-19 16:05:51+00', 'c3b4d5e6-7a8f-4c9d-0e1f-2a3b4c5d6e7f', '226711', 'Granite State Transport', 'web',
  NULL, 'Manchester, NH', 'Charlotte, NC',
  'abandoned', 'negative', 28,
  'Agent quoted $400 below loadboard rate — carrier offended, said "are you serious?" and hung up mid-sentence. No recovery attempted.',
  'FLAG: hostile-disconnect',
  87, 740, 110, 30, 320, 105),

-- 4. BOOKED perfect (positive) — Jan 27
('2026-01-27 11:14:27+00', 'd4c5e6f7-8b9a-4d0e-1f2a-3b4c5d6e7f8a', '478099', 'Coastal Carriers LLC', 'web',
  NULL, 'Long Beach, CA', 'Phoenix, AZ',
  'booked', 'positive', 98,
  'Smooth — confirmed pickup window, dock hours, lumper policy, and reefer temp setpoint. Carrier thanked agent twice and asked to be called for return lanes.',
  'Repeat-candidate carrier',
  287, 1240, 198, 110, 540, 175),

-- 5. BOOKED rough (negative) — Feb 4
('2026-02-04 13:39:14+00', 'e5d6f7a8-9c0b-4e1f-2a3b-4c5d6e7f8a9b', '663388', 'Heartwood Hauling', 'web',
  NULL, 'Nashville, TN', 'Houston, TX',
  'booked', 'negative', 65,
  'Carrier asked for dispatcher 3 times — agent kept pitching new lanes instead of escalating. Booked the load but driver complained about "robot won''t listen."',
  'Booked but complaint risk',
  398, 1320, 235, 130, 580, 190),

-- 6. NO_MATCH fumble (negative) — Feb 12
('2026-02-12 10:27:42+00', 'f6e7a8b9-0d1c-4f2a-3b4c-5d6e7f8a9b0c', '540122', 'Mesa Verde Trucking', 'web',
  NULL, 'Albuquerque, NM', 'Salt Lake City, UT',
  'no_match', 'negative', 48,
  'Agent looped on "what''s your equipment type" 3 times after carrier already answered "53 dry van." Carrier asked for human; call ended without search.',
  'Loop bug',
  142, 860, 155, 70, 380, 130),

-- 7. ABANDONED flagged (negative) — Feb 20
('2026-02-20 15:51:09+00', 'a7f8b9c0-1e2d-4a3b-4c5d-6e7f8a9b0c1d', '187655', 'Anchor Freight Services', 'web',
  NULL, 'Jacksonville, FL', 'Memphis, TN',
  'abandoned', 'negative', 22,
  'Agent failed to acknowledge driver''s prior 2 bookings on file — came across as fully scripted. Carrier said "you don''t know me at all" and disconnected.',
  'FLAG: relationship damage',
  104, 780, 125, 45, 340, 115),

-- 8. BOOKED rough (neutral) — Feb 28
('2026-02-28 08:33:55+00', 'b8a9c0d1-2f3e-4b4c-5d6e-7f8a9b0c1d2e', '902366', 'Compass Carrier Co', 'web',
  NULL, 'Seattle, WA', 'Denver, CO',
  'booked', 'neutral', 68,
  'Negotiation went 5 rounds — agent never proposed a counter alternative, just said "no" to each carrier offer. Booked at floor but carrier said "this took forever."',
  'Slow close, no creativity',
  421, 1280, 220, 105, 560, 180),

-- 9. BOOKED perfect (positive) — Mar 8
('2026-03-08 12:08:21+00', 'c9b0d1e2-3a4f-4c5d-6e7f-8a9b0c1d2e3f', '311088', 'Brightline Express', 'web',
  NULL, 'Chicago, IL', 'Minneapolis, MN',
  'booked', 'positive', 100,
  'Textbook call — verified MC, matched lane on first search, agreed at original rate, confirmed pickup time and special instructions. Carrier said "easiest broker I''ve worked with."',
  'Reference-quality call',
  246, 1190, 185, 80, 510, 160),

-- 10. NO_MATCH fumble (negative) — Mar 16
('2026-03-16 14:46:17+00', 'd0c1e2f3-4b5a-4d6e-7f8a-9b0c1d2e3f4a', '729044', 'Hinterland Transport LLC', 'web',
  NULL, 'Omaha, NE', 'Indianapolis, IN',
  'no_match', 'neutral', 58,
  'Search returned 4 matching loads but agent only pitched the first one; when carrier passed, agent said "no more options" instead of offering the others. Carrier hung up confused.',
  'Surfacing failure',
  176, 890, 162, 75, 395, 138),

-- 11. ABANDONED flagged (negative) — Mar 24
('2026-03-24 17:19:48+00', 'e1d2f3a4-5c6b-4e7f-8a9b-0c1d2e3f4a5b', '156088', 'Pinewood Logistics', 'web',
  NULL, 'Portland, OR', 'Las Vegas, NV',
  'abandoned', 'negative', 35,
  'Agent confirmed a booking before getting pickup time — carrier said "wait, when does it load?" Agent answered with the dropoff date. Carrier said "I''m out" and hung up.',
  'FLAG: incomplete handoff',
  118, 810, 140, 55, 360, 122),

-- 12. BOOKED rough (neutral) — Apr 1
('2026-04-01 11:02:36+00', 'f2e3a4b5-6d7c-4f8a-9b0c-1d2e3f4a5b6c', '833277', 'Riverside Express Trucking', 'web',
  NULL, 'St. Louis, MO', 'Cleveland, OH',
  'booked', 'neutral', 75,
  'Agent quoted same rate 3 times despite carrier saying "fuel surcharge changed last week." Eventually matched the ask but never explained the math. Booking landed flat.',
  'Math-blind negotiation',
  315, 1230, 208, 100, 535, 172),

-- 13. NO_MATCH fumble (negative) — Apr 9
('2026-04-09 09:24:53+00', 'a3f4b5c6-7e8d-4a9b-0c1d-2e3f4a5b6c7d', '270955', 'Summit Freight Group', 'web',
  NULL, 'Detroit, MI', 'Pittsburgh, PA',
  'no_match', 'negative', 51,
  'Carrier mentioned reefer twice, agent searched dry van inventory only. When asked about reefer, agent said "let me check" then ended the search without re-running.',
  'Equipment-filter miss',
  211, 940, 175, 85, 425, 148),

-- 14. BOOKED perfect (positive) — Apr 17
('2026-04-17 15:37:12+00', 'b4a5c6d7-8f9e-4b0c-1d2e-3f4a5b6c7d8e', '415833', 'Bluebird Carriers Inc', 'web',
  NULL, 'Kansas City, MO', 'Salt Lake City, UT',
  'booked', 'positive', 96,
  'Carrier accepted second-round counter, agent confirmed dock hours, hazmat status, and provided dispatcher number unprompted. Carrier said "send me your card."',
  'Strong rapport',
  268, 1210, 192, 90, 525, 168),

-- 15. BOOKED rough (negative) — Apr 25
('2026-04-25 13:55:39+00', 'c5b6d7e8-9a0f-4c1d-2e3f-4a5b6c7d8e9f', '692100', 'Steel City Hauling', 'web',
  NULL, 'Pittsburgh, PA', 'Charlotte, NC',
  'booked', 'negative', 60,
  'Agent interrupted carrier 4 times during rate discussion — carrier said "let me finish a sentence." Booked at apply rate but carrier muttered "never again" before disconnect.',
  'Booked but burned bridge',
  376, 1290, 225, 115, 565, 185);

-- === STATEMENT BREAK ===

INSERT INTO bookings (created_at, call_id, mc_number, load_id, apply_rate) VALUES
-- Rough-negotiation booked (5): apply_rate 90-100% of typical
('2026-01-03 14:28:14+00', 'a1f2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d', '391022', 'LOAD-0007', 1850.00),
('2026-02-04 13:46:02+00', 'e5d6f7a8-9c0b-4e1f-2a3b-4c5d6e7f8a9b', '663388', 'LOAD-0014', 2120.00),
('2026-02-28 08:41:18+00', 'b8a9c0d1-2f3e-4b4c-5d6e-7f8a9b0c1d2e', '902366', 'LOAD-0022', 2475.00),
('2026-04-01 11:09:47+00', 'f2e3a4b5-6d7c-4f8a-9b0c-1d2e3f4a5b6c', '833277', 'LOAD-0031', 1690.00),
('2026-04-25 14:03:21+00', 'c5b6d7e8-9a0f-4c1d-2e3f-4a5b6c7d8e9f', '692100', 'LOAD-0044', 1925.00),
-- Perfect booked (3): apply_rate 100-110% of typical
('2026-01-27 11:20:09+00', 'd4c5e6f7-8b9a-4d0e-1f2a-3b4c5d6e7f8a', '478099', 'LOAD-0011', 2380.00),
('2026-03-08 12:13:44+00', 'c9b0d1e2-3a4f-4c5d-6e7f-8a9b0c1d2e3f', '311088', 'LOAD-0026', 1675.00),
('2026-04-17 15:43:55+00', 'b4a5c6d7-8f9e-4b0c-1d2e-3f4a5b6c7d8e', '415833', 'LOAD-0038', 2890.00);
