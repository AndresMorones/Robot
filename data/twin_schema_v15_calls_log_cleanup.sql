-- HR Twin: calls_log cleanup — strip load-grain columns now owned by the bookings table.
--
-- Run BEFORE twin_schema_v15_bookings.sql so the schema split is atomic from the
-- writer's perspective: post-call writes lose the load fields the same moment
-- mid-call writes start populating bookings.
--
-- HR Twin SQL editor accepts a single statement at a time — paste each block separated
-- by `-- === STATEMENT BREAK ===` as its own submission.
--
-- Final calls_log shape after this script:
--   id, created_at, call_id (UNIQUE), mc_number, carrier_name, call_outcome,
--   sentiment, case_health_score, audit_remarks, fmcsa_eligibility_failure_reason,
--   callback_phone, duration_seconds, transcript
--
-- Note: zero production rows exist, so DROP COLUMN is non-destructive.

-- Drop the multi-row Loop-pattern uniqueness constraint (call_id, booking_seq).
-- No longer meaningful once bookings live in their own table.
ALTER TABLE calls_log DROP CONSTRAINT IF EXISTS calls_log_call_booking_seq_uniq;

-- === STATEMENT BREAK ===

-- Drop the load_id index before its column.
DROP INDEX IF EXISTS idx_calls_log_load_id;

-- === STATEMENT BREAK ===

-- Drop the composite outcome+booking_seq index before its column.
DROP INDEX IF EXISTS idx_calls_log_outcome_booking;

-- === STATEMENT BREAK ===

-- Drop load-grain column: load_id moves to bookings.load_id.
ALTER TABLE calls_log DROP COLUMN IF EXISTS load_id;

-- === STATEMENT BREAK ===

-- Drop load-grain column: apply_rate moves to bookings.apply_rate.
ALTER TABLE calls_log DROP COLUMN IF EXISTS apply_rate;

-- === STATEMENT BREAK ===

-- Drop derived flag: presence of a bookings row IS the booking signal.
ALTER TABLE calls_log DROP COLUMN IF EXISTS is_booking;

-- === STATEMENT BREAK ===

-- Drop multi-row sequence column: bookings.id (BIGSERIAL) supersedes it.
ALTER TABLE calls_log DROP COLUMN IF EXISTS booking_seq;

-- === STATEMENT BREAK ===

-- Drop per-load negotiation counter: irrelevant under post-call grain.
ALTER TABLE calls_log DROP COLUMN IF EXISTS num_negotiation_rounds;

-- === STATEMENT BREAK ===

-- Promote call_id from non-unique index to UNIQUE constraint.
-- One calls_log row per call is the new invariant; bookings.call_id is the FK-style
-- pointer back to it (no formal FK because HR Twin write order isn't guaranteed).
ALTER TABLE calls_log ADD CONSTRAINT calls_log_call_id_uniq UNIQUE (call_id);
