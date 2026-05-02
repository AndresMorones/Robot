# UI Build Guide — Inbound Carrier Sales workflow from zero

Authoritative recipe for rebuilding the HR voice workflow by hand in HR UI, phase by phase, with a voice/integration test between every phase. After every conversation compact, this doc is the source of truth for "how do we rebuild from scratch?" Reference [scripts/iac/snapshots/v5_nodes.json](../../scripts/iac/snapshots/v5_nodes.json) for any long config values not embedded here.

## Why we're rebuilding

Empirically established (memory: `reference_hr_post_batch_corruption.md` + `reference_hr_import_breaks_references.md`):
- **API POSTs to forks corrupt voice runtime** — UI-build is mandatory
- **HR's import doesn't translate `call.static.id` and stale `group_id` references** — fresh imports always need 1+ UI fixes
- **Forks from corrupted ancestors stay corrupted** — restart from a fresh UI build, not a fork

So we build by hand in the UI, on a brand-new empty workflow. We test between each phase to catch issues early instead of at the end.

## Skip-list (per Andres direction)

- **Computations** — drop. Re-route Case Health Score's parent from Computations → Extract.
- **Carrier Sales Auditor** — drop. Re-route Classify Sentiment's parent from Auditor → Case Health Score. Drop `final_offer_position` + `posted_price_increase` columns from Write to Twin.

## Canonical config source

Every node's full config (prompt bodies, parameters, Python code, tag definitions) lives in:

```
scripts/iac/snapshots/v5_nodes.json
```

When a phase says "paste from v5", search the JSON for the node by name, copy its `configuration` (or `function` for tools, or top-level `prompt_md` for the Prompt node). Don't retype long content — copy-paste from this file.

---

## Phase 0 — Setup (one-time, ~5 min)

**0a. Create empty workflow in HR UI**
- Top nav → New Workflow → choose **Empty / Blank** (NOT "from template" — has reference bug)
- Name: `Inbound Carrier Sales` (or your preference; keep simple)
- Save

**0b. Create workflow variables** (Workflow → Settings → Variables)
- `negotiation_floor_pct` = `0.10`
- `max_negotiation_rounds` = `3`
- `agent_name` = `Paul`
- `company_name` = `Acme Logistics`

(All four fields, value_development = value_staging = value_production for each.)

**0c. Twin schema setup** (one-time per org — already done if previous workflows used it):
- HR Twin SQL editor → run `data/twin_schema_loads.sql` (creates `loads` table)
- HR Twin SQL editor → run `data/twin_schema_calls_log.sql` (creates `calls_log` table, 23 cols + 3 indexes)
- HR Twin → load CSV: `data/twin_seed_loads.sql` (25 seed rows)

If tables already exist in your org's Twin from prior work, skip 0c.

**Test**: Open `loads` and `calls_log` in HR Twin UI. Both should be visible.

---

## Phase 1 — Trigger + Voice Agent + Prompt (test voice)

**1a. Web call trigger**
- Drag → Trigger → **Web call** (event_id `6e32e01e-722f-4b8b-9372-500b845686d1`, integration "AI Agent")
- No config needed. Connect downstream when adding next node.

**1b. Inbound Voice Agent**
- Drag → AI Agent → **Inbound Voice Agent** (event_id `0192e5dc-08df-78bf-a549-f43c6bf9f087`)
- Parent: Web call (drag connection)
- **Configure (use the @ picker for "Call source" — never hand-type)**:
  - **Call source**: pick "Web call" from dropdown (this writes the correct `call.static.id`)
  - **Agent name**: `Paul`
  - **Voice**: pick a known-good voice from dropdown — try `Paul` first (id `m357hexpjk2s`). If unavailable, pick any voice with audible preview.
  - **Languages**: English (en)
  - **Background**: Call center (id `https://storage.googleapis.com/happyrobot-public/backgrounds/call-center.8k.wav`)
  - **Transcription context**: paste from v5_nodes.json (471-char freight-carrier paragraph)
  - **Keyterms**: 13 entries — `Valdosta`, `San Jose`, `Oakland`, `Cartersville, Georgia`, `Columbus, Ohio`, `Boise, Idaho`, `Ada, Michigan`, `Menasha, Wisconsin`, `book the load`, `thirty degrees`, `carrier qualification`, `online posting`, `freight`
  - **Real-time sentiment classifier**: ON
  - **Real-time classifiers**: add "Call Outcome" with 6 tags — `load_booked`, `negotiation_failed`, `carrier_not_qualified`, `no_load_match`, `carrier_declined`, `abandoned`. Prompt body in v5_nodes.json.
  - **Enable memory**: ON
  - **Enable denoised STT**: ON
  - **Interaction limit**: `10`
  - **Max call duration**: `600` seconds
  - **Recording**: ON, no disclaimer

**1c. Prompt node (auto-created under Voice Agent OR add explicitly)**
- If HR auto-created a child Prompt: open it. Otherwise drag → Prompt under Voice Agent.
- **Configure**:
  - **Model**: pick "GPT-4.1" or "Turbo" from dropdown (UI writes registry id `turbo-one` or `turbo` — both are valid; never hand-type "gpt-4.1" as the id)
  - **Initial message**: `Thank you for calling Acme Logistics, this is Paul. How can I help?`
  - **Prompt body** (markdown): paste from v5_nodes.json `prompt_md` field — 1717 chars covering carrier sales rep persona, load-number flow, style. OR paste a simplified version from `prompts/voice-agent-system-prompt.md` if it exists.

### TEST after Phase 1

1. Open the workflow's Web call test panel in HR UI
2. Click "Test web call" — agent should answer with the initial message
3. Say "hello" — agent should respond conversationally
4. **Pass criteria**: voice works end-to-end. No tools yet — agent will improvise responses.
5. **If broken**: voice config is the issue. Re-check voice dropdown, transcription context, model dropdown. Don't proceed until voice works.

---

## Phase 2 — 4 Tools + their children (test tool calls)

Tool nodes attach UNDER the Prompt (not under the Voice Agent directly). Each tool gets ONE child node that performs the actual work.

**2a. verify_carrier (tool) → GET MC Number (webhook child)**
- Tool config (paste from v5_nodes.json `function` field):
  - Description: `Look up the carrier's MC number in the FMCSA database to verify their operating authority...`
  - Message: AI-mode, "Let me pull that up real quick."
  - Parameters: `mc_number` (required, "The carrier's FMCSA Motor Carrier (MC) number provided by the caller.")
- Child: webhook GET node named `GET MC Number`
  - URL: `https://mobile.fmcsa.dot.gov/qc/services/carriers/` + @-picker variable `mc_number` from `verify_carrier` + `?webKey=cdc33e44d693a3a58451898d4ec9df862c65b954`
  - **Use the @ picker to insert the variable** — DO NOT hand-type `{{mc_number}}`
  - authType: none
  - ignore5XX: true

**2b. find_available_loads (tool) → Get load (Read-from-Twin child)**
- Tool config (from v5):
  - Description: "Look up a specific load by its reference number..."
  - Message: AI-mode, "Let me pull up that load for you."
  - Parameters: `reference_number` (example LOAD-0042)
- Child: Twin → **Read from Twin** node named `Get load`
  - tableName: `loads`
  - filters: 1 filter — column `load_id`, operator `equals`, value = @ picker → `find_available_loads.reference_number`

**2c. search_loads_by_lane (tool) → Fetch Loads (Read-from-Twin child)**
- Tool config (from v5):
  - Description: "Search for available loads by lane..."
  - Message: AI-mode, "Let me search for available loads on that lane for you."
  - Parameters (6): `origin_state` (req), `origin_city` (opt), `destination_state` (opt), `destination_city` (opt), `equipment_type`, `pickup_window` (req, ISO 8601)
- Child: Twin → **Read from Twin** node named `Fetch Loads`
  - tableName: `loads`
  - 5 filters (use @ picker for each value, all from `search_loads_by_lane`):
    - `origin_state` equals @search_loads_by_lane.origin_state
    - `origin_city` equals @search_loads_by_lane.origin_city
    - `destination_state` equals @search_loads_by_lane.destination_state
    - `destination_city` equals @search_loads_by_lane.destination_city
    - `equipment_type` equals @search_loads_by_lane.equipment_type
  - limit: `20`
  - orderByColumn: `pickup_datetime`, orderByDirection: `asc`

**2d. negotiate_evaluate (tool) → Calculate Carrier Cost (Run Python child)**
- Tool config (from v5, 9 parameters):
  - Description: "Evaluate the carrier's rate counter-offer. Returns ACCEPT/COUNTER/REJECT/ESCALATE..."
  - Message: none (silent tool call)
  - Parameters: `load_reference`, `loadboard_rate`, `carrier_offer`, `round_number`, `prior_broker_offers`, `current_sentiment`, `pickup_datetime`, `equipment_type`, `commodity_type`, `load_notes`
- Child: Code → **Run Python** node named `Calculate Carrier Cost`
  - Code: paste from v5_nodes.json `Calculate Carrier Cost` configuration `code` field — 4587-char Python with edge cases + ACCEPT/COUNTER/REJECT/ESCALATE/REQUEST_OFFER actions
  - input_data (7 keys, use @ picker for each):
    - `load_reference` → @negotiate_evaluate.load_reference
    - `loadboard_rate` → @negotiate_evaluate.loadboard_rate
    - `carrier_offer` → @negotiate_evaluate.carrier_offer
    - `round_number` → @negotiate_evaluate.round_number
    - `prior_broker_offers` → @negotiate_evaluate.prior_broker_offers
    - `negotiation_floor_pct` → @use_case_variables.negotiation_floor_pct
    - `max_negotiation_rounds` → @use_case_variables.max_negotiation_rounds

### TEST after Phase 2

1. Test web call → agent picks up
2. Say "I'm calling about a load, MC 12345" — agent should call `verify_carrier`, see FMCSA response
3. Say a load reference number that exists in Twin (check `data/loads.csv` for valid IDs) — agent should call `find_available_loads` → `Get load` returns the row
4. Say "I'm picking up in TX going to GA, dry van" — agent calls `search_loads_by_lane` → `Fetch Loads` returns matching rows
5. Pitch a load and counter the rate — agent calls `negotiate_evaluate` → `Calculate Carrier Cost` returns scripted message
6. **Pass criteria**: each tool fires, returns data, agent speaks the result. Don't proceed until all 4 tools work.

---

## Phase 3 — Post-call analytics chain (test extract + classify)

This branch attaches under the **Voice Agent** (sibling of Prompt), not under the Prompt. Skip Computations + Auditor per Andres direction. Re-route children to grandparent.

**3a. Initiate New Contact** (Transfer Popup → Create Popup)
- Parent: Voice Agent
- event_id: `49d7c629-bf96-47c2-ad84-1a44600b9b6e`
- phone_number: literal text `MC-pending`
- ttl_days: `10`
- enable_transfer_summary: false, enable_location: false, enable_transcript: false, enable_feedback: false

**3b. Classify** (AI → Classify, Outcome)
- Parent: Initiate New Contact
- event_id: `01926f30-36e3-7f14-9c3a-8d9a1003e532`
- Input: @ picker → `Voice Agent.transcript` (use @, never hand-type)
- Tags (6): `load_booked`, `negotiation_failed`, `carrier_not_qualified`, `no_load_match`, `carrier_declined`, `abandoned` — descriptions in v5_nodes.json
- Prompt body: from v5

**3c. Extract** (AI → Extract)
- Parent: Classify
- event_id: `01926f30-36a3-7394-8f73-eeead5d7f948`
- Input: @ picker → Voice Agent.transcript
- Parameters (14): `reference_number`, `mc_number`, `carrier_name`, `load_origin`, `load_destination`, `equipment_type`, `listed_rate`, `agreed_rate`, `num_negotiation_rounds`, `counter_offers`, `booking_decision`, `decline_reason`, `call_outcome`, `call_duration` — full schema in v5_nodes.json
- Prompt body: paste from v5_nodes.json

### Skip Computations — re-route Case Health Score parent to Extract directly

**3d. Case Health Score** (AI → Extract — uses Extract event for typed output)
- Parent: **Extract** (NOT Computations — we skip it)
- event_id: `01926f30-36a3-7394-8f73-eeead5d7f948`
- **Model**: pick "GPT-4.1" from dropdown (UI writes `turbo-one` registry id) — DO NOT leave `gpt-4.1` as the id
- Input: @ picker → Voice Agent.transcript
- Parameters (5): `case_health_score` (number), `sentiment_start`, `sentiment_end`, `sentiment_trajectory`, `health_score_reasoning` — schema in v5
- Prompt body: 53-paragraph scoring framework — paste from v5_nodes.json `Case Health Score.configuration.prompt`
- Variable references inside prompt: 11 @ picker references to Extract (response.call_outcome, response.booking_decision, etc.) and Voice Agent (user_filler_message_ratio, etc.). All via @ picker, never hand-typed.

### Skip Carrier Sales Auditor — re-route Classify Sentiment parent to Case Health Score

**3e. Classify Sentiment** (AI → Classify)
- Parent: **Case Health Score** (NOT Auditor — we skip it)
- event_id: `01926f30-36e3-7f14-9c3a-8d9a1003e532`
- Model: pick "GPT-5 Mini" (id `gpt-5-mini`) or any classifier-grade model
- Input: @ picker → Voice Agent.transcript
- Tags (5): `positive`, `neutral`, `negative`, `frustrated`, `mixed` — descriptions in v5
- Prompt body: from v5

### TEST after Phase 3

1. Make a test web call, complete a sample conversation (verify carrier, find a load, accept, hang up)
2. Open the Run details in HR UI → check each post-call node's output
3. **Pass criteria**: Classify outputs a tag, Extract outputs structured fields, Case Health Score outputs a score 0-100 + sentiment trajectory, Classify Sentiment outputs a tag. Each node should show JSON output, not errors.
4. If a node fails: re-check its @-picker bindings (most common issue)

---

## Phase 4 — Write to Twin (test calls_log persistence)

**4a. Write to Twin**
- Parent: Classify Sentiment
- event_id: `7021bfff-3e47-459c-b871-b0271ca04d9f`
- tableName: `calls_log`
- columnValues — **18 columns** (we drop 2 Auditor-sourced columns: `final_offer_position` and `posted_price_increase`):

| columnName | type | source (use @ picker) |
|---|---|---|
| `call_id` | text | `current.run_id` |
| `mc_number` | text | `Extract.response.mc_number` |
| `carrier_name` | text | `Extract.response.carrier_name` |
| `load_id` | text | `Extract.response.reference_number` |
| `equipment_type` | text | `Extract.response.equipment_type` |
| `pitched_loadboard_rate` | float8 | `Extract.response.listed_rate` |
| `agreed_rate` | float8 | `Extract.response.agreed_rate` |
| `num_negotiation_rounds` | int8 | `Extract.response.num_negotiation_rounds` |
| `call_outcome` | text | `Classify.response.classification` |
| `sentiment` | text | `Classify Sentiment.response.classification` |
| `case_health_score` | int8 | `Case Health Score.response.case_health_score` |
| `audit_remarks` | text | `Case Health Score.response.health_score_reasoning` |
| `fmcsa_eligibility_failure_reason` | text | `Extract.response.decline_reason` |
| `duration_seconds` | int8 | `Voice Agent.duration` |
| `transcript` | text | `Voice Agent.transcript` |
| `sentiment_start` | text | `Case Health Score.response.sentiment_start` |
| `sentiment_trajectory` | text | `Case Health Score.response.sentiment_trajectory` |
| `p90_latency_ms` | float8 | `Voice Agent.p90_latency_ms` |

**Always use the @ picker** when filling each value. Never hand-type the variable reference.

### TEST after Phase 4

1. Make a test web call, complete a sample conversation
2. After call ends, query Twin: `SELECT * FROM calls_log ORDER BY created_at DESC LIMIT 1;`
3. **Pass criteria**: row is inserted with all 18 fields populated (some may be empty if call didn't trigger them, but row exists with non-null call_id and transcript)

---

## Phase 5 — Publish + capture URL

1. HR UI → top nav → **Publish to Development**
2. After publish, copy the web call URL displayed in the Publish dialog
3. Save to `docs/references/happyrobot/web-call-url.txt` (file may already exist)

---

## What stays in API/script (NOT UI)

These are safe and stay in our IaC:
- Twin schema DDL (`/twin/sql`)
- Twin seed data (`/twin/tables/loads/rows/bulk`)
- Workflow variables (`/workflows/{id}/variables` — CRUD)
- GET reads (snapshots, audits)
- Our FastAPI + Docker + Fly deploy
- Next.js dashboard
- Workflow JSON exports (for documentation / future imports)

## What never goes through API
- Node CREATE/UPDATE/DELETE on voice workflows (corrupts voice runtime)
- Forking from API-mutated ancestors (inherits corruption)

## Hard-won rules (memory cross-references)

- `reference_hr_post_batch_corruption.md` — POST corrupts voice
- `reference_hr_import_breaks_references.md` — imports + 1-fix recipe
- `reference_hr_fork_corruption.md` — corrupted forks stay corrupted
- `reference_hr_model_registry.md` — `turbo-one` not `gpt-4.1` for model.static.id
- `reference_hr_create_popup_schema.md` — Initiate New Contact schema
- `reference_hr_post_call_webhook_schema.md` — 48-field POST webhook (alternate to Write to Twin)

## Build phase summary (for compact recovery)

After compact, the keyword to invoke this guide is **`REBUILD`** (or any explicit phrase like "start phase 1"). On hearing it:
1. Open this guide
2. Confirm the user's current Phase
3. Walk them through that phase's instructions one node at a time
4. Reference `scripts/iac/snapshots/v5_nodes.json` for any long config values
5. Wait for "done phase N" + voice/integration test result before advancing
