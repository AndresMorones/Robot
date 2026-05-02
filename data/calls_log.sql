-- Twin Postgres schema for the inbound-carrier-v4 workflow's calls_log table.
-- Created via Twin SQL editor (HR-managed Postgres) on 2026-04-25.
-- Each row = one completed call. Populated by Twin Workflow Dump after every run.
--
-- IMPORTANT: Twin's SQL editor rejects inline `-- comments` inside CREATE TABLE.
-- If re-creating, paste only the CREATE TABLE statement below (no comments).
-- Reference comments live HERE in this file for repo readers, not in Twin.
--
-- Source map (24 columns):
--   2 HR auto fields (id, created_at)
--   1 HR built-in (call_id from __run_id__)
--   1 workflow variable (agent_version)
--   9 transcript-derived (via post-call AI Extract)
--   8 verify_carrier API output (via @ picker direct in Workflow Dump; nested path)
--   2 post-call classifier outputs (outcome, sentiment)
--   2 post-call analysis (audit_remarks, case_health_score)
--   1 callback (callback_phone — via AI Extract)
--
-- Detail in plan file's "VARIABLE ALIGNMENT LOCK 2026-04-25" section.

CREATE TABLE calls_log (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  call_id TEXT,
  agent_version TEXT,

  -- Carrier identity (6) — via AI Extract (transcript-derived) + verify_carrier (API)
  mc_number TEXT,                       -- Extract: from transcript
  dot_number BIGINT,                    -- verify_carrier.content.carrier.dotNumber
  legal_name TEXT,                      -- verify_carrier.content.carrier.legalName
  dba_name TEXT,                        -- verify_carrier.content.carrier.dbaName
  caller_name TEXT,                     -- Extract: from transcript
  caller_role TEXT,                     -- Extract: from transcript

  -- FMCSA eligibility snapshot (6) — via verify_carrier API + Extract for failure reason
  allowed_to_operate TEXT,              -- verify_carrier.content.carrier.allowedToOperate
  status_code TEXT,                     -- verify_carrier.content.carrier.statusCode
  safety_rating TEXT,                   -- verify_carrier.content.carrier.safetyRating
  carrier_operation_code TEXT,          -- verify_carrier.content.carrier.carrierOperation.carrierOperationCode
  fmcsa_eligibility_failure_reason TEXT,  -- Extract: from agent's decline phrasing → enum
  fmcsa_retrieval_date TIMESTAMP,       -- verify_carrier.retrievalDate

  -- Load + negotiation (4) — via Extract
  load_reference TEXT,                  -- Extract: from agent's pitch utterance "LOAD-0001..."
  pitched_loadboard_rate DOUBLE PRECISION,  -- Extract: from "Rate is $2,400"
  agreed_rate DOUBLE PRECISION,         -- Extract: from "we have a deal at $2,250"
  negotiation_rounds_used BIGINT,       -- Extract: counted from agent's counter-offers

  -- Call result (4) — via post-call classifiers + analysis nodes
  outcome TEXT,                         -- post-call Classify Outcome (8 enum tags)
  sentiment TEXT,                       -- post-call Classify Sentiment (4 enum tags)
  case_health_score BIGINT,             -- Case Health Score Code node (0-100)
  audit_remarks TEXT,                   -- Carrier Sales Auditor

  -- Callback (1) — via Extract
  callback_phone TEXT                   -- Extract: from agent's confirmation utterance, digits-only
);

-- Indexes for dashboard queries (add later if needed; 25-row MVP doesn't need them yet):
--   CREATE INDEX idx_calls_log_outcome ON calls_log (outcome);
--   CREATE INDEX idx_calls_log_mc_number ON calls_log (mc_number);
--   CREATE INDEX idx_calls_log_created_at ON calls_log (created_at DESC);

-- Verification queries after creation:
--   SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'calls_log' ORDER BY ordinal_position;
--   -- Expected: 24 rows
--
--   SELECT COUNT(*) FROM calls_log;
--   -- Expected: 0 (empty until first call.ended fires Workflow Dump)
