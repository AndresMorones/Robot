-- HR Twin: calls_log table — canonical v2 production schema.
-- Live state: 29 columns, semantic ordering (caller → lane → quality →
-- transcript → tokens → telemetry-end), all indexes + UNIQUE.
-- Verified live 2026-04-30 against successful run 532a2b4c (24/29 cols populated;
-- 5 expected NULLs: lane_origin/lane_dest when no lane discussed +
-- intermediate_response_count/p70_latency_ms/p90_latency_ms which are
-- HR-platform NULL per ADR-012 — dashboard derives latency from HR REST API).
-- Dropped: hangup_reason/room_name/status (cosmetic, reserved-then-dropped) +
-- node_timings_json (verified redundant — HR REST API has per-node timings).
--
-- Run via Twin SQL editor (single-statement only) OR POST /api/v2/twin/sql.
-- Statements separated by `-- === STATEMENT BREAK ===` per HR's single-statement rule.

CREATE TABLE calls_log (
  -- identity
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  call_id TEXT,

  -- caller identification
  mc_number TEXT,                                 -- bound from verify_carrier @ picker (NOT extract)
  carrier_name TEXT,                              -- bound from Extract.response.carrier_name
  callback_phone TEXT,                            -- bound from Voice Agent.from ("web" for web-calls is expected)
  fmcsa_eligibility_failure_reason TEXT,          -- bound from Extract.response.fmcsa_eligibility_failure_reason

  -- lane context (bound from Extract response, transcript-derived)
  lane_origin TEXT,                               -- format: "City, ST" or null
  lane_dest TEXT,                                 -- format: "City, ST" or null

  -- call outcome / quality
  call_outcome TEXT,                              -- bound from Extract.response.call_outcome (4-tag enum)
  sentiment TEXT,                                 -- bound from CHS.response.sentiment (4-tag enum)
  case_health_score BIGINT,                       -- bound from CHS.response.case_health_score (0-100)
  audit_remarks TEXT,                             -- bound from CHS.response.audit_remarks (1-3 sentences)
  notes TEXT NOT NULL DEFAULT '',                 -- bound from Extract.response.notes (handoff free-text; default '')

  -- conversation data
  transcript TEXT,                                -- bound from Voice Agent.transcript (full JSON array)

  -- token usage — Extract Call Details
  extract_input_tokens INTEGER,                   -- bound from Extract.llm_usage.input_tokens
  extract_output_tokens INTEGER,                  -- bound from Extract.llm_usage.output_tokens
  extract_reasoning_tokens INTEGER,               -- bound from Extract.llm_usage.reasoning_tokens
  extract_cached_input_tokens INTEGER,            -- bound from Extract.llm_usage.cached_input_tokens
  extract_uncached_input_tokens INTEGER,          -- bound from Extract.llm_usage.uncached_input_tokens

  -- token usage — Case Health Score
  chs_input_tokens INTEGER,                       -- bound from CHS.llm_usage.input_tokens
  chs_output_tokens INTEGER,                      -- bound from CHS.llm_usage.output_tokens
  chs_reasoning_tokens INTEGER,                   -- bound from CHS.llm_usage.reasoning_tokens
  chs_cached_input_tokens INTEGER,                -- bound from CHS.llm_usage.cached_input_tokens
  chs_uncached_input_tokens INTEGER,              -- bound from CHS.llm_usage.uncached_input_tokens

  -- operational telemetry (grouped at end per locked column-order direction 2026-04-30)
  duration_seconds BIGINT,                        -- bound from Voice Agent.duration
  intermediate_response_count BIGINT,             -- HR-platform var (NULL forever per ADR-012; dashboard derives from HR REST API)
  p70_latency_ms INTEGER,                         -- HR-platform var (NULL forever per ADR-012; dashboard derives from HR REST /runs/{id}/nodes)
  p90_latency_ms INTEGER                          -- HR-platform var (NULL forever per ADR-012; dashboard derives from HR REST /runs/{id}/nodes)
);

-- === STATEMENT BREAK ===

-- Idempotency: one calls_log row per call_id (Phase 3 v2 invariant).
ALTER TABLE calls_log ADD CONSTRAINT calls_log_call_id_uniq UNIQUE (call_id);

-- === STATEMENT BREAK ===

-- Dashboard time-window queries (e.g. "last 24h") sort by created_at DESC.
CREATE INDEX idx_calls_log_created_at ON calls_log (created_at DESC);

-- === STATEMENT BREAK ===

-- Carrier rollup queries: "show all calls from MC 123456".
CREATE INDEX idx_calls_log_mc_number ON calls_log (mc_number);

-- === STATEMENT BREAK ===

-- Funnel queries: GROUP BY call_outcome for outcome distribution.
CREATE INDEX idx_calls_log_call_outcome ON calls_log (call_outcome);
