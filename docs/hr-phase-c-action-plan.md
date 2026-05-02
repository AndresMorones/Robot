# HR Phase C — full action plan

Comprehensive HR-side work to land BEFORE the dashboard widget build kicks off. Organized by priority tier. Each item: what it fixes, where in HR UI, click-by-click, verify step, time estimate.

**Total estimated user-time:** ~60-90 min if done in one session; can be split.

**Workflow:** `inbound-carrier-sales-new`, latest version (currently v19 dev → fork to v20 if any node changes are needed; voice-config changes ALWAYS require a fork per `reference_hr_post_batch_corruption.md`).

**Important rule:** Do NOT use the HR API to mutate workflow nodes. UI only. (HR API mutations on voice workflows leave invisible corruption per `reference_hr_fork_corruption.md`.)

---

## Tier 1 — BLOCKING (must fix before next live test calls)

### T1.1 — F2 dedup: Voice Agent Prompt body duplication
**Impact:** ~50% reduction in voice-agent input tokens on every call. Highest cost lever in the entire workflow.

**Steps:**
1. Open the workflow editor → click the **Prompt** node (the big one with the system prompt).
2. Scroll the prompt body. You'll see `<role_and_objective>` appear twice — once near the top, once again roughly halfway down.
3. Select the SECOND occurrence (from the second `<role_and_objective>` to the end of its duplicate `<closing_reminders>`) and DELETE it.
4. Save.

**Verify:** Search the prompt body for `<role_and_objective>` — should appear exactly once. Run a dry test call; observe the next CHS extract's `Llm Usage Input Tokens` should drop ~50%.

**Time:** ~5 min.

---

### T1.2 — F4 required flags on book_load
**Impact:** LLM may currently omit `mc_number` or `apply_rate` on tool call. Forces explicit values.

**Steps:**
1. Click the **book_load** tool node.
2. In the parameters panel, find `mc_number` row → toggle **Required** to `true`.
3. Find `apply_rate` row → toggle **Required** to `true`.
4. Confirm `load_id` is already `Required: true` (it is — leave alone).
5. Save.

**Verify:** Click the tool params; all three (load_id, mc_number, apply_rate) show Required ✓.

**Time:** ~2 min.

---

### T1.3 — F3 calculate_rate `now` vs `now_iso` mismatch
**Impact:** Currently silently falling through to `datetime.datetime.now()` (server UTC), causing timezone drift on urgency-tier boundaries.

**Steps (pick ONE — they're equivalent):**
- **Option A (preferred — change the input_data key):**
  1. Click **calculate_rate** Run Python node.
  2. In the **Input Data** repeater, find the row with key `now_iso` (value bound to `time.now_america_new_york`).
  3. Rename the key from `now_iso` to `now`.
  4. Save.
- **Option B (change the Code body):**
  1. Click **calculate_rate** node.
  2. In the **Code** field, find the line `now_str = inp.get("now")`.
  3. Change to `now_str = inp.get("now_iso")`.
  4. Save.

**Verify:** Test the node with a sample input where `now_iso` (or `now`, depending on option) has an ISO string. The output's `urgency_tier` should match the actual hours-until-pickup.

**Time:** ~3 min.

---

### T1.4 — F11 FMCSA webKey out of plaintext URL
**Impact:** Security finding. The webKey `cdc33e44...` is currently visible in any workflow read.

**Steps:**
1. **First, in HR Settings → Credentials:** create a new credential named `fmcsa_webkey` of type "Header" → header name `X-Web-Key`, value `cdc33e44d693a3a58451898d4ec9df862c65b954`. (Or use whatever credential type HR offers — header is what the FMCSA API actually needs but we're keeping URL semantics for now; if HR has only "URL parameter" type credentials, use that with key `webKey`.)
2. Open workflow editor → click **GET MC Number** webhook node (child of `verify_carrier`).
3. Change the URL from `...?webKey=cdc33e44...` to just `...` (drop the query string entirely if using header credential, or to `?webKey={{credential.fmcsa_webkey}}` if using URL-parameter credential).
4. In the **Auth** or **Credentials** section of the webhook, attach the `fmcsa_webkey` credential.
5. Save.

**Verify:** Test the webhook with a known-valid MC. Should return the same FMCSA payload as before. Workflow JSON read no longer shows the key in plaintext.

**Time:** ~8 min.

---

## Tier 2 — IMPORTANT (improves data quality + unlocks telemetry)

### T2.1 — F8 latency type fix
**Impact:** Currently `p70_latency_ms` numeric → wired to `p70_intermediate_fired` BOOLEAN column. Latency value is silently truthified; we lose the actual ms value.

**Steps:**
1. **Twin DDL first** (Twin SQL editor, single-statement each):
   ```sql
   ALTER TABLE calls_log DROP COLUMN p70_intermediate_fired;
   ```
   ```sql
   ALTER TABLE calls_log DROP COLUMN p90_intermediate_fired;
   ```
   ```sql
   ALTER TABLE calls_log ADD COLUMN p70_latency_ms INTEGER;
   ```
   ```sql
   ALTER TABLE calls_log ADD COLUMN p90_latency_ms INTEGER;
   ```
2. Open workflow → click **Log Event** Write-to-Twin chip.
3. Find the existing `p70_intermediate_fired` mapping → DELETE the row (the column no longer exists).
4. Find the existing `p90_intermediate_fired` mapping → DELETE the row.
5. Click **+ Add column** → column `p70_latency_ms`, type `int4`, value via @ picker → search "p70" → click `<Voice Agent>.p70_latency_ms`.
6. Click **+ Add column** → column `p90_latency_ms`, type `int4`, value via @ picker → search "p90" → click `<Voice Agent>.p90_latency_ms`.
7. Save.

**Verify:** Make a test call. After it ends, verify `calls_log.p70_latency_ms` has a numeric value (not boolean).

**Time:** ~6 min.

---

### T2.2 — Bind 10 token columns (Extract + CHS)
**Impact:** Populates the columns we already added. Powers the Token-usage widgets on the Pit Telemetry tab.

**Steps:**
1. Click **Log Event** Write-to-Twin chip.
2. Click **+ Add column** ten times. For each:

| # | Column | Type | @ picker source |
|---|---|---|---|
| 1 | `extract_input_tokens` | int4 | Extract Call Details → Llm Usage Input Tokens |
| 2 | `extract_output_tokens` | int4 | Extract Call Details → Llm Usage Output Tokens |
| 3 | `extract_reasoning_tokens` | int4 | Extract Call Details → Llm Usage Reasoning Tokens |
| 4 | `extract_cached_input_tokens` | int4 | Extract Call Details → Llm Usage Cached Input Tokens |
| 5 | `extract_uncached_input_tokens` | int4 | Extract Call Details → Llm Usage Uncached Input Tokens |
| 6 | `chs_input_tokens` | int4 | Case Healt Score → Llm Usage Input Tokens |
| 7 | `chs_output_tokens` | int4 | Case Healt Score → Llm Usage Output Tokens |
| 8 | `chs_reasoning_tokens` | int4 | Case Healt Score → Llm Usage Reasoning Tokens |
| 9 | `chs_cached_input_tokens` | int4 | Case Healt Score → Llm Usage Cached Input Tokens |
| 10 | `chs_uncached_input_tokens` | int4 | Case Healt Score → Llm Usage Uncached Input Tokens |

3. Save.

**Verify:** Make a test call. After post-call extracts run, verify all 10 columns populate with non-NULL values.

**Time:** ~5 min.

---

### T2.3 — Bind 6 missing F7 calls_log columns
**Impact:** Closes the audit's F7 gap. These columns exist in `calls_log` but currently get NULL on every write because they're not mapped.

**Steps (still in Log Event Write-to-Twin chip):**
1. Click **+ Add column** six times. For each:

| # | Column | Type | @ picker source |
|---|---|---|---|
| 1 | `carrier_name` | text | Extract Call Details → response.carrier_name (add to Extract params first if not present) |
| 2 | `lane_origin` | text | Extract Call Details → response.lane_origin |
| 3 | `lane_dest` | text | Extract Call Details → response.lane_dest |
| 4 | `hangup_reason` | text | Analyze Incoming Conversation → call_end_event |
| 5 | `room_name` | text | Analyze Incoming Conversation → room_name |
| 6 | `status` | text | Analyze Incoming Conversation → status |

2. **Note:** if `response.carrier_name`, `response.lane_origin`, `response.lane_dest` aren't in the Extract Call Details parameters list, ADD them first via the Extract node's parameter editor (with a JSON Schema entry for each), then come back and bind.
3. Save.

**Verify:** Make a test call where the carrier names a lane. After post-call, verify `lane_origin`, `lane_dest`, `carrier_name` populate.

**Time:** ~10 min (the params extension is the slowest step).

---

### T2.4 — F13 single-load lookup fix
**Impact:** Currently `query_loads(load_id="LOAD-0188")` returns lane-filtered results, ignoring the load_id. Single-load lookup mode is broken.

**Steps:**
1. Click **Get Load Details** Twin Read node (child of `query_loads`).
2. In the **Filters** panel, click **+ Add filter**.
3. Configure: column `load_id`, operator `equals`, value via @ picker → `query_loads → load_id`.
4. Save.

**Verify:** Test the tool with `load_id="LOAD-0042"` (and lane filters empty). Should return exactly that load row, or empty if it doesn't exist.

**Time:** ~3 min.

---

## Tier 3 — NICE-TO-HAVE (polish, can defer)

### T3.1 — F12 classifier classes
The real-time `Call Outcome` classifier has `classes: []`. Either:
- Populate the classes list with the 5 enum values (load_booked / no_match / carrier_not_qualified / call_abandoned / rate_disagreement).
- OR delete the classifier entirely if not used downstream.
**Time:** ~3 min. Decide based on whether the dashboard will use real-time classifier output.

### T3.2 — HR-1 `notes` column
Already covered in `project_callback_audit_field.md`. Add 1 Twin column + 1 Extract param + 1 prompt section + 1 Write-to-Twin binding. **Time:** ~10 min.

### T3.3 — Path B-1 node-timing Run Python node (timestamp source for telemetry)
Per `project_telemetry_widgets_locked.md` — adds a Run Python node post-call that captures all upstream node start/end times into a JSON blob, written to a new `node_timings_json TEXT` column. Unlocks per-tool latency p50/p99 dashboard-side. **Time:** ~15 min (DDL + node add + Code body + binding).

### T3.4 — VP-1..VP-5 voice prompt patches
Per `project_v15_e2e_first_pass_findings.md` + the question set you locked earlier:
- VP-1: clarification-loop cap — never re-ask same slot more than once
- VP-2: narrowing rule — narrow only when <2 dimensions specified
- VP-3: recap-before-transfer strict 6-tuple
- VP-4: no-retry on FMCSA decline (one mishear retry, then end)
- VP-5: intent-language negotiation phrasing with alternative-first
**Time:** ~10 min total (paste 5 short patches into the Prompt node).

### T3.5 — Northstars on Prompt node
Define 2 measurable + 3 behavioral northstars per locked instinct on Q7. Drops into the Prompt node's Northstar slot if HR exposes one; otherwise into a `<northstars>` section in the prompt body. **Time:** ~5 min.

### T3.6 — Cosmetic
- F14: `verify_carrier` + `negotiate_rate` parameters all `required: null` → set to `true` for required ones, `false` for optional. ~3 min.
- F15: rename "Case Healt Score" → "Case Health Score" in the AI Extract node title. ~30 sec.

---

## Suggested order for one HR session

If you want to do all of Tier 1 + Tier 2 in one session (~45-60 min):

1. **First** — fork the workflow to v20 (right-click latest version → "Fork" → name "v20-phase-c").
2. **Tier 1.4 (F11 webKey)** — outside the workflow editor, in HR Credentials. Do this first while you're not yet in the editor.
3. **Inside v20 editor:**
   - Tier 1.1 (F2 dedup) — most impactful, do while fresh.
   - Tier 1.2 (F4 flags) — quick.
   - Tier 1.3 (F3 now/now_iso) — quick.
4. **Twin DDL detour** — Tier 2.1 step 1 (the 4 ALTER TABLE statements for latency).
5. **Back in editor:**
   - Tier 2.1 (F8 latency rebind).
   - Tier 2.2 (10 token bindings).
   - Tier 2.3 (6 F7 columns; extend Extract params first if needed).
   - Tier 2.4 (F13 load_id filter).
6. **Save + publish v20.**
7. **Test call** — make one test call to verify v20 works end-to-end. Confirm `calls_log` row populates 10 token cols + 6 F7 cols + `p70_latency_ms`/`p90_latency_ms` (numeric, not boolean).

**Tier 3 is a separate session** — defer until Tier 1+2 ship cleanly.

---

## Things explicitly NOT in scope of this session

- Dashboard widget build — comes AFTER Phase C is verified shipped.
- Sales-rep dashboard view — `project_sales_dashboard_view.md`, deferred indefinitely.
- HR-2 timestamps via runs API — Path B-1 (T3.3) is the simpler alternative; runs API access still gated.
- Super test workflow / edge case harness — `project_super_test_workflow.md`, deferred.

---

## When you're done

Tell me which tiers shipped + paste any errors. Then I:
1. Re-run `scripts/review_transcripts.py` against new test-call rows to confirm telemetry data is flowing.
2. Run an HR audit (via your "paste this prompt to HR AI" pattern) to confirm F1-F11 status moves to FIXED.
3. Start the `transcript_telemetry.py` + dashboard widget build per the locked design docs.
