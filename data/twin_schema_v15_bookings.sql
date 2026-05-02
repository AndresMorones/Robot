-- HR Twin: bookings table — 1 row per booking, written mid-call by HR `book_load` tool
-- via the Write-to-Twin component. Companion table to calls_log (post-call grain).
--
-- Run AFTER twin_schema_v15_calls_log_cleanup.sql.
-- HR Twin SQL editor accepts a single statement at a time — paste each block separated
-- by `-- === STATEMENT BREAK ===` as its own submission.
--
-- Idempotency: UNIQUE (call_id, load_id) protects against HR webhook retries firing
-- the same booking twice within a single call. Cloudflare WAF rejects CHECK with
-- IN-lists and complex JSONB ops, so we keep DDL minimal — no constraints beyond
-- PK + UNIQUE + NOT NULL, no JSONB.

CREATE TABLE bookings (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  call_id TEXT NOT NULL,
  mc_number TEXT NOT NULL,
  load_id TEXT NOT NULL,
  apply_rate DOUBLE PRECISION NOT NULL
);

-- === STATEMENT BREAK ===

-- Idempotency guard: a single (call_id, load_id) pair can only be booked once.
-- HR Write-to-Twin retries on transient failures will collide on this constraint.
ALTER TABLE bookings ADD CONSTRAINT bookings_call_load_uniq UNIQUE (call_id, load_id);

-- === STATEMENT BREAK ===

-- Dashboard time-window queries (e.g. "bookings last 24h") sort by created_at DESC.
CREATE INDEX idx_bookings_created_at ON bookings (created_at DESC);

-- === STATEMENT BREAK ===

-- JOIN bookings → calls_log on call_id for funnel/economics dashboards.
CREATE INDEX idx_bookings_call_id ON bookings (call_id);

-- === STATEMENT BREAK ===

-- Carrier lookup: "show all bookings for MC 123456".
CREATE INDEX idx_bookings_mc_number ON bookings (mc_number);

-- === STATEMENT BREAK ===

-- Popular-loads metric: GROUP BY load_id to find most-booked lanes.
CREATE INDEX idx_bookings_load_id ON bookings (load_id);
