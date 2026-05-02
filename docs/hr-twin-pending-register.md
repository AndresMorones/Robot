# HR + Twin Pending Register

**Purpose.** Single canonical inventory of every HappyRobot-side change, Twin schema change, and HR/Twin operational task that is still pending, deferred, in-flight, or open. Synthesised from the user's memory store + repo SQL + HR architecture map + the two Phase C action plans + the activity log.

**Scope.** HR voice workflow (Voice Agent / Prompt / tools / Run Python sidecars / Extract / CHS / classifiers / webhooks / Northstars / evals / adversarial suites / workflow vars), Twin schemas (`calls_log`, `bookings`, `loads`), and the cross-cutting Write-to-Twin chip mappings that bind one to the other. NOT in scope: dashboard-only items, FastAPI hardening, infra/Fly polish, GitHub push, Loom recording — those have their own registers.

**Audit timestamp.** 2026-04-30.

---

## 1. Live state — canonical (what's already shipped)

### 1.1 HR voice workflow

| Property | Value | Source |
|---|---|---|
| Workflow name | `inbound-carrier-sales-new` (canonical fork-base) | `docs/hr-architecture-map.md:22` |
| Workflow ID | `019db77a-0548-741c-9ac8-d713bea1a51f` | `docs/hr-architecture-map.md:23` |
| Latest published version | v19 → v20-phase-c forked, v21 audited 2026-04-30, v22+ TBD after time-handling fix | `docs/hr-architecture-map.md:24`, `memory/project_hr_audit_2026_04_30_findings.md` |
| Latest version_id (v19) | `019ddc83-70c2-7f1e-bc03-b1232a6e07ed` | `docs/hr-architecture-map.md:24` |
| Workflow slug | `xsfvbpjpsoy4` | `memory/project_carlos_email_artifacts.md:41` |
| Languages enabled | 28 (LOCKED — F10 will NOT be narrowed per user direction 2026-04-28) | `memory/project_keep_all_languages.md`, `docs/hr-architecture-map.md:27` |
| Workflow vars | `agent_name`, `company_name`, `negotiation_floor_pct=0.10`, `max_negotiation_rounds=3`, `Time.Now` | `docs/hr-architecture-map.md:31-35` |

### 1.2 HR voice agent prompt

| Item | Value | Source |
|---|---|---|
| Repo ground-truth body | `prompts/voice-agent-system-prompt-v5.1.md` (404 lines / 5,930 words) | `memory/project_v5_rlhf_tuning_in_flight.md:11` |
| Live HR state | v5.1 pasted + user has applied v5.2 edits on top inside HR UI (not all v5.2 patches captured in repo) | `docs/hr-architecture-map.md:69-70` |
| In-call (system) prompt reference | `docs/references/happyrobot/voice-agent-prompt.md` | listed in CLAUDE.md |
| Post-call extraction prompt reference | `docs/references/happyrobot/post-call-extraction-prompt.md` | listed in CLAUDE.md |
| `_hangup` integration | WIRED in v5.1 on every terminal path | `docs/hr-architecture-map.md:114` |

### 1.3 HR custom tools (parented to Voice Agent → Prompt)

| # | Tool | Status | Action child | Source |
|---|---|---|---|---|
| 1 | `verify_carrier` | SHIPPED ✓ | Predefined Webhook → FMCSA `mobile.fmcsa.dot.gov` | `docs/hr-architecture-map.md:80-84` |
| 2 | `query_loads` | SHIPPED ✓ | Read-from-Twin (filter column `load_id`, sort pickup_datetime ASC, cap 25) | `docs/hr-architecture-map.md:86-92`, `memory/reference_loads_table_column_load_id.md` |
| 3 | `negotiate_rate` | SHIPPED ✓ | Run Python child = `calculate_rate.py` (reads both `now` and `now_iso` keys post F3 fix) | `docs/hr-architecture-map.md:94-101` |
| 4 | `book_load` | SHIPPED ✓ | Write-to-Twin → `bookings` (idempotency via UNIQUE(call_id, load_id)) | `docs/hr-architecture-map.md:103-110` |
| 5 | `_hangup` | HR built-in, wired in v5.1 | n/a | `docs/hr-architecture-map.md:113-114` |

### 1.4 HR post-call chain (after Voice Agent ends)

```
Voice Agent.transcript → AI Extract → Case Health Score → Update Data in Record (calls_log)
                                                       ↘ (BOOKED path) Transfer Popup
```

| Node | Status | Schema | Source |
|---|---|---|---|
| AI Extract | SHIPPED ✓ (JSON Schema strict mode) | 2 fields shipped: `call_outcome`, `fmcsa_eligibility_failure_reason` (NOTE: `notes`/`carrier_name`/`lane_origin`/`lane_dest` are queued — see §2 + §4) | `docs/hr-architecture-map.md:124-130`, `prompts/ai-extract-schema-v3.md` |
| Case Health Score | SHIPPED ✓ | 3 fields: `case_health_score (0-100)`, `audit_remarks`, `sentiment` | `docs/hr-architecture-map.md:132-135` |
| Update Data in Record (calls_log) | SHIPPED ✓ (29 cols live per `data/twin_schema_calls_log.sql`) | Maps tools/Extract/CHS @ pickers into Twin chip | `docs/hr-architecture-map.md:137-141` |
| Transfer Popup | CONFIGURED (mock transfer per spec, MVP minimum: `phone_number = "MC-{{mc_number}}"`) | `memory/reference_hr_create_popup_schema.md` |

### 1.5 Twin schemas — live state (canonical)

**`loads`** (per `data/twin_schema_loads.sql`): 15 cols, PK is `load_id` TEXT (NOT `id` BIGSERIAL — verified 2026-04-28 per `memory/reference_loads_table_column_load_id.md`).
- `load_id, origin_city, origin_state, destination_city, destination_state, pickup_datetime, delivery_datetime, equipment_type, loadboard_rate, weight, commodity_type, num_of_pieces, miles, dimensions, notes`
- Indexes: `idx_loads_lane_equipment` (origin_state, destination_state, equipment_type), `idx_loads_pickup`
- Live row count: 150 (refreshed 2026-04-28; May 2026 → Oct 2030 weighted heavy May–Aug). HR architecture map lists 18 cols which contradicts the SQL file (15) — see §10 confidence-and-gaps.

**`calls_log`** (per `data/twin_schema_calls_log.sql`): 29 cols (canonical v2). Order: identity → caller → lane → quality → transcript → tokens → telemetry-end.
- 29 cols: `id, created_at, call_id, mc_number, carrier_name, callback_phone, fmcsa_eligibility_failure_reason, lane_origin, lane_dest, call_outcome, sentiment, case_health_score, audit_remarks, notes, transcript, extract_input_tokens, extract_output_tokens, extract_reasoning_tokens, extract_cached_input_tokens, extract_uncached_input_tokens, chs_input_tokens, chs_output_tokens, chs_reasoning_tokens, chs_cached_input_tokens, chs_uncached_input_tokens, duration_seconds, intermediate_response_count, p70_latency_ms, p90_latency_ms`
- UNIQUE constraint on `call_id` + indexes on `created_at DESC`, `mc_number`, `call_outcome`
- Verified live 2026-04-30 against run `532a2b4c` — 24/29 cols populated; 5 expected NULLs (lane_origin/lane_dest when no lane discussed + intermediate_response_count/p70/p90 — see §5)
- Phase C v2 plan said the target was 32 cols (`hangup_reason`, `room_name`, `status`, `node_timings_json` were transient adds) — final shape dropped those four per `data/twin_schema_calls_log.sql` header comment

**`bookings`** (per `data/twin_schema_v15_bookings.sql`): 6 cols.
- `id, created_at, call_id, mc_number, load_id, apply_rate`
- UNIQUE(call_id, load_id) idempotency — exercised live (caught duplicate book_load on v15 E2E)
- Indexes: `idx_bookings_created_at`, `idx_bookings_call_id`, `idx_bookings_mc_number`, `idx_bookings_load_id`

### 1.6 Auth + key wiring

| Token | Surface | Holder | Source |
|---|---|---|---|
| `API_BEARER_TOKEN` | `/v1/*` Bearer + `x-api-key` header (header-only per ADR-008) | Fly secret on `robot-api`; same value Next.js uses server-side | `docs/hr-architecture-map.md:174` |
| `HAPPYROBOT_API_KEY` (`sk_live_...`) | FastAPI → HR Twin REST gateway | Fly secret server-side only; rotated twice 2026-04-30 | `memory/project_twin_production_lock_in.md` |
| `FMCSA_WEB_KEY` (`cdc33e44...`) | HR `verify_carrier` GET MC Number webhook URL | LIVE in plaintext URL (F11 OPEN) | `memory/project_fmcsa_key_provided.md` |

---

## 2. HR-side OPEN items (still pending)

### 2.A Voice agent prompt patches (`<call_notes>`, time-handling, VP-1..VP-5)

| ID | Title | Severity | Effort | Source memory | Trigger | Depends on |
|---|---|---|---|---|---|---|
| VP-1 | Clarification-loop cap — never re-ask same slot more than once; if non-answer filler twice, offer 2-3 specific options | IMPORTANT | S | `project_v15_e2e_first_pass_findings.md`, `docs/hr-phase-c-action-plan-v2.md C-T2.10` | Phase C v2 paste pass | none |
| VP-2 | Narrowing rule — require ≥1 of (origin OR destination OR equipment) before calling `query_loads` | IMPORTANT | S | same | same | none |
| VP-3 | Recap-before-transfer strict 6-tuple (load_id, origin, dest, equipment, pickup, rate) | IMPORTANT | S | same | same | none |
| VP-4 | No-retry on FMCSA decline — one mishear retry, then end | IMPORTANT | S | same | same | none |
| VP-5 | Intent-language negotiation phrasing — vary across rounds, no script-language repetition | IMPORTANT | S | same | same | none |
| VP-6 | `<call_notes>` section guiding agent to capture alt callback / dispatcher Q / soft notes (paired with `notes` Extract param + `notes` Twin column) | IMPORTANT | S | `project_callback_audit_field.md`, Phase C v2 C-T2.2 | bundle with §3 `notes` column add | §3 `notes` column DDL + §2.D Extract `notes` param |
| VP-7 | Robotic negotiation phrasing polish (carry-over from v15 first-pass findings) | POLISH | S | `project_v15_e2e_first_pass_findings.md` item 5 | post-test-call iteration | none |
| VP-8 | TIME-HANDLING — replace `<calendar_context>` block + add new `<time_handling>` section + add line to `<closing_reminders>` | BLOCKING (now ACTIVE; was DEFERRED 2026-04-30 night, RESUMED per audit instruction) | M | `project_time_handling_critical_deferred.md`, `reference_hr_time_data_inventory.md` | NOW (see §6) | §2.B `get_current_time` tool |

Also flagged in `project_post_mvp_prompt_improvements.md` (deferred): generalize human-broker persona, active narrowing pre-search, off-topic redirect, multi-state regional search.

### 2.B Tool definitions

| ID | Title | Severity | Effort | Source | Depends on |
|---|---|---|---|---|---|
| T-1 | Build `get_current_time` Tool node + Run Python child (paste-ready code in `project_time_handling_critical_deferred.md`) — returns `spoken_clock_eastern`, `today_eastern`, etc. | BLOCKING (active fix) | M | `project_time_handling_critical_deferred.md` Edit 3 | none |
| T-2 | F14 — flip `verify_carrier.mc_number.required`, `negotiate_rate.loadboard_rate.required`, `negotiate_rate.pickup_datetime.required` from `null` to `true` | OPEN HIGH | S (3 boolean flips, ~2 min) | `project_hr_audit_2026_04_30_findings.md` | none |
| T-3 | F9 — `book_load` tool name trailing space cleanup ("book_load " → "book_load") | POLISH | S | `project_hr_review_later_inventory.md` item 7, `project_phase_b_complete_audit_2026_04_28.md` D2 | none — verify done |
| T-4 | F11 / F23 — clear plaintext `apiKey` field on the `GET MC Number` webhook (URL re-routed to header/param via API Key auth dropdown; legacy plaintext field still holds the secret) | OPEN MEDIUM | S | `project_hr_audit_2026_04_30_findings.md`, `docs/hr-phase-c-action-plan-v2.md C-T2.1` | none |
| T-5 | Add `status` filter (`equals 'available'`) to `query_loads` Read-from-Twin filter set | DEFERRED (Tier-2) | S | `project_load_booked_status_lifecycle.md`, `docs/hr-architecture-map.md:92` | depends on §3 loads.status DDL |
| T-6 | Add `cancel_booking` tool (real-prod cancellation flow) | DEFERRED (Tier-2) | M | `project_hr_review_later_inventory.md` item 9 | depends on §3 loads.status DDL |

### 2.C Run Python sidecars

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| RP-1 | `get_current_time` Code paste — already authored in memory; sandbox-safe (RestrictedPython compliant, no leading-underscore identifiers, no networking) | BLOCKING (active fix) | M | `project_time_handling_critical_deferred.md` Edit 3 |
| RP-2 | `calculate_rate` — F3 `now`/`now_iso` key mismatch — already RESOLVED 2026-04-28 (Python now reads both keys); verify retained on v19/v20+ | RESOLVED, verify | S | `reference_hr_architectural_review_2026_04_28.md` F3, `docs/hr-phase-c-action-plan.md` T1.3 |
| RP-3 | `negotiate_evaluate` Python sidecar — KB references it under `negotiate_rate` Tool but the actual sidecar is the simpler `calculate_rate` Run Python; the full negotiation state machine sits in HR's `negotiate_evaluate` Python Code security sidecar (CLAUDE.md). Verify the live shape and whether `final_floor` / `urgency_tier` are surfaced cleanly | OPEN VERIFY | S | CLAUDE.md "Don't put the negotiation state machine in Python-on-our-API" |
| RP-4 | Capture Node Timings Run Python — DEFERRED per ADR-012 (dashboard-side compute from transcript + duration; only build if HR run details API turns out insufficient). Twin column `node_timings_json` was added then DROPPED in v2 cleanup — verify `data/twin_schema_calls_log.sql` does not contain it (confirmed: dropped) | DEFERRED | M | `docs/hr-phase-c-action-plan-v2.md C-T2.9`, `project_dashboard_latency_compute_locked.md`, ADR-012 |

### 2.D Extract prompt + schema parameters

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| EX-1 | Add `notes` field (string, nullable, `required:true` per strict mode) to AI Extract JSON Schema + add description string from `project_callback_audit_field.md` | IMPORTANT | S | `docs/hr-phase-c-action-plan-v2.md C-T2.2(a)`, `project_callback_audit_field.md` |
| EX-2 | Add `carrier_name`, `lane_origin`, `lane_dest` Extract fields (string, nullable, `required:true`) — Phase C v2 C-T2.3 | IMPORTANT | S | `docs/hr-phase-c-action-plan-v2.md C-T2.3(a)` |
| EX-3 | Strict-mode hygiene — verify every Extract property is in `required[]`, optionals as `["string","null"]`, `additionalProperties:false` on every object level (Azure structured-output rules) | RESOLVED, verify | S | `reference_hr_extract_strict_schema_rules.md` |
| EX-4 | Post-MVP enum tightening — `audit_remarks` predefined enum + "other" fallback; `fmcsa_eligibility_failure_reason` enum from FMCSA codes; drop `booking_decision` (call_outcome covers it); rebind `pitched_loadboard_rate`/`agreed_rate` from Twin row not transcript Extract | DEFERRED (post-MVP) | L | `project_post_mvp_field_design_research.md` items 1-5 |

### 2.E CHS prompt + schema parameters

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| CH-1 | F15 cosmetic — rename "Case Healt Score" → "Case Health Score" in the AI Extract node title | POLISH | S (~30s) | `docs/hr-phase-c-action-plan-v2.md C-T2.8` |
| CH-2 | Verify CHS prompt + 3 outputs (case_health_score / audit_remarks / sentiment) match `data/twin_schema_calls_log.sql` ordering — already verified 2026-04-30 | RESOLVED | — | `docs/hr-architecture-map.md:132-135` |
| CH-3 | Post-MVP — pair sentiment 3-tag enum with NPS-style numeric trajectory + first/last/transition fields (per industry research) | DEFERRED (post-MVP) | M | `project_post_mvp_field_design_research.md` item 7 |
| CH-4 | Self-reflection column — agent-generated edge-case / improvement note per call (recursive self-improvement loop) | DEFERRED (post-MVP) | M | `project_post_mvp_self_reflection_column.md` |

### 2.F Real-time classifiers (F12 cleanup)

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| RT-1 | F12 — Real-time `Call Outcome` classifier has `classes: []`. Decision LOCKED Phase C v2: REMOVE the node entirely (post-call Extract handles `call_outcome` reliably; real-time observability is not consumed downstream). Verify the deletion landed | OPEN MEDIUM | S | `docs/hr-phase-c-action-plan-v2.md C-T2.7`, `project_hr_audit_2026_04_30_findings.md` |
| RT-2 | F7 (legacy) — taxonomy mismatch: real-time classifier had 5 classes incl `rate_disagreement`; post-call Extract has 4. RESOLVED by F12 deletion (RT-1) | RESOLVED via RT-1 | — | `reference_hr_architectural_review_2026_04_28.md` F7 |

### 2.G Workflow variables

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| WV-1 | Add `time.now_utc.iso` and `time.now_utc.friendly` references via @ picker in `<calendar_context>` (LOCKED replacement block in `project_time_handling_critical_deferred.md`) | BLOCKING (active fix) | S | `project_time_handling_critical_deferred.md` Edit 1 |
| WV-2 | Confirm `time.now_america_new_york.iso` is NOT used anywhere — it returns `-05:00` (EST) year-round, wrong during DST. Replace any remaining usage with `time.now_utc` | OPEN VERIFY | S | `reference_hr_time_data_inventory.md` |
| WV-3 | Existing 4 tunable vars (`negotiation_floor_pct`, `max_negotiation_rounds`, `agent_name`, `company_name`) are LIVE — no action | RESOLVED | — | `docs/hr-architecture-map.md:31-35` |

### 2.H Webhook configs

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| WH-1 | F21 — `Send Event Notification` webhook payload uses `Voice Agent.session_id`; `calls_log.call_id` and `bookings.call_id` use `current.run_id`. Align all three (run_id wins, used by 2/3 sites). User-claimed-fixed 2026-04-30 night; awaiting HR-AI verification round 2 | OPEN MEDIUM (user claims fixed, unverified) | S | `project_hr_audit_2026_04_30_findings.md` |
| WH-2 | F11 / F23 (T-4 above) — webKey relocate via API Key auth dropdown — user-claimed-fixed 2026-04-30 night; awaiting verification | OPEN MEDIUM (user claims fixed, unverified) | S | same |
| WH-3 | `call.ended` workflow webhook → `POST /v1/events/call-ended` (Bearer auth, idempotent on call_id) — SHIPPED ✓ | RESOLVED | — | `docs/hr-architecture-map.md:39-49` |
| WH-4 | DEFERRED — second `negotiation.counter` webhook fires mid-call from `negotiate_rate` sidecar to expose live counter offer + `final_floor` to sales-rep dashboard via SSE | DEFERRED (Tier-2) | M | `project_realtime_negotiation_hook.md`, `docs/hr-architecture-map.md:281-284` |

### 2.I Northstars / evals / adversarial suites

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| NS-1 | Define Northstars on Prompt node — 2 measurable + 3 behavioral (drafted in Phase C v2 C-T2.11) | POLISH | S (~5 min) | `docs/hr-phase-c-action-plan-v2.md C-T2.11`, `project_hr_review_later_inventory.md` item 1 |
| NS-2 | Reusable Prompt Component (extract negotiation policy + style guide into a Component for cross-workflow reuse) | DEFERRED | M | `project_hr_review_later_inventory.md` item 2 |
| NS-3 | Adversarial test suite activation (HR's built-in red-team tooling — not activated) | DEFERRED | M | `project_hr_review_later_inventory.md` item 3 |
| NS-4 | Custom evals (regression tests on prompt changes) | DEFERRED | M | `project_hr_review_later_inventory.md` item 4 |
| NS-5 | Super-test workflow — 10 edge tests per node × cheap-LLM substrate, then 10 live HR test calls (production-publish gate) | DEFERRED | L | `project_super_test_workflow.md` |

### 2.J Audit findings index — see §7 for the full F1-F25 status table.

---

## 3. Twin-side OPEN items (still pending)

### 3.A Schema additions

| ID | Title | DDL | Severity | Effort | Source |
|---|---|---|---|---|---|
| TS-1 | Already-applied `notes` column on calls_log (column name LOCKED 2026-04-30 as `notes`) — confirmed live in `data/twin_schema_calls_log.sql` line 35 | — | RESOLVED IN SCHEMA FILE; verify Twin matches live — paste `ALTER TABLE calls_log ADD COLUMN notes TEXT NOT NULL DEFAULT '';` if not live yet | S | `project_callback_audit_field.md`, `data/twin_schema_calls_log.sql:35` |
| TS-2 | Load-status lifecycle on `loads` — `ALTER TABLE loads ADD COLUMN status TEXT NOT NULL DEFAULT 'available'; ADD COLUMN booked_at TIMESTAMPTZ NULL; ADD COLUMN booked_by_call_id TEXT NULL; CREATE INDEX idx_loads_status ON loads(status);` (4 single statements) | see DDL | DEFERRED (Tier-2 production) | S | `project_load_booked_status_lifecycle.md` |
| TS-3 | Carrier aggregates table for persistent rollups — `CREATE TABLE carrier_aggregates (mc_number, total_calls, booking_rate, avg_agreed_discount, ...)` + nightly refresh | see source | DEFERRED (Tier-2) | M | `project_dashboard_hr_twin_dependencies.md` |
| TS-4 | Tool-call timeline table — `CREATE TABLE tool_calls (id, call_id, tool_name, fired_at, args JSONB, result JSONB)` + HR Workflow Dump fan-out | see source | DEFERRED (Tier-2) | M | `project_dashboard_hr_twin_dependencies.md` |
| TS-5 | `bookings.original_rate DOUBLE PRECISION` for pitched-vs-applied delta tracking (broker upside metric). `book_load` tool gains `original_rate` param; bookings chip binds it. Phase C v2 says NOT-IN-SCOPE; v16 enhancement | DEFERRED | M | `docs/hr-phase-c-action-plan-v2.md` Tier-3 §, `memory/project_field_renames_pending.md` |

### 3.B Schema renames

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| TR-1 | DEFERRED — `pitched_loadboard_rate → original_rate` (legacy v14 calls_log column from a now-dropped path; cleanup) | DEFERRED — column dropped from v15 calls_log; rename moot for canonical schema; FastAPI grep-replace pending | S | `project_field_renames_pending.md`, `docs/hr-phase-c-action-plan-v2.md` Tier-3 |
| TR-2 | DEFERRED — `agreed_rate → apply_rate` (already done in `bookings`; legacy `calls_log.agreed_rate` column was dropped in v15 cleanup. FastAPI grep-replace + dashboard renames pending) | DEFERRED — column dropped; FastAPI side renames pending only if Pydantic models still reference old names | S | `project_field_renames_pending.md` |

NOTE: per Phase C v2 Tier 3 "N/A AT v2 LOCK" — bookings.apply_rate is already the new name; `original_rate` was deliberately not added (lean-design); the entire renames memory file is now stale-but-not-closed. Close it after FastAPI grep-replace verification.

### 3.C Data refreshes

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| DR-1 | Refresh `data/loads.csv` to 100-500 rows all dated AFTER demo day. Current: refreshed to 150 rows on 2026-04-28 (May 2026 → Oct 2030, weighted heavy May–Aug). Re-verify all rows are still future-dated when demo-day approaches | DONE 2026-04-28; re-verify pre-demo | S | `project_loads_dummy_data_refresh.md`, `docs/hr-architecture-map.md:152` |
| DR-2 | Twin `loads` table sync — confirm 150-row reseed landed in Twin (script `scripts/sync_twin_loads.py`) | DONE 2026-04-28; re-verify | S | `docs/hr-architecture-map.md:151` |
| DR-3 | Full Twin data re-audit after 5-10 real test calls produce v14+ Extract data — per-column scorecard (population, shape, source-of-truth, cardinality, coverage, drift) | DEFERRED (trigger before Phase 6 test re-run OR Phase 7 polish) | L | `project_twin_data_reaudit.md` |

### 3.D Indexes / constraints / triggers

| ID | Title | Severity | Effort | Source |
|---|---|---|---|---|
| IDX-1 | `idx_loads_status` index for the load-status lifecycle (depends on TS-2) | DEFERRED | S | `project_load_booked_status_lifecycle.md` |
| IDX-2 | `idx_calls_log_sentiment` index for sentiment-distribution dashboards (queued in v2 phase plan) | OPEN | S | `project_phase3_calls_log_v2.md` |
| IDX-3 | Cron / scheduled flip — `loads SET status='expired' WHERE pickup_datetime < NOW() AND status='available'` | DEFERRED | M | `project_load_booked_status_lifecycle.md` |

### 3.E Cleanup of dropped columns / leftover Phase C transients

| ID | Title | Status | Source |
|---|---|---|---|
| CL-1 | `node_timings_json` Twin column — added 2026-04-30 night, then DROPPED in v2 cleanup (per `data/twin_schema_calls_log.sql` header comment "Dropped: ... node_timings_json (verified redundant — HR REST API has per-node timings)") — verify it is NOT live in Twin (run `SELECT column_name FROM ... WHERE table_name='calls_log'` once Twin probe is available) | RESOLVED IN SCHEMA FILE; verify live | `data/twin_schema_calls_log.sql` header |
| CL-2 | `hangup_reason`, `room_name`, `status` — Phase C v2 added 3 new cols; v2 schema file shows them DROPPED (cosmetic, reserved-then-dropped). Verify Twin matches | RESOLVED IN SCHEMA FILE; verify live | same |
| CL-3 | Phase C v2 column reorder (drop+recreate via INSERT SELECT) — was canonical 32-col plan in `docs/hr-phase-c-action-plan-v2.md`. Final schema file is 29 cols with the 4 dropped (above) — confirm Twin live shape against the SQL file | OPEN VERIFY | `docs/hr-phase-c-action-plan-v2.md C-T1.1`, `data/twin_schema_calls_log.sql` |

---

## 4. HR + Twin both touched (cross-cutting)

These items require BOTH the Twin DDL AND the HR @ picker / chip mapping change in lockstep. Don't ship one half without the other.

### 4.1 `notes` column rollout (column name LOCKED 2026-04-30)

| Half | Action | Source |
|---|---|---|
| Twin | `ALTER TABLE calls_log ADD COLUMN notes TEXT NOT NULL DEFAULT '';` (already in `data/twin_schema_calls_log.sql`) | TS-1 |
| HR — Extract | Add `notes` field to AI Extract JSON Schema (string nullable, required:true, description per memory file) | EX-1 |
| HR — Prompt | Add `<call_notes>` section guiding agent capture (paste-ready in `project_callback_audit_field.md` Option A; also Phase C v2 C-T2.2(b)) | VP-6 |
| HR — Log Event chip | Add column mapping `notes ← @Extract.response.notes` | `docs/hr-phase-c-action-plan-v2.md C-T2.2(c)` |
| Dashboard | Surface in call-detail view (already displayed-when-present per `project_dashboard_calls_logs_tab.md`) | `project_dashboard_hr_twin_dependencies.md` |

### 4.2 Load-status lifecycle (Tier-2 production)

| Half | Action | Source |
|---|---|---|
| Twin | `ALTER TABLE loads ADD COLUMN status TEXT NOT NULL DEFAULT 'available'; ADD COLUMN booked_at TIMESTAMPTZ; ADD COLUMN booked_by_call_id TEXT;` + index `idx_loads_status` | TS-2 |
| HR — book_load | Add a parallel Update-Twin-Row chain that flips `loads.status='booked', booked_at=NOW(), booked_by_call_id=@call_id` | `project_load_booked_status_lifecycle.md` |
| HR — query_loads | Read-from-Twin filter `status equals 'available'` (always-on) | T-5 |
| Operations | Cron / scheduled SQL to flip stale rows to `expired`; manual `cancel_booking` tool to flip back to `available` | IDX-3, T-6 |

### 4.3 Token capture (already shipped — verify both halves)

| Half | Action | Status | Source |
|---|---|---|---|
| Twin | 10 INTEGER columns: `extract_*_tokens` + `chs_*_tokens` (in canonical schema file) | RESOLVED | `data/twin_schema_calls_log.sql` |
| HR — Log Event chip | 10 @ picker bindings — Phase C v2 C-T2.4 (resume from paused state — was C5.2 mid-flow) | RESOLVED 2026-04-30 night per HR-AI verification round 1 | `project_hr_audit_2026_04_30_findings.md` "All 10 token bindings CLEAN" |

### 4.4 F7 six-column extension (Phase C v2 C-T2.3)

| Half | Action | Status | Source |
|---|---|---|---|
| Twin | `carrier_name`, `lane_origin`, `lane_dest` cols | RESOLVED IN SCHEMA FILE | `data/twin_schema_calls_log.sql` lines 22-29 |
| Twin (transient) | `hangup_reason`, `room_name`, `status` — were on Phase C v2 32-col plan, then DROPPED in v2 cleanup | DROPPED — verify Twin matches | CL-2 |
| HR — Extract | Add 3 NEW Extract params: `carrier_name`, `lane_origin`, `lane_dest` | EX-2 |
| HR — Log Event chip | Bind 3 from Extract @ picker | OPEN | C-T2.3(b) |

### 4.5 Real-time negotiation hook (DEFERRED Tier-2)

| Half | Action | Source |
|---|---|---|
| HR | Add `Send Webhook` action child under `negotiate_rate` (or after `calculate_rate`) firing per round | `project_realtime_negotiation_hook.md` |
| FastAPI | New endpoint `POST /v1/events/negotiation-counter` receiving payload | `docs/hr-architecture-map.md:281-284` |
| Frontend | SSE subscriber on sales-rep dashboard | `project_sales_dashboard_view.md` |

### 4.6 F16 — log_event chip missing 3 bindings (`hangup_reason`, `room_name`, `status`)

User-claimed-fixed 2026-04-30 night per `project_hr_audit_2026_04_30_findings.md`; awaiting HR-AI verification round 2. NOTE: the canonical schema file DROPPED these 3 cols, so the user's "claimed fix" + the schema-file drop together imply both halves landed on a "remove rather than bind" decision — verify which path actually shipped on the next live Twin probe.

---

## 5. Items that CANNOT be done by us (HR platform limitations)

These are HR-platform constraints. Working around them is the user's job, not the platform's job to fix. Document them clearly so reviewer doesn't think they're our bugs.

| Limitation | Impact | Workaround | Source |
|---|---|---|---|
| `intermediate_response_count`, `p70_latency_ms`, `p90_latency_ms` columns will stay NULL on every call. HR var binding broken even after F8 fix | Latency telemetry NULL in Twin | Dashboard-side compute from `transcript` + `duration_seconds` per ADR-012 (Phase 1) + HR run details API (Phase 2) | `project_dashboard_latency_compute_locked.md`, ADR-012 |
| HR REST API does NOT expose transcript content (`/api/v2/runs/{id}` is metadata only — id, org_id, workflow_id, version_id, status, annotation, timestamp, completed_at, execution_environment) | Cannot poll for transcripts | 3 paths only: async CSV export, MCP `get_transcript`, in-workflow @ picker → `<Voice Agent>.transcript`. We use path 3 (Twin write) | `reference_hr_transcript_access_paths.md` |
| HR API mutations (PUT / POST nodes / DELETE / unpublish-unlock-PUT-republish) leave invisible runtime corruption that propagates through forks. Voice goes silent without errors | Cannot use HR REST API to mutate voice-workflow nodes | UI-only edits on voice workflows. API safe ONLY for: workflow vars, Twin DDL via `/twin/sql`, fork-from-clean-ancestor, GET reads, publish UI-built versions | `reference_hr_post_batch_corruption.md`, `reference_hr_fork_corruption.md` |
| HR import-from-template breaks `call.static.id` references inside Voice Agent configs (HR's importer doesn't rewrite this one field). Voice silent post-import | Cannot reproduce voice workflows by JSON import alone | After import, open Voice Agent in HR UI → re-bind "Call source" → 30-second fix. Or build from scratch in UI on a forked-from-clean-ancestor base | `reference_hr_import_breaks_references.md` |
| HR Twin SQL editor is single-statement only (no `;`-separated, no comments) | Multi-statement DDL must be split | Submit each statement separately; `data/twin_schema_*.sql` files use `-- === STATEMENT BREAK ===` markers | `reference_hr_procedural_quirks.md` |
| Cloudflare WAF in front of `/twin/sql` blocks `information_schema`, `ORDER BY+LIMIT`, multi-aggregate SELECT, IN-list literals, UNION | Some queries 403 with HTML response | Pull raw rows + aggregate in Python (`api/app/services/dashboard_aggregations.py`); use `LEFT JOIN ... IS NULL` instead of `NOT IN` | `reference_cloudflare_waf_twin.md` |
| HR Read-from-Twin `equals` operator is literal string comparison — empty-string parameter becomes `WHERE column = ''` (excludes every row) | Optional tool params can't bind to Read-from-Twin filter via `equals` | Don't add filter for optional fields; let agent reason over returned rows in-context | `reference_hr_twin_empty_string_filter.md` |
| HR Run Python sandbox = RestrictedPython. Blocks dunder access (`__name__`, `__class__`), leading-underscore identifiers, networking modules (urllib, requests, httpx, socket) | Must rewrite normal-Python before paste | Use plain names (no `_dt`); use `str(e)` not `type(e).__name__`; outbound HTTP impossible from Run Python | `reference_hr_python_sandbox_restrictions.md` |
| HR Voice Agent (AIC) output schema only fully populates on workflows with prior call history | Fresh workflows show greyed @ picker for Voice Agent forever | Always fork from `Inbound Carrier Sales New` (workflow_id `019db77a-...`); never build new workflows from scratch | `reference_hr_workflow_schema_population.md` |
| HR Extract Test Node fails with "room name required" sandbox-only error on inbound-voice-agent children | Cannot validate Extract via Test button | Validate via real test web call → run details | `reference_hr_extract_test_node_sandbox.md` |
| HR `model.static.id` is internal registry id, not display name (`turbo-one` not `gpt-4.1`). API silently accepts any string; runtime fails silently | Voice silent if `id` derived from `name` | Always GET node's current `model` field BEFORE PUT and copy `id` verbatim | `reference_hr_model_registry.md` |
| HR `time.now_america_new_york.iso` returns `-05:00` (EST) year-round, ignoring DST. `time.now_america_new_york.friendly` likewise off | Time-related variables drift 1 hour during DST | Use `time.now_utc.iso` / `time.now_utc.friendly` always; `data.now` field on Analyze Incoming Conversation is broken | `reference_hr_time_data_inventory.md`, `project_time_handling_critical_deferred.md` |
| HR `Carrier Sales Auditor` exposes ONLY 2 outputs at @ picker (`final_offer_position`, `posted_price_increase`). NO `audit_remarks` / narrative-text field | Plans relying on auditor producing free-text audit string must redirect | Use `Case Health Score.response.health_score_reasoning` (or v15 CHS `audit_remarks`) as the closest substitute | `reference_hr_procedural_quirks.md` Auditor section |
| HR Twin DB is take-home grade not production-grade — SPOF on `HAPPYROBOT_API_KEY`, cross-org coupling, WAF restrictions, no SLA | Customer (Acme) cannot run a copy without their own HR org + Twin tables + API key | Tier-2 escape: Postgres migration (~6-8 hr Claude); for take-home, document as Tier-2 roadmap not blocker | `project_twin_production_lock_in.md` |
| HR sk_live_* keys can be revoked / rotated unexpectedly (rotated twice in one day 2026-04-30) | Dashboard 502s on revoke | Background monitor at `scripts/monitor_hr_key.py`; demo-day mitigation = rotate 30-60 min pre-meeting + smoke-test | same |

---

## 6. Time-handling fix — full action item (now ACTIVE, was DEFERRED)

**Status as of audit:** ACTIVE FIX. User direction 2026-04-30 night was *"I'm tired and blocked lets note this problem as highly critical on plan but lets postpone setting of this hour but do not forget to do at some point."* The fix is ready to paste — full content lives in `memory/project_time_handling_critical_deferred.md`.

**Severity:** CRITICAL (BLOCKING for production demo). Affects every call's correctness — translation rules need today's date as anchor; pickup_datetime math (`hours_until_pickup`) needs current time; carriers will ask "what time is it?" and agent currently hallucinates wildly (verified across 4+ test calls — said "14:00 central time", "2026-04-27T08:00 local time", "10 o'clock" with no source).

**Three root causes (3 leak channels)**
1. Translation block hour anchors leak into agent narration ("this afternoon" → 14:00 was internal-only, agent emits 14:00 when asked the time).
2. Calendar_context @ picker chip is malformed (truncated text suggests hover preview leaked into prompt instead of properly-bound chip).
3. No `<time_handling>` rule — prompt has zero positive instruction on what to do when asked the time.

**Locked fix architecture** (paste-ready in memory file):
1. Edit 1 — REPLACE `<calendar_context>` block entirely with the inject-UTC-at-call-start version (chips for `time.now_utc.iso` + `time.now_utc.friendly`, plus the carrier-speech→ISO translation rules clearly marked INTERNAL ONLY)
2. Edit 2 — ADD `<time_handling>` section after `<calendar_context>` (forbids speaking digital format / ISO / digit-by-digit; mandates calling `get_current_time` tool; speak only `spoken_clock_eastern` string)
3. Edit 3 — BUILD `get_current_time` Tool node + Run Python child node. Code is paste-ready in memory — DST-aware, returns `spoken_clock_eastern` ("four thirty five P M Eastern Daylight Time"), `natural_clock_eastern`, `natural_clock_utc`, `today_eastern` ("Thursday, April 30"), `now_utc_iso`, `now_eastern_iso`, `is_dst`. Sandbox-safe (no leading-underscore identifiers, no networking, no dunder access).
4. Edit 4 — APPEND to `<closing_reminders>`: "TIME questions: ALWAYS call get_current_time. Speak ONLY the `spoken_clock_eastern` string..."
5. Edit 5 — FORK current published version → next version (v22 / v23 depending on current state). Voice workflows fork-on-edit when published (HR rule).

**Click-by-click steps the user has to do** (in HR UI — UI ONLY per `reference_hr_post_batch_corruption.md`):
1. Open the canonical workflow → fork latest published version.
2. Open Prompt node body → SELECT existing `<calendar_context>` block → DELETE → PASTE the LOCKED replacement (chips inserted via @ picker, NOT hand-typed).
3. After `<calendar_context>` block, PASTE the `<time_handling>` section (verbatim from memory).
4. APPEND the closing-reminders one-liner.
5. CREATE a new Tool node parented to Voice Agent → Prompt. Name: `get_current_time`. Empty params `{}`. Description per memory file (verbatim).
6. Under that tool, ADD a Run Python child action. Event Name: `Get Current Time`. Input Data: empty. PASTE the Code block from memory file (replaces the default `output = {}`).
7. SAVE all nodes.
8. PUBLISH the new version to development environment.
9. Run a single test web call: ask "what time is it?" — expect agent to call `get_current_time` and read `spoken_clock_eastern` cleanly ("four thirty five P M Eastern Daylight Time" not "four three five P M").
10. F25 follow-up — also verify `<calendar_context>` no longer renders the truncated "Thursday, A...7:41 PM UTC" hover-preview leak.

**Resume trigger phrases:** "let's fix the time" / "build the get_current_time tool" / "do the time fix" / "now let's do the deferred time work."

---

## 7. v19 audit findings — F1-F25 status table

Sources: `reference_hr_architectural_review_2026_04_28.md` (F1-F11 catalog), `project_hr_audit_2026_04_30_findings.md` (v21 audit, F12-F25 + F1-F11 status updates).

| Finding | Status | Severity | Source | Notes |
|---|---|---|---|---|
| F1 — book_load missing Write-to-Twin child | RESOLVED in v18 | was BLOCKING | reference 2026-04-28, v21 audit | verified RESOLVED v18+ |
| F2 — Voice Agent Prompt body fully duplicated | RESOLVED in v18+ | was BLOCKING | same | Phase C C3.1 verified single occurrence |
| F3 — calculate_rate `now`/`now_iso` key mismatch | RESOLVED 2026-04-28 | was BLOCKING | same | Python now reads both keys |
| F4 — book_load `mc_number` + `apply_rate` `required:null` | RESOLVED Phase C C3.2 | was HIGH | same | flipped to required:true |
| F5 — Extract + CHS overlap on 4 fields | RESOLVED in v15 split | was HIGH | reference 2026-04-28 | Extract emits 2 fields, CHS emits 3 fields (no overlap) |
| F6 — Log Event column map drift (6 unmapped + 3 stale v14) | PARTIAL — 24/29 cols populated; expected NULLs documented | was HIGH | same | Phase C v2 closed via column reorder + new bindings |
| F7 — Real-time classifier taxonomy mismatch (5 classes vs 4 enum) | RESOLVED via F12 removal | was HIGH | same | Phase C v2 C-T2.7 removed the classifier |
| F8 — `p90_latency_ms` Twin column wired to `p70_latency_ms` variable; later finding latency-as-boolean type mismatch | RESOLVED in v21 (3 required:true flips landed); column type fixed via Phase C C-T1 (drop bool, add int4) — but the underlying HR var doesn't populate (NULL forever per ADR-012) | was MEDIUM | reference 2026-04-28, v21 audit | Dashboard computes from transcript |
| F9 — `book_load` tool name trailing space | OPEN VERIFY | POLISH | `project_hr_review_later_inventory.md` item 7, `project_phase_b_complete_audit_2026_04_28.md` D2 | should have been Phase A1 Edit 7 — verify done |
| F10 — 28 languages enabled | LOCKED-KEEP (intentionally NOT narrowed) | n/a | `project_keep_all_languages.md` | user direction 2026-04-28 |
| F11 — FMCSA API key in plaintext URL | OPEN MEDIUM (user-claimed-fixed 2026-04-30, awaiting verification) | OPEN MEDIUM | `project_hr_audit_2026_04_30_findings.md` | apiKey field cleared per user fix-pass 2; HR-AI verify round 2 pending |
| F12 — Real-time `Call Outcome` classifier `classes:[]` empty | RESOLVED via removal (Phase C v2 C-T2.7 LOCKED REMOVE) | was MEDIUM | same | verify deletion landed |
| F13 — Single-load lookup broken (load_id filter missing on Get Load Details) | RESOLVED Phase C C5.3 | was MEDIUM | same | filter added |
| F14 — `verify_carrier.mc_number.required=null`, `negotiate_rate.loadboard_rate.required=null`, `negotiate_rate.pickup_datetime.required=null` | RESOLVED in v21 (3 required:true flips landed) | OPEN HIGH originally | same | VERIFIED-CLOSED v21 |
| F15 — "Case Healt Score" typo in node title | OPEN POLISH | POLISH | same | Phase C v2 C-T2.8 — 30-second rename |
| F16 — Log Event chip missing 3 bindings (`hangup_reason`, `room_name`, `status`) | RESOLVED VIA DROP (cols dropped in v2 schema cleanup; user-claimed-fixed via DDL ALTERs) — verify which path landed | OPEN MEDIUM (user claims fixed) | same | HR-AI verify round 2 pending |
| F17 — `node_timings_json` column with empty literal value | RESOLVED via removal in v2 cleanup | was LOW | same | VERIFIED-CLOSED v21 |
| F18 — Misread on first audit pass; second pass confirms `extract_output_tokens` correctly bound | RETRACTED | n/a | same | no action |
| F19 — `callback_phone` semantics (Voice Agent.from vs from_number) | RESOLVED — doc drift, "web" for web-call is EXPECTED | was LOW | `reference_twin_calls_log_field_semantics.md` | doc updated |
| F20 / F21 — call_id alignment: webhook vs Twin (run_id wins, used by 2/3 sites) | OPEN MEDIUM (user-claimed-fixed 2026-04-30, awaiting verification) | OPEN MEDIUM | `project_hr_audit_2026_04_30_findings.md` | webhook call_id rebound to current.run_id per user fix-pass 2 |
| F22 — `intermediate_response_count` doc references obsolete variable name | RESOLVED — doc drift | was LOW | same | doc updated |
| F23 — same as F11/F23 (renamed) | OPEN MEDIUM (see F11) | OPEN MEDIUM | same | bundled with F11 fix |
| F24 — (no record found in audit) | n/a | — | — | placeholder |
| F25 — `<calendar_context>` prompt section reads "Today's local time, [blank]" — no time variable injected | OPEN — DEFERRED 2026-04-30 night, NOW ACTIVE per audit (see §6) | OPEN LOW | same | user direction "we will fix time later" — now resumed |

**Summary by status:**
- RESOLVED: F1, F2, F3, F4, F5, F6 (partial), F7, F8 (column type fixed; HR var NULL-forever accepted), F12, F13, F14, F17, F19, F22; F18 RETRACTED
- OPEN VERIFY (user-claimed-fixed, awaiting HR-AI re-verify): F11/F23, F16, F20/F21
- OPEN unresolved: F9 (verify), F15 (cosmetic), F25 (now ACTIVE per §6)
- LOCKED-KEEP (intentionally not changed): F10

---

## 8. Twin-side production lock-in (for context)

Quoted from `memory/project_twin_production_lock_in.md`:

> HR Twin as the canonical store creates 4 production lock-in problems:
> 1. **SPOF on `HAPPYROBOT_API_KEY`** — if revoked, dashboard 502s.
> 2. **Cross-org coupling** — Twin tables live in Andres's HR org. A real customer (Acme Logistics) cannot run a copy of this without their OWN HR org + their OWN Twin tables + their OWN API key.
> 3. **Cloudflare WAF restricts legitimate queries** — no IN-lists, no ORDER BY+LIMIT, no multi-aggregate. We aggregate in Python.
> 4. **No SLA, no psql, no migrations tooling, no backup control** — all out of our hands.

**Why we kept Twin anyway** (Route B, locked 2026-04-25 in master plan): zero infra to provision; native HR Workflow Dump / Write-to-Twin chips; reduced attack surface (no public POST endpoints); ADR-005 two-table booking pattern works; spec-compliant ("API in a file or DB").

**Production migration path** (Tier-2 roadmap, ADR-013): Route A from master plan = Fly managed Postgres + HR pushes via webhook → FastAPI → our Postgres. Removes `HAPPYROBOT_API_KEY` from dashboard read path. ~6-8hr Claude work. NOT in current sprint.

**Tier triggers (when to escape):**
- Tier 2 (~$50-100/mo): HR Twin SLA gap >0.5% downtime/mo, OR cross-org WAF blocking critical queries, OR data retention >90 days needed.
- Tier 3 (~$500-2000/mo): >100k calls/mo sustained, OR multi-tenancy live, OR analytics queries exceed 5s p95.

**Why everything in this register sits behind that ceiling:** every Twin schema change in §3 is a workaround on a take-home-grade store. None of them survive a Postgres migration unchanged — `notes` column, load-status lifecycle, carrier_aggregates, tool_calls timeline all need to be re-applied on the Postgres side. Field renames (TR-1, TR-2) become moot on Postgres because we'd choose canonical names from the start.

---

## 9. What to do NEXT — priority list (top 5)

Ranked by impact / urgency / blocking-demo:

1. **VP-8 + T-1 + RP-1 + WV-1 — Time-handling fix (§6)**
   - **Rationale:** BLOCKING for production demo. Affects every call's correctness. Carriers WILL ask "what time is it?" and agent currently hallucinates. Fix is fully authored — paste-ready in memory.
   - **Acceptance criterion:** test web call asking "what time is it?" — agent calls `get_current_time` and speaks `spoken_clock_eastern` ("four thirty five P M Eastern Daylight Time") cleanly, not digit-by-digit, not in 24-hour format, not as ISO string.

2. **F11 / F23 + F20 / F21 + F16 verification (§7)**
   - **Rationale:** User claimed-fixed all three on 2026-04-30 night but HR-AI verification round 2 has not run. Three OPEN-VERIFY items block sign-off on Phase C v2 closeout.
   - **Acceptance criterion:** HR-AI re-audit confirms apiKey field empty, webhook call_id binds to `current.run_id`, and the F16 path (drop or bind) landed cleanly in Twin.

3. **F9 + F15 cosmetic cleanup (§7)**
   - **Rationale:** Trivial polish — `book_load ` trailing space + "Case Healt Score" typo. ~30 seconds each. Reviewer-visible quality signal.
   - **Acceptance criterion:** Tool name = "book_load" (no trailing space); CHS node label = "Case Health Score".

4. **VP-1..VP-5 + EX-1 + EX-2 + VP-6 + Log Event chip mappings (§4.1, §4.4)**
   - **Rationale:** Phase C v2 C-T2.2 (`notes` pipeline) + C-T2.3 (F7 six-column extension) + C-T2.10 (5 prompt patches) all bundle into one HR UI session. v15 first-pass findings flag clarification-loop hell + wide-search defaults + no recap as recurrent agent failures.
   - **Acceptance criterion:** test call where carrier names lane + offers callback phone — calls_log row populates `notes`, `carrier_name`, `lane_origin`, `lane_dest` non-NULL; agent doesn't ask same slot 3+ times; agent recaps 6-tuple before transfer.

5. **Phase C v2 column-reorder verification + dropped-column verification (CL-1, CL-2, CL-3)**
   - **Rationale:** `data/twin_schema_calls_log.sql` describes 29 cols with `node_timings_json`, `hangup_reason`, `room_name`, `status` DROPPED. HR architecture map describes some of these as "PENDING" or wired-then-dropped. Verify Twin live shape matches the canonical schema file before publishing v22+.
   - **Acceptance criterion:** `SELECT * FROM calls_log LIMIT 1` returns exactly 29 columns in the order documented in the SQL file header.

---

## 10. Confidence + gaps

### 10.1 Where I had to interpret

- **Live workflow version.** HR architecture map says v19 latest published; `project_hr_audit_2026_04_30_findings.md` describes a v21 audit (workflow `c22clmeecc87`) with two-pass results. `project_phase_c_in_progress_resume.md` says v20-phase-c forked from v19. I treat **v20+ → v21** as the workflow that received the Phase C edits, and **v22 / v23** as the next fork once the time-handling fix lands. The architecture map is dated 2026-04-30 and labels itself "INTERIM"; the v21 audit is also 2026-04-30 night. There may be a v22 sitting on disk somewhere I didn't see.

- **`loads` table column count.** `data/twin_schema_loads.sql` says 15 cols; `docs/hr-architecture-map.md:152` says "Schema (18 cols): id, created_at, reference_number, ..." — but `reference_number` was renamed to `load_id` per `reference_loads_table_column_load_id.md`, AND the SQL file uses `load_id` as PK. The architecture map's "18 cols" + `id, created_at, reference_number, ..., posted_at` is OUT OF SYNC with the canonical SQL file. Treat the SQL file as ground truth pending live Twin probe.

- **Phase C v2 32-col target vs canonical 29-col live.** Phase C v2 plan locked a 32-col target with `hangup_reason / room_name / status / node_timings_json` included. The canonical `data/twin_schema_calls_log.sql` says these were DROPPED (cosmetic, reserved-then-dropped + redundant per ADR-012). Either the schema file was updated AFTER Phase C v2 ran and the v2 plan is now stale, OR the v2 plan ran but the DROP statements were applied later. Live Twin probe is the only way to disambiguate.

- **F8 status.** Multiple sources disagree: `reference_hr_architectural_review_2026_04_28.md` calls F8 a wiring bug (p90 wired to p70 var); `project_hr_audit_2026_04_30_findings.md` reframes F8 as "latency-as-boolean type mismatch" (DDL added boolean cols `p70/p90_intermediate_fired`); `project_dashboard_latency_compute_locked.md` says HR var binding broken even after F8 fix (NULL forever). All three are the same column-drift saga — I treated the latency-as-boolean DDL fix as RESOLVED + the NULL-forever HR var as a platform limitation per ADR-012.

- **Field renames closure.** `project_field_renames_pending.md` is dated 2026-04-27. Phase C v2 says "Tier 3 — N/A AT v2 LOCK" because `bookings.apply_rate` is already correct and `calls_log.pitched_loadboard_rate` / `agreed_rate` were dropped in v15 cleanup. The memory file is technically still OPEN per its own contents but functionally CLOSED. Marked DEFERRED with the suggestion to close the memory file post-v22 publish.

### 10.2 Conflicts between memory files

- **Dashboard HTML vs Next.js.** `project_dashboard_html_decision.md` LOCKED HTML on 2026-04-28 then `project_dashboard_nextjs_committed.md` REVERSED it the same day. Latest position per `docs/hr-architecture-map.md:227-244` and `feedback_full_recall_discipline.md`: Next.js is production deliverable, HTML retained as fallback. Not in scope of this register but flagged for completeness — neither is HR or Twin work.

- **Calls_log column count.** `reference_twin_calls_log_field_semantics.md` (2026-04-30) says 15 cols. `data/twin_schema_calls_log.sql` (canonical) says 29 cols. The 15-col file represents an INTERIM v15 shape from before Phase C v2's 14-column expansion landed (notes, lane_origin, lane_dest, carrier_name, 10 token cols). The 29-col SQL file is the latest canonical. Memory file is stale.

- **Workflow version naming.** `docs/hr-architecture-map.md` says v19 latest published. README per `project_phase_b_complete_audit_2026_04_28.md` D17 says "v4". Both can be true (different docs, different timeframes) but it's reviewer-confusing — `project_phase_b_complete_audit_2026_04_28.md` D16 already flags README rewrite as critical-path. NOT this register's problem but flagged for context.

- **`book_load.original_rate` deferred.** `project_post_mvp_field_design_research.md` recommends rebinding `pitched_loadboard_rate` from Twin row not Extract; `docs/hr-phase-c-action-plan-v2.md` Tier-3 says add `original_rate` to bookings as a v16 enhancement; `project_v14_loop_architecture.md` says it was deliberately NOT added in v15 (lean-design). Three slightly-different framings of the same defer. Captured under TS-5.

- **Phase C v2 `hangup_reason / room_name / status` columns.** Plan said add them (32-col target); schema file says drop them (29-col canonical). Resolution needs live Twin probe — see §10.1 third bullet.

### 10.3 Items NOT covered in scope but worth flagging

- Carlos email artifacts checklist (`project_carlos_email_artifacts.md`) — pre-submission blockers (Next.js deploy, docker-compose.yml, GitHub push, Loom, fresh web-call URL for v19+, scoped API_BEARER_TOKEN). Not HR or Twin work but on the same critical path as Phase C v2 closeout.

- Production lock-in escape hatch (Postgres migration) — Tier-2 roadmap. ~6-8 hr Claude work. Triggers documented in §8.

- Master plan §1502 supersede banner needed (deprecated endpoints `/v1/fmcsa/verify`, `/v1/negotiate/evaluate`, `POST /v1/calls/log`). Not HR or Twin but linked to the architecture map's drift-cleanup posture.

---

## 11. Comprehensive deferred-items index

Cross-referenced flat list. Every item either OPEN or DEFERRED, sorted by effort × severity for sequencing.

### 11.1 Quick wins (S effort, OPEN)

| Item | Section | Severity | Estimated time |
|---|---|---|---|
| F15 typo "Case Healt Score" → "Case Health Score" | §2.E CH-1 | POLISH | ~30 sec |
| F9 verify `book_load` trailing space removed | §2.B T-3 | POLISH | ~30 sec |
| RT-1 verify F12 classifier deletion landed | §2.F | OPEN MEDIUM | ~1 min |
| F11/F23 verify apiKey field cleared | §7 (T-4) | OPEN MEDIUM | ~30 sec verify |
| F20/F21 verify webhook call_id rebound to current.run_id | §7 | OPEN MEDIUM | ~30 sec verify |
| F16 verify which path landed (drop vs bind) | §4.6 | OPEN MEDIUM | ~30 sec verify |
| WV-2 verify `time.now_america_new_york.iso` is NOT used anywhere | §2.G | OPEN VERIFY | ~2 min grep |
| RP-2 verify `calculate_rate` retained `now`/`now_iso` dual-key fix on v20+ | §2.C | RESOLVED, verify | ~1 min |
| EX-3 verify Extract strict-mode hygiene retained | §2.D | RESOLVED, verify | ~1 min |
| CL-1 / CL-2 / CL-3 verify Twin live shape matches canonical 29-col SQL | §3.E | OPEN VERIFY | ~2 min |
| DR-1 / DR-2 verify 150 loads still future-dated pre-demo | §3.C | DONE-VERIFY | ~2 min |

### 11.2 Active fixes (M effort, BLOCKING)

| Item | Section | Severity | Estimated time |
|---|---|---|---|
| Time-handling complete fix (4 prompt edits + 1 tool + 1 sidecar + fork) | §6 | BLOCKING | ~30-45 min user-time |
| F14 — 3 required:true flips on tool params | §2.B T-2 | OPEN HIGH | ~2 min (already RESOLVED v21 per audit; verify) |

### 11.3 Phase C v2 paste pass (M effort, IMPORTANT — bundle into one HR session)

| Item | Section | Severity | Estimated time |
|---|---|---|---|
| EX-1 — Add `notes` Extract field | §2.D, §4.1 | IMPORTANT | ~3 min |
| EX-2 — Add `carrier_name`, `lane_origin`, `lane_dest` Extract fields | §2.D, §4.4 | IMPORTANT | ~5 min |
| VP-1..VP-5 — 5 prompt patches | §2.A | IMPORTANT | ~10 min |
| VP-6 — `<call_notes>` section | §2.A, §4.1 | IMPORTANT | ~3 min |
| Log Event chip — bind `notes`, `carrier_name`, `lane_origin`, `lane_dest` from @ picker | §4.1, §4.4 | IMPORTANT | ~5 min |
| NS-1 — Define Northstars (2 measurable + 3 behavioral) | §2.I | POLISH | ~5 min |

### 11.4 Tier-2 production features (DEFERRED)

| Item | Section | Severity | Effort | Trigger |
|---|---|---|---|---|
| Load-status lifecycle (Twin DDL + book_load update + query_loads filter + cron) | §4.2 | DEFERRED | M-L | Real-prod traffic / multi-carrier collisions |
| Postgres migration (Tier-2 escape from HR Twin) | §8 | DEFERRED | L (~6-8 hr) | SLA gap / cross-org / 100k+ calls/mo |
| Cancellation flow + `cancel_booking` tool | §2.B T-6 | DEFERRED | M | Post-MVP |
| `bookings.original_rate` for pitched-vs-applied delta | §3.A TS-5 | DEFERRED | M | v16 enhancement |
| Carrier aggregates table | §3.A TS-3 | DEFERRED | M | Dashboard performance gate |
| Tool-call timeline table | §3.A TS-4 | DEFERRED | M | Drilldown UX requires it |
| Real-time negotiation hook (HR webhook + SSE + sales-rep dashboard) | §4.5 | DEFERRED | M | Sales-rep operational view ships |
| Reusable Prompt Component | §2.I NS-2 | DEFERRED | M | Multi-workflow scaling |
| Adversarial test suite activation | §2.I NS-3 | DEFERRED | M | Pre-production publish gate |
| Custom evals (regression tests on prompt changes) | §2.I NS-4 | DEFERRED | M | Ongoing prompt iteration |
| Super-test workflow (cheap-LLM substrate, 10 edge tests/node) | §2.I NS-5 | DEFERRED | L (~10-20 hr) | Production publish gate |
| Workflow-level monitoring webhook | `project_hr_review_later_inventory.md` item 5 | DEFERRED | S | External observability needs |
| FMCSA wrapper (caching proxy) | `project_fmcsa_key_provided.md` | DEFERRED | M | Tier-2 broker-doc narrative |

### 11.5 Tier-2 dashboard / analytics (DEFERRED — for HR/Twin context only; not register-scope work)

These items are listed in `project_hr_review_later_inventory.md` items 20-25 but only the HR-side / Twin-side halves are register-relevant:

| Item | HR/Twin half | Source |
|---|---|---|
| Per-carrier drilldown view | none — pure dashboard | `project_dashboard_hr_twin_dependencies.md` |
| Real-time call monitor | requires WH-4 (negotiation webhook) + `Send Webhook` action child | `project_realtime_negotiation_hook.md` |
| CSV export per tab | none — pure dashboard | review-later inventory |
| Anomaly alerts | optional HR webhook → external alerting | review-later inventory |
| Outcome trend lines + forecasting | none — pure dashboard | review-later inventory |
| Load utilization rate | depends on §4.2 load-status lifecycle | review-later inventory |

### 11.6 Post-MVP field design rigor (DEFERRED — research-mode work)

Listed in `project_post_mvp_field_design_research.md` — runs as 4-sub-agent goliath:

1. `audit_remarks` — predefined enum + "other" fallback
2. `fmcsa_eligibility_failure_reason` — enum from FMCSA codes (`MC_NOT_FOUND`, `NOT_AUTHORIZED`, `INACTIVE`, `REVOKED`, etc.)
3. `booking_decision` — drop entirely (call_outcome covers it) OR align with industry tender lifecycle
4. `pitched_loadboard_rate` — rebind from Twin row not Extract
5. `agreed_rate` — capture via terminal tool call (`finalize_call`-style) for explicit structured emission
6. `call_outcome` enum — research industry vocabularies (TMS, TIA, DAT)
7. `sentiment` — pair with Case Health Score 0-100 + sentiment_start / sentiment_end / sentiment_trajectory

Plus per `feedback_track_requirements.md`: maintain ongoing requirements registry across multi-turn requirement-gathering.

### 11.7 In-flight items (current sprint, not deferred)

| Item | Status | Source |
|---|---|---|
| v5.1 prompt → HR paste | SHIPPED ✓ + user has applied v5.2 edits on top inside HR (not all captured in repo) | `project_v5_rlhf_tuning_in_flight.md`, `docs/hr-architecture-map.md:69-70` |
| Phase C v2 plan execution | PARTIAL — C0-C5.3 done, C5.2 paused mid-flow, C5.4 not done | `project_phase_c_in_progress_resume.md` |
| HR audit v21 closeout | OPEN VERIFY — F11/F23, F16, F20/F21 user-claimed-fixed, awaiting HR-AI re-verify round 2 | `project_hr_audit_2026_04_30_findings.md` |
| Time-handling fix | RESUMED 2026-04-30 night, paste-ready in memory | §6, `project_time_handling_critical_deferred.md` |

---

## 12. Source-file index

Every claim in this register cites one of:

**Memory files (read in full)**:
- `project_callback_audit_field.md` — `notes` column rollout (column name LOCKED 2026-04-30)
- `project_call_loads_attribution_review.md` — calls_log.load_id redundancy review-trigger
- `project_chs_deduction_model.md` — CHS architecture (LLM-driven, single node, 4 fields, deduction tiers, threshold ≥70)
- `project_dashboard_hr_twin_dependencies.md` — every dashboard improvement tagged dashboard / HR / Twin
- `project_field_renames_pending.md` — pitched_loadboard_rate / agreed_rate renames (deferred)
- `project_fmcsa_key_provided.md` — FMCSA web key is take-home credential, not a Tier-2 acquisition step
- `project_goliath_analytics_answers.md` — q1=B, q2=C, q3=A, q4=B, q5=A; goliath postponed pending Twin search fix
- `project_hr_audit_2026_04_30_findings.md` — v21 audit catalog F1-F25
- `project_hr_review_later_inventory.md` — 35-item canonical review-later register
- `project_load_booked_status_lifecycle.md` — Tier-2 production feature
- `project_loads_dummy_data_refresh.md` — 100-500 future-dated rows (DONE 2026-04-28; re-verify pre-demo)
- `project_phase3_calls_log_v2.md` — 24 MVP cols + 7 Tier-2 (historical hypothesis under audit)
- `project_post_mvp_field_design_research.md` — 4-sub-agent goliath plan + 13 specific issues
- `project_realtime_negotiation_hook.md` — DEFERRED webhook + SSE counter offer + final_floor visibility
- `project_sales_dashboard_view.md` — sales-rep persona view + dummy mimic-accept (no backend)
- `project_super_test_workflow.md` — 80-base-tests + 10 live HR calls harness (DEFERRED)
- `project_telemetry_widgets_locked.md` — RPM/TPM/percentile direction + Voice Agent BIG widget
- `project_test_scenarios_phase2.md` — 10 lane-search variants for agent reasoning
- `project_time_handling_critical_deferred.md` — full time-handling fix architecture (paste-ready)
- `project_twin_data_reaudit.md` — full per-column scorecard after 5-10 real test calls
- `project_twin_production_lock_in.md` — 4 production lock-in problems + Postgres migration roadmap
- `project_v14_loop_architecture.md` — multi-load architecture (Loop + Extract array + denormalized CHS)
- `project_v15_e2e_first_pass_findings.md` — VP-1..VP-5 backlog + behavioral issues
- `reference_calls_log_transcript_shape.md` — JSON array role/content turns including role=tool; no per-turn timestamps
- `reference_hr_architectural_review_2026_04_28.md` — F1-F11 catalog (v17 audit)
- `reference_hr_create_popup_schema.md` — Transfer Popup full schema (14 fields, MVP minimum)
- `reference_hr_extract_strict_schema_rules.md` — Azure structured-output strict-mode rules
- `reference_hr_extract_test_node_sandbox.md` — Test Node "room name required" sandbox-only error
- `reference_hr_fork_corruption.md` — API mutation corruption propagation through forks
- `reference_hr_import_breaks_references.md` — `call.static.id` is the one field HR's importer misses
- `reference_hr_model_registry.md` — `model.static.id` internal id, not display name
- `reference_hr_post_batch_corruption.md` — POST batch additions corrupt voice (UI-only rule)
- `reference_hr_post_call_webhook_schema.md` — Version 3's 48-field POST schema (cheatsheet)
- `reference_hr_procedural_quirks.md` — @ picker, Twin SQL, webhook patterns, REST API endpoints
- `reference_hr_python_sandbox_restrictions.md` — RestrictedPython rules (no dunder, no leading underscore, no networking)
- `reference_hr_run_python_node_ui.md` — 3 fields: Event Name + Input Data repeater + Code
- `reference_hr_time_data_inventory.md` — verified UTC sources + DST-bug flags
- `reference_hr_transcript_access_paths.md` — 3 paths: async CSV, MCP get_transcript, in-workflow @ picker
- `reference_hr_twin_empty_string_filter.md` — `equals` is literal string comparison
- `reference_hr_workflow_schema_population.md` — fresh workflows have greyed @ picker forever
- `reference_loads_table_column_load_id.md` — column is `load_id` not `reference_number`
- `reference_twin_calls_log_field_semantics.md` — calls_log column semantics + bindings
- `reference_cloudflare_waf_twin.md` — WAF blocks information_schema, ORDER BY+LIMIT, multi-aggregate, IN-lists, UNION
- `reference_adr_013_operational_analytical.md` — ADR-013 at-a-glance (operational vs analytical store)

**Repo SQL** (canonical Twin schemas):
- `data/twin_schema_loads.sql` — 15 cols + 2 indexes (PK is `load_id`)
- `data/twin_schema_calls_log.sql` — 29 cols (canonical v2) + UNIQUE + 3 indexes
- `data/twin_schema_v15_bookings.sql` — 6 cols + UNIQUE(call_id, load_id) + 4 indexes
- `data/twin_schema_v15_calls_log_cleanup.sql` — drops 7 columns (load_id, apply_rate, is_booking, booking_seq, num_negotiation_rounds, etc.) before bookings split

**Repo HR-tools / scripts**:
- `scripts/hr-tools/calculate_rate.py` — Run Python sidecar for `negotiate_rate` (reads `now` and `now_iso`)
- `scripts/hr-tools/case_health_score.py` — sandbox-safe deduction-model implementation (reference; v15+ uses single LLM-driven CHS node, this script is reference-only per `project_chs_deduction_model.md`)
- `scripts/hr-tools/apply_demo_adjustment.py` — historical demo adjustment

**Architecture map**:
- `docs/hr-architecture-map.md` — v19 interim snapshot, several upgrades pending; canonical "what's actually wired"

**Phase C action plans**:
- `docs/hr-phase-c-action-plan.md` — v1, superseded by v2
- `docs/hr-phase-c-action-plan-v2.md` — final canonical plan; covers `notes` Tier-1 promotion + 32-col reorder + F12 removal + F15 typo + Path B-1 (deferred per ADR-012) + VP-1..VP-5 + Northstars + bookings rename N/A

**Voice / extraction prompts**:
- `docs/references/happyrobot/voice-agent-prompt.md` — in-call system prompt (v4.x reference; live HR is v5.1+v5.2 edits)
- `docs/references/happyrobot/post-call-extraction-prompt.md` — historical 48-field schema; live v15+ uses 2-field Extract + 3-field CHS

**Activity log**:
- `docs/activity-log.md` — running journal; ADR-013 lock 2026-04-30 referenced from §8

---

**End of register.**

Audit boundary: this register is point-in-time as of 2026-04-30. Live Twin probe + HR-AI verification round 2 should run before treating any "OPEN VERIFY" item as either RESOLVED or genuinely OPEN. Memory files are mostly 2-3 days old (per system-reminders) and may have drifted from current code/schema; verify against `data/twin_schema_calls_log.sql` and `docs/hr-architecture-map.md` as ground truth where available.
