-- HR Twin: loads table — single source of truth for the loadboard catalog.
-- Live state: 15 columns + 2 indexes + 25 seed rows (verified 2026-04-25).
-- Run via Twin SQL editor (single-statement only) OR POST /api/v2/twin/sql.
-- Seed data lives in data/twin_seed_loads.sql.

CREATE TABLE loads (
  load_id TEXT PRIMARY KEY,
  origin_city TEXT NOT NULL,
  origin_state TEXT NOT NULL,
  destination_city TEXT NOT NULL,
  destination_state TEXT NOT NULL,
  pickup_datetime TIMESTAMPTZ,
  delivery_datetime TIMESTAMPTZ,
  equipment_type TEXT NOT NULL,
  loadboard_rate DOUBLE PRECISION NOT NULL,
  weight DOUBLE PRECISION,
  commodity_type TEXT,
  num_of_pieces BIGINT,
  miles BIGINT,
  dimensions TEXT,
  notes TEXT
);

-- Indexes (each must be a separate single-statement submission)
CREATE INDEX idx_loads_lane_equipment ON loads (origin_state, destination_state, equipment_type);
CREATE INDEX idx_loads_pickup ON loads (pickup_datetime);
