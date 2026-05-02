# HR Phase C v2 — final production plan

**Supersedes** [hr-phase-c-action-plan.md](hr-phase-c-action-plan.md). v1 deferred items the user flagged as Phase-C-required: `notes` field, column reorder, and full-detail recall on every small thing. v2 captures every detail; v1 stays as historical record.

**Workflow:** `inbound-carrier-sales-new`. v20-phase-c already forked from v19. UI-only changes per [reference_hr_post_batch_corruption.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/reference_hr_post_batch_corruption.md).

**Snapshot — what's done at v2 lock time** (from resume state):
- C0 pre-flight ✅
- C1 webKey context (HR has no Credentials manager — use API Key auth dropdown, see C-T1.4 below) ✅ context-clear, fix pending
- C2 fork to v20 ✅
- C3.1 F2 prompt dedup verified single occurrence ✅
- C3.2 F4 book_load required flags ✅
- C3.3 F3 calculate_rate now/now_iso key rename ✅
- C4 Twin DDL — 4 ALTER TABLEs (drop bool latency cols, add int4 cols) ✅
- C5.1 F8 Log Event latency rebind ✅
- C5.3 F13 Get Load Details `load_id` filter added ✅

**In progress / not started at v2 lock time:**
- C5.2 — 10 token-column bindings on Log Event (paused mid-flow)
- C5.4 — Extract carrier_name + lane_origin + lane_dest param add + 6 F7 bindings (not started)
- All v2-new items below (notes, column reorder, F12, F15, Path B-1, VP patches, bookings rename)

---

## Live Twin schema audit (run 2026-04-30 night, ground truth)

Pulled `SELECT * FROM calls_log WHERE call_id IS NOT NULL` (WAF-safe; returned 15 rows). Current 25 columns in current order:

```
 1 id                              BIGSERIAL PK
 2 created_at                      TIMESTAMPTZ
 3 call_id                         TEXT (UNIQUE per v15 cleanup)
 4 mc_number                       TEXT
 5 call_outcome                    TEXT
 6 sentiment                       TEXT
 7 case_health_score               BIGINT
 8 audit_remarks                   TEXT
 9 fmcsa_eligibility_failure_reason TEXT
10 callback_phone                  TEXT
11 duration_seconds                BIGINT          ← user: move to END
12 transcript                      TEXT
13 intermediate_response_count     BIGINT          ← user: move to END (with latency)
14 extract_input_tokens            INTEGER
15 extract_output_tokens           INTEGER
16 extract_reasoning_tokens        INTEGER
17 extract_cached_input_tokens     INTEGER
18 extract_uncached_input_tokens   INTEGER
19 chs_input_tokens                INTEGER
20 chs_output_tokens               INTEGER
21 chs_reasoning_tokens            INTEGER
22 chs_cached_input_tokens         INTEGER
23 chs_uncached_input_tokens       INTEGER
24 p70_latency_ms                  INTEGER         ← all NULL (just added in C4, no calls yet)
25 p90_latency_ms                  INTEGER         ← all NULL (just added in C4, no calls yet)
```

**Missing from `calls_log` per Phase C scope:**
- `carrier_name` — F7
- `lane_origin` — F7
- `lane_dest` — F7
- `hangup_reason` — F7
- `room_name` — F7
- `status` — F7
- `notes` — user-flagged gap (was Tier-3 in v1, promoted to Tier-1 here per [project_callback_audit_field.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/project_callback_audit_field.md))

7 new columns to add. Plus column reorder requested.

---

## Strategic decision: column reorder via drop+recreate

Postgres `ALTER TABLE` does NOT support column reordering. Options:

| Option | Mechanism | Data preserved | Cosmetics | Risk |
|---|---|---|---|---|
| A | `CREATE TABLE calls_log_new` + `INSERT SELECT` + `DROP calls_log` + `ALTER TABLE calls_log_new RENAME TO calls_log` | ALL rows preserved via INSERT SELECT | ✅ correct order | Constraints/indexes/permissions need re-adding; if any HR @-picker chip references the table during the transaction window, it errors briefly |
| B | Just `ALTER TABLE ADD COLUMN` for the 7 new cols | All rows preserved | ❌ duration + intermediate_response_count + token cols not at end | Zero |
| C | Drop entirely + recreate from scratch | All 15 mock-seeded rows lost (re-runnable via `scripts/seed_token_columns.py`) | ✅ correct order | Same as A but simpler |

**Pick: Option A.** Preserves the 15 rows (mock-seeded but useful for telemetry preview), achieves correct order, and the Twin write window is sub-second. The single index + UNIQUE constraint we re-add is `idx_calls_log_created_at`, `idx_calls_log_mc_number`, `idx_calls_log_call_outcome` (per stale schema file) + `calls_log_call_id_uniq` (per v15 cleanup).

---

## Final target column order (32 cols)

Grouped semantically; user-flagged ops cluster (duration + response_count + latency) at the END together.

| # | Column | Type | Group | Source |
|---|---|---|---|---|
| 1 | id | BIGSERIAL PK | identity | HR auto |
| 2 | created_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | identity | HR auto |
| 3 | call_id | TEXT UNIQUE | identity | `__run_id__` |
| 4 | mc_number | TEXT | caller | verify_carrier @ picker |
| 5 | carrier_name | TEXT | caller | Extract.response.carrier_name (NEW) |
| 6 | callback_phone | TEXT | caller | Voice Agent.from |
| 7 | fmcsa_eligibility_failure_reason | TEXT | caller | Extract.response.fmcsa_eligibility_failure_reason |
| 8 | lane_origin | TEXT | lane | Extract.response.lane_origin (NEW) |
| 9 | lane_dest | TEXT | lane | Extract.response.lane_dest (NEW) |
| 10 | call_outcome | TEXT | quality | Extract.response.call_outcome |
| 11 | sentiment | TEXT | quality | Real-time Carrier Sentiment classifier |
| 12 | case_health_score | BIGINT | quality | CHS Code node |
| 13 | audit_remarks | TEXT | quality | CHS reasoning |
| 14 | notes | TEXT NOT NULL DEFAULT '' | quality | Extract.response.notes (NEW — was Tier-3) |
| 15 | hangup_reason | TEXT | session | Voice Agent / Analyze chip (NEW) |
| 16 | room_name | TEXT | session | Voice Agent / Analyze chip (NEW) |
| 17 | status | TEXT | session | Voice Agent / Analyze chip (NEW) |
| 18 | transcript | TEXT | session | Voice Agent.transcript |
| 19 | extract_input_tokens | INTEGER | tokens-extract | Extract Llm Usage |
| 20 | extract_output_tokens | INTEGER | tokens-extract | Extract Llm Usage |
| 21 | extract_reasoning_tokens | INTEGER | tokens-extract | Extract Llm Usage |
| 22 | extract_cached_input_tokens | INTEGER | tokens-extract | Extract Llm Usage |
| 23 | extract_uncached_input_tokens | INTEGER | tokens-extract | Extract Llm Usage |
| 24 | chs_input_tokens | INTEGER | tokens-chs | CHS Llm Usage |
| 25 | chs_output_tokens | INTEGER | tokens-chs | CHS Llm Usage |
| 26 | chs_reasoning_tokens | INTEGER | tokens-chs | CHS Llm Usage |
| 27 | chs_cached_input_tokens | INTEGER | tokens-chs | CHS Llm Usage |
| 28 | chs_uncached_input_tokens | INTEGER | tokens-chs | CHS Llm Usage |
| 29 | duration_seconds | BIGINT | telemetry-end | Voice Agent.duration |
| 30 | intermediate_response_count | BIGINT | telemetry-end | Voice Agent var |
| 31 | p70_latency_ms | INTEGER | telemetry-end | Voice Agent.p70_latency_ms |
| 32 | p90_latency_ms | INTEGER | telemetry-end | Voice Agent.p90_latency_ms |

---

## Tier 1 — Twin DDL session (run via Twin SQL editor, single-statement each)

Run **before** opening the HR workflow editor for Phase C HR UI work, so Log Event can rebind to fresh schema.

### C-T1.0 Pre-flight: row count guard
Confirms expected row count survives.
```sql
SELECT count(*) FROM calls_log;
```
Should return 15 (or current actual). Note the number — reverify after rebuild.

### C-T1.1 Create new table with target order
```sql
CREATE TABLE calls_log_new (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  call_id TEXT,
  mc_number TEXT,
  carrier_name TEXT,
  callback_phone TEXT,
  fmcsa_eligibility_failure_reason TEXT,
  lane_origin TEXT,
  lane_dest TEXT,
  call_outcome TEXT,
  sentiment TEXT,
  case_health_score BIGINT,
  audit_remarks TEXT,
  notes TEXT NOT NULL DEFAULT '',
  hangup_reason TEXT,
  room_name TEXT,
  status TEXT,
  transcript TEXT,
  extract_input_tokens INTEGER,
  extract_output_tokens INTEGER,
  extract_reasoning_tokens INTEGER,
  extract_cached_input_tokens INTEGER,
  extract_uncached_input_tokens INTEGER,
  chs_input_tokens INTEGER,
  chs_output_tokens INTEGER,
  chs_reasoning_tokens INTEGER,
  chs_cached_input_tokens INTEGER,
  chs_uncached_input_tokens INTEGER,
  duration_seconds BIGINT,
  intermediate_response_count BIGINT,
  p70_latency_ms INTEGER,
  p90_latency_ms INTEGER
);
```

### C-T1.2 Copy existing rows into new table
Select existing columns explicitly (NOT `SELECT *`) so the missing 7 default to NULL/'' correctly.
```sql
INSERT INTO calls_log_new (
  id, created_at, call_id, mc_number,
  callback_phone, fmcsa_eligibility_failure_reason,
  call_outcome, sentiment, case_health_score, audit_remarks,
  transcript,
  extract_input_tokens, extract_output_tokens, extract_reasoning_tokens,
  extract_cached_input_tokens, extract_uncached_input_tokens,
  chs_input_tokens, chs_output_tokens, chs_reasoning_tokens,
  chs_cached_input_tokens, chs_uncached_input_tokens,
  duration_seconds, intermediate_response_count,
  p70_latency_ms, p90_latency_ms
)
SELECT
  id, created_at, call_id, mc_number,
  callback_phone, fmcsa_eligibility_failure_reason,
  call_outcome, sentiment, case_health_score, audit_remarks,
  transcript,
  extract_input_tokens, extract_output_tokens, extract_reasoning_tokens,
  extract_cached_input_tokens, extract_uncached_input_tokens,
  chs_input_tokens, chs_output_tokens, chs_reasoning_tokens,
  chs_cached_input_tokens, chs_uncached_input_tokens,
  duration_seconds, intermediate_response_count,
  p70_latency_ms, p90_latency_ms
FROM calls_log;
```

### C-T1.3 Sync the BIGSERIAL sequence to the max id
Otherwise the next INSERT collides with existing id values.
```sql
SELECT setval(pg_get_serial_sequence('calls_log_new', 'id'), (SELECT COALESCE(MAX(id), 1) FROM calls_log_new));
```

### C-T1.4 Verify row count parity
```sql
SELECT count(*) FROM calls_log_new;
```
Must equal C-T1.0 pre-flight count.

### C-T1.5 Drop old table
```sql
DROP TABLE calls_log;
```

### C-T1.6 Rename new → canonical
```sql
ALTER TABLE calls_log_new RENAME TO calls_log;
```

### C-T1.7 Re-add UNIQUE constraint on call_id
```sql
ALTER TABLE calls_log ADD CONSTRAINT calls_log_call_id_uniq UNIQUE (call_id);
```

### C-T1.8 Re-add indexes (one per submission)
```sql
CREATE INDEX idx_calls_log_created_at ON calls_log (created_at DESC);
```
```sql
CREATE INDEX idx_calls_log_mc_number ON calls_log (mc_number);
```
```sql
CREATE INDEX idx_calls_log_call_outcome ON calls_log (call_outcome);
```

### C-T1.9 Final verify
```sql
SELECT * FROM calls_log WHERE call_id IS NOT NULL;
```
Confirm: 15 rows (or expected count), 32 columns in correct order, schema cache reload triggered.

---

## Tier 2 — HR UI session (in v20-phase-c editor)

### C-T2.1 — F11 webKey relocate (HR API Key auth dropdown)
Per [resume note](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/project_phase_c_in_progress_resume.md), HR has no global Credentials manager — only per-webhook Authentication dropdown. Take the best path available:

1. Open `GET MC Number` webhook node (child of `verify_carrier`).
2. **URL:** change `https://mobile.fmcsa.dot.gov/qc/services/carriers/{{mc_number}}?webKey=cdc33e44d693a3a58451898d4ec9df862c65b954` to bare `https://mobile.fmcsa.dot.gov/qc/services/carriers/{{mc_number}}`.
3. **Authentication dropdown** → select **API Key**.
4. Fill in: Key name `webKey`, Key value `cdc33e44d693a3a58451898d4ec9df862c65b954`, Location **Query Parameter**.
5. Save.

**If API Key dropdown lacks query-parameter location** → fallback: drop URL query string, add `webKey=cdc33e44...` row to the Params section instead. Same security posture — slightly cleaner config than baked-in URL.

**Verify:** Test webhook with a known-valid MC. Returns same payload as before. Workflow JSON read no longer shows the key in the URL string (it's under the auth/params config block, still readable but a step abstracted — best HR offers without a credentials feature).

---

### C-T2.2 — `notes` field full pipeline (NEW from Tier-3 promotion)

Three sub-edits, all in v20 editor:

**(a) Extract Call Details — add `notes` parameter**
1. Click `Extract Call Details` AI Extract node.
2. Click `+ Add Field` (or equivalent in HR's strict-schema editor).
3. Field name: `notes`
4. Type: `string` (nullable per [reference_hr_extract_strict_schema_rules.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/reference_hr_extract_strict_schema_rules.md) — strict mode requires `["string", "null"]`)
5. Description (paste verbatim into HR field):

   > Free-text notes the case owner picking this up later needs to know — alternate callback phone if the carrier gave one, open questions the carrier had for dispatcher, anything anomalous worth flagging at handoff. Empty string `""` if nothing meaningful happened on this call. Do NOT invent content; default empty.

6. Required: `true` (per strict mode every property must be in `required`); add to required array.
7. Save.

**(b) Voice Agent Prompt — add `<call_notes>` section**

Locate the Prompt node body. Add this section (place it after `<out_of_scope>` and before `<closing_reminders>`, or wherever the current sectioning lands cleanly):

```
<call_notes>
If during the call you collect any of the following — capture them mentally:
- An alternate callback phone number the carrier offered.
- An open question the carrier had for dispatcher / case owner.
- Anything anomalous worth flagging for the human picking this up later.

You do NOT need to read any of this back to the carrier. The post-call extraction pulls it into a single `notes` audit field. Speak naturally with the carrier; the structured note is a side effect of the conversation, not a script line.

If nothing meaningful happens, the post-call extract will record an empty string — that is the correct default.
</call_notes>
```

Save.

**(c) Log Event Write-to-Twin chip — bind `notes` column**
1. Click `Log Event` chip.
2. `+ Add column` → column `notes`, type `text`, value via @ picker → `Extract Call Details → response.notes`.
3. Save.

**Verify:** Test call where carrier offers a callback number ("call me back at 555-1234 if anything changes"). Post-call, `SELECT notes FROM calls_log WHERE call_id = '<id>'` shows the captured note. A clean happy-path call shows `''` (empty string).

---

### C-T2.3 — F7 six-column extension (Extract param add + Log Event bindings)

This is the **C5.4 backlog item** plus the F7 set in one step now that the Twin schema has the columns.

**(a) Extract Call Details — add 3 NEW params**
1. Click `Extract Call Details`.
2. Add field: `carrier_name` (string, nullable, required:true). Description:

   > Carrier company legal name as the carrier or FMCSA stated it during the call. Null if no carrier name was confirmed.

3. Add field: `lane_origin` (string, nullable, required:true). Description:

   > Origin city + state (e.g., "Dallas, TX") if the carrier specified an origin lane during the call. Null if not stated. Format: "City, ST" 2-letter state code.

4. Add field: `lane_dest` (string, nullable, required:true). Description:

   > Destination city + state if the carrier specified a destination lane during the call. Null if not stated. Format: "City, ST" 2-letter state code.

5. Save Extract.

**(b) Log Event Write-to-Twin chip — 6 new column bindings**
| # | Column | Type | @ picker source |
|---|---|---|---|
| 1 | `carrier_name` | text | Extract Call Details → response.carrier_name |
| 2 | `lane_origin` | text | Extract Call Details → response.lane_origin |
| 3 | `lane_dest` | text | Extract Call Details → response.lane_dest |
| 4 | `hangup_reason` | text | Voice Agent → call_end_event |
| 5 | `room_name` | text | Voice Agent → room_name |
| 6 | `status` | text | Voice Agent → status (or call status equivalent in @ picker) |

If `room_name` / `status` aren't directly available in Voice Agent's @ picker, search `Analyze Incoming Conversation` outputs — the v19 audit said they were exposed there. Note actual path used.

**Verify:** Test call where carrier names origin + destination lane. After call, all 6 columns populate non-NULL.

---

### C-T2.4 — C5.2 — 10 token-column bindings (resume from paused state)

Already partially in flight per resume state. Complete now.

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

**Verify:** Test call. After post-call extracts run, all 10 cols show non-NULL token counts; mock-seeded values on historical rows untouched.

---

### C-T2.5 — `intermediate_response_count` rebind verify

C-T1 rebuilt the table and preserved this column's data, but the Log Event chip mapping needs to be re-verified after the rename. Click `Log Event` → confirm `intermediate_response_count` row is still bound to the Voice Agent intermediate-response counter @ picker chip. If missing (rebuild may have nudged it), re-add via @ picker.

---

### C-T2.6 — F8 latency rebind verify (now OPTIONAL per ADR-012)

**Update 2026-04-30 post-test:** live test call id=45 confirmed `p70_latency_ms` / `p90_latency_ms` / `intermediate_response_count` populate as NULL even with chip bindings in place. User direction: this is **expected HR-platform behavior**, ignore. ADR-012 locks dashboard-side compute from `transcript` + `duration_seconds` as the authoritative source for these three values.

**Current chip binding status:** OPTIONAL. Both states (bound or unbound) produce NULL on every Twin write. Decide per personal preference; the dashboard ignores the raw columns either way.

If you choose to bind defensively in case HR fixes the bug later: confirm `p70_latency_ms` and `p90_latency_ms` are wired to the int @ pickers from `<Voice Agent>.p70_latency_ms` / `<Voice Agent>.p90_latency_ms` (NOT to the deprecated `*_intermediate_fired` boolean vars). Same for `intermediate_response_count` from the Voice Agent intermediate-response counter.

If you choose to leave unbound: just skip — dashboard pulls transcript + duration directly.

---

### C-T2.7 — F12 classifier decision: REMOVE

Real-time Call Outcome classifier has `classes: []` (empty array per audit). Two paths:
- Wire it: 5 enums = `load_booked / no_match / carrier_not_qualified / call_abandoned / rate_disagreement`.
- **Remove it.** Post-call Extract handles call_outcome (4 enums) more reliably than real-time classifiers per [reference_hr_workflow_schema_population.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/reference_hr_workflow_schema_population.md). Real-time's value is observability-only; we don't consume it downstream.

**Pick: REMOVE.** Click the real-time `Call Outcome` classifier node → delete. Saves an LLM call per turn.

---

### C-T2.8 — F15 cosmetic typo fix

Click the `Case Healt Score` AI Extract node → rename to `Case Health Score`. ~30 sec.

---

### C-T2.9 — Path B-1 node-timing capture — DEFERRED per ADR-012

**Updated 2026-04-30 night.** User direction: *"No but just save it. If we do robust version with transcript or run details no need to use the one on twin don't."*

Decision: skip C-T2.9 at MVP. Robust latency comes from HR run details API + transcript per ADR-012 Phase 2. The `node_timings_json` Twin column is **already added** as an escape hatch (live, harmless, empty); only populated if run details API probe turns out insufficient.

**Skip the rest of this section** unless future investigation flips this decision. Original instructions kept below for reference if you do need to build the node later.

---

**Twin DDL (already applied 2026-04-30 night):**
```sql
ALTER TABLE calls_log ADD COLUMN node_timings_json TEXT;
```

**HR UI:**
1. In v20 editor, add a new `Run Python` action node post-call (chain it after CHS, before Log Event so its output is bindable).
2. Name: `Capture Node Timings`.
3. Input Data fields (one row per node we want timestamps from):
   - `voice_agent_start` ← `Voice Agent.started_at` (or whatever the HR var is for call start)
   - `voice_agent_end` ← `Voice Agent.ended_at`
   - `verify_carrier_start` ← `verify_carrier.started_at` (if exposed; else skip; same for each tool)
   - `verify_carrier_end` ← `verify_carrier.ended_at`
   - `query_loads_start`, `query_loads_end`
   - `negotiate_rate_start`, `negotiate_rate_end`
   - `book_load_start`, `book_load_end`
   - `extract_start` ← `Extract Call Details.started_at`
   - `extract_end` ← `Extract Call Details.ended_at`
   - `chs_start`, `chs_end`
4. Code body (RestrictedPython-safe per [reference_hr_python_sandbox_restrictions.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/reference_hr_python_sandbox_restrictions.md)):

```python
import json

# Defensive: if any var was unbound at HR call time, key is missing → skip silently.
out = {}
for name in (
    "voice_agent_start", "voice_agent_end",
    "verify_carrier_start", "verify_carrier_end",
    "query_loads_start", "query_loads_end",
    "negotiate_rate_start", "negotiate_rate_end",
    "book_load_start", "book_load_end",
    "extract_start", "extract_end",
    "chs_start", "chs_end",
):
    val = inp.get(name)
    if val:
        out[name] = val

output = {"node_timings_json": json.dumps(out)}
```

5. Add new column to Log Event Write-to-Twin chip:
   - column `node_timings_json`, type `text`, @ picker → `Capture Node Timings.node_timings_json`.

**If HR doesn't expose `started_at` / `ended_at` per node** (which the v19 audit suggests it doesn't): keep the node but with whatever timing fields ARE bindable. Even just Voice Agent start + end gives you call-level wall-clock duration cross-checked against `duration_seconds`.

If 0 timing fields bind: skip C-T2.9 entirely and accept p50/p99 stay NULL until HR exposes per-node timings (Tier-2 platform feature request).

---

### C-T2.10 — VP-1..VP-5 voice prompt patches (consolidated paste)

Per [project_v15_e2e_first_pass_findings.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/project_v15_e2e_first_pass_findings.md). 5 small targeted edits to the voice prompt body. Group them into a single paste pass (we're already in the prompt node for C2.1 dedup verify):

**VP-1 — clarification-loop cap.** In the existing slot-collection / clarification section, append:

> If you've asked for the same slot (equipment, lane origin, lane destination, weight, etc.) twice and the carrier responds with non-answer filler ("right on", "fine", "anything sound", etc.) — STOP asking. Offer 2-3 specific options to choose from instead. Example: "Sure — to make this easier, are you running a dry van, reefer, or flatbed today?"

**VP-2 — narrowing rule.** In the load-search prep section:

> Before calling `query_loads`, you MUST have at least ONE of: origin state, destination state, OR equipment type. If the carrier hasn't given any of those, ask ONE narrowing question first ("Where are you running today — origin or destination?" OR "What's your equipment?"). Do NOT call `query_loads` with all three blank — that returns 12 random loads, not your carrier's lane.

**VP-3 — recap-before-transfer strict 6-tuple.** In the transfer / handoff section:

> Before mock-transferring, you MUST recap each booking to the carrier in this exact 6-tuple format: load ID, origin, destination, equipment, pickup time, agreed rate. Example: "Confirming — you're booked on LOAD-0042, Dallas TX to Atlanta GA, dry van, picking up Tuesday at 0800, $2,400 all-in. I'll transfer you to dispatch now." Do NOT skip this even if time feels tight.

**VP-4 — no-retry on FMCSA decline.** In the FMCSA gate section:

> One mishear retry on the MC number is allowed (carrier said "8-2-5-1-9-1" and `verify_carrier` returned MC_NOT_FOUND → re-readback once, retry once). After that, if FMCSA still declines, end the call politely. Do NOT loop on retries — three FMCSA misses in one call is a process failure, not a recovery opportunity.

**VP-5 — intent-language negotiation.** In the negotiation section:

> Negotiate using intent-language, not script-language. Vary phrasing across rounds — never use "I can do" / "best I can offer" / "final number" verbatim multiple times. Use carrier's stated context (urgency, lane familiarity, prior load) to anchor the next move. Examples: round 1 frame around lane fairness, round 2 reframe around urgency or backhaul value, round 3 close with the alternative-or-leave anchor. Do not announce round numbers.

Save Prompt node.

---

### C-T2.11 — Northstar definition (optional, ~5 min)

Per [feedback_diagram_principles.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/feedback_diagram_principles.md) + the user's earlier Q7 lock instinct (2 measurable + 3 behavioral). If HR exposes a Northstar slot on the Prompt node, fill in:

- **Measurable 1:** ≥40% of completed calls (sentiment != frustrated, not abandoned within 30s) result in at least one `book_load` fire.
- **Measurable 2:** Median p70_latency_ms < 1500ms across the trailing 10 calls.
- **Behavioral 1:** Agent never reads back floor / target / discount values to the carrier.
- **Behavioral 2:** Agent recaps each booking in the 6-tuple before transfer (load ID, origin, dest, equipment, pickup, rate).
- **Behavioral 3:** Agent FMCSA-validates BEFORE pitching loads, not after.

If no Northstar slot, paste these into a `<northstars>` section at the very top of the Prompt node body (above `<role_and_objective>`).

---

## Tier 3 — Bookings table renames — N/A AT v2 LOCK

**Live bookings audit (2026-04-30 night):** `bookings` table has 6 columns in this order:
```
id, created_at, call_id, mc_number, load_id, apply_rate
```

`apply_rate` is already the new name. `original_rate` was deliberately NOT added in v15 (lean-design decision per [project_v14_loop_architecture.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/project_v14_loop_architecture.md) — only the booked rate is stored, not the pitched rate).

**Status: nothing to do.** [project_field_renames_pending.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/project_field_renames_pending.md) is now stale — close it post-v20 publish.

**If we LATER want pitch/apply delta tracking** for economics dashboard ($pitched − $apply per booking): add a single column `original_rate DOUBLE PRECISION` to bookings + bind from `book_load.original_rate` (will need to add as a tool param). That's a v16 enhancement, NOT Phase C scope.

---

## Out of scope for Phase C v2 (deferred items confirmed)

These appeared in the user's flagged list but DON'T belong in Phase C — kept here for explicit acknowledgement:

- **Load-booked-status lifecycle** — `loads.status` + `booked_at` + `booked_by_call_id` per [project_load_booked_status_lifecycle.md](../C:/Users/Andre/.claude/projects/c--Users-Andre-OneDrive-Documentos-GitHub-Robot/memory/project_load_booked_status_lifecycle.md). Tier-2 production feature; not a take-home requirement.
- **Sales-rep dashboard view** + **Real-time negotiation hook** — both deferred per their own memory files.
- **F12 alternative wiring (rather than removal)** — only if dashboard later wants real-time outcome stream.
- **Super test workflow / edge-case harness** — deferred.
- **HR `key_details` historical name** — superseded by `notes`. Not relevant.

---

## Suggested execution order (one HR + Twin session)

1. **Twin DDL session (~10 min):** Run all of Tier 1 (C-T1.0 through C-T1.9) in the Twin SQL editor. Each statement is one submission.
2. **HR UI session (~50-70 min):**
   - C-T2.1 webKey relocate (~5 min)
   - C-T2.2 notes pipeline (Extract param + prompt section + Log Event binding) (~10 min)
   - C-T2.3 F7 six-column + 3 new Extract params (~12 min)
   - C-T2.4 finish 10 token bindings (~5 min)
   - C-T2.5 + C-T2.6 verify intermediate_response_count + p70/p90 still bound (~3 min)
   - C-T2.7 remove F12 empty classifier (~1 min)
   - C-T2.8 F15 typo fix (~30 sec)
   - C-T2.9 Path B-1 timing capture (~15 min if HR exposes per-node times; skip if not)
   - C-T2.10 VP-1..VP-5 prompt patches (~10 min)
   - C-T2.11 Northstars (~5 min)
3. **Save + publish v20-phase-c.**
4. **Bookings rename Tier 3 if applicable (~5 min).**
5. **Test call** — one full live call carrier specifies origin + destination + equipment + books one load + offers callback phone. Should populate every NEW column (carrier_name, lane_origin, lane_dest, notes, hangup_reason, room_name, status, all 10 token cols, p70/p90 latency).
6. **SQL verify** — `SELECT * FROM calls_log ORDER BY created_at DESC LIMIT 1` (note: WAF blocks ORDER BY+LIMIT — use `WHERE created_at > '<5min ago>'` instead). Confirm 32 columns populated as expected.

---

## When done — handoff to dashboard build

After Phase C v2 ships clean:
1. Re-run `scripts/review_transcripts.py` against the new test-call rows to confirm tokens + transcripts still parse.
2. Run an HR audit pass via the paste-prompt-to-HR-AI pattern — confirm F1, F2, F4, F3, F8, F11, F12, F13, F15 all FIXED; F5, F6, F14 status updated.
3. Begin `api/app/services/transcript_telemetry.py` per [docs/design/transcript-telemetry-module.md](design/transcript-telemetry-module.md).
4. Begin Telemetry tab + 3 widgets per [docs/design/dashboard-widget-integration-plan.md](design/dashboard-widget-integration-plan.md).
5. Apply `.pit-surface` palette swap on Telemetry page.
6. Run [docs/reviews/faang-qc-prompt.md](reviews/faang-qc-prompt.md) before sign-off.

---

## Summary of v2 deltas vs v1

| Item | v1 | v2 |
|---|---|---|
| `notes` field | T3.2 (deferred) | **Tier-1, C-T2.2 with full Extract+prompt+binding pipeline** |
| Column reorder | Not addressed | **Tier-1 drop+recreate via INSERT SELECT, target order locked** |
| F7 6-col extension | T2.3 | C-T2.3 (now includes 3 NEW Extract params) |
| F12 classifier | T3.1 (decide later) | **C-T2.7 — REMOVE (decision locked)** |
| F15 typo | T3.6 | C-T2.8 (still cheap, batched here) |
| Path B-1 timing capture | T3.3 | **C-T2.9 (Tier-2, mandatory if HR exposes timings)** |
| VP-1..VP-5 prompt patches | T3.4 | C-T2.10 (paste in same prompt session as F2 dedup verify) |
| Northstars | T3.5 | C-T2.11 (lower-cost cosmetic) |
| Bookings rename | Not addressed | **Tier-3 explicit step (verify-then-rename)** |
| Live Twin audit | Not done | **Done — 25-col current state ground truth in this doc** |
| Final target order | Implicit | **Explicit 32-col table with type + source per column** |

v2 is the canonical Phase C plan. v1 stays as historical record only.
