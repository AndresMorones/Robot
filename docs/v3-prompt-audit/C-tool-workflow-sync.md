# Audit C — Tool / Workflow Sync (v3 prompt vs v14→v15 HR workflow)

**Date:** 2026-04-27
**Inputs:** `prompts/voice-agent-system-prompt-v3.md`, `docs/v15-book-load-tool-spec.md`, `docs/v15-two-table-schema.md`, `docs/v15-architecture-2026-04-27.md`, `docs/iac/ui-build-guide.md`, `docs/v14-classifier-design-2026-04-27.md`, memory files (`project_v14_loop_architecture.md`, `reference_hr_post_call_webhook_schema.md`, `reference_hr_create_popup_schema.md`, `reference_hr_run_python_node_ui.md`, `reference_hr_procedural_quirks.md`, `project_call_end_tool_pattern.md`).
**Method:** Documentation-only. No live HR probe. All findings cite repo docs or canonical memory file names.

---

## Section 1 — Tools v3 prompt references

| Tool name | Section in v3 | Purpose | Required parameters per v3 | Required behavior per v3 |
|---|---|---|---|---|
| `verify_carrier` | §3, §4 | FMCSA lookup; gates everything downstream | `mc_number` (string, digits only) | Called only after MC readback passes; one retry on `content: null`; hard 7-check AND-gate gates all downstream tools |
| `find_available_loads` | §6 | Single-load lookup by reference number | `reference_number` (exact casing, no whitespace) | Only when carrier names a specific load id; never on random digits in lane utterance |
| `search_loads_by_lane` | §5, §6 | Default lane search across `loads` Twin table | `origin_state`, `origin_city`, `destination_state`, `destination_city`, `equipment_type` (5-enum), `pickup_window` (ISO 8601) | Hard cap 3 calls per conversation; never broaden silently; multi-state regional uses `destination_state=""` |
| `calculate_rate` | §8.3, §14 | Optional sidecar — adjusts floor when pickup ≤24h away | `loadboard_rate` (number) | Called ONCE per call only when pickup within 24h of `Time.Now`; returns `adjusted_floor`; silent (never spoken) |
| `book_load` | §9, §10 | Mid-call booking write to `bookings` table | `load_id` (string), `mc_number` (string), `apply_rate` (integer dollars) | Fires THE MOMENT clean yes lands at agreed rate, BEFORE any "deal"/"transfer" wording; multi-load = one fire per agreement; max 2 retries per `(load_id, mc_number)`; idempotency via `UNIQUE(call_id, load_id)` |

Indirectly-referenced HR built-ins (not LLM tools but workflow nodes the prompt assumes):

- `Time.Now` workflow variable — §0 calendar anchor.
- Workflow vars `agent_name`, `company_name`, `negotiation_floor_pct`, `max_negotiation_rounds` — §1, §8.
- Transfer Popup (Initiate New Contact / mock transfer endpoint) — §10 spec-literal wording.

---

## Section 2 — Tools currently configured in v14 workflow

Per `docs/iac/ui-build-guide.md` Phase 2 + memory `project_v14_loop_architecture.md`:

| Tool name | Type | Status |
|---|---|---|
| `verify_carrier` | Tool → Predefined Webhook GET (FMCSA `mobile.fmcsa.dot.gov` URL with `webKey`) | CONFIGURED |
| `find_available_loads` | Tool → Read-from-Twin (table `loads`, filter `load_id equals @reference_number`) | CONFIGURED |
| `search_loads_by_lane` | Tool → Read-from-Twin (table `loads`, 5 equality filters, limit 20, order `pickup_datetime asc`) | NEEDS-UPDATE — current build has 6 params; v3 prompt expects same 6 but `origin_city`/`destination_*` should be optional/empty-string-tolerant per memory `reference_hr_twin_empty_string_filter.md` (Twin treats empty string as literal `''` match). Confirm filters skip when value is empty. |
| `negotiate_evaluate` | Tool → Run Python sidecar (`Calculate Carrier Cost`, 4587-char Python, 7 input keys) | DROP — v3 prompt removes this. Negotiation math now lives in the prompt body (§8). |
| `calculate_rate` | Run Python sidecar (NOT YET BUILT) | NEW — v3 prompt §8.3 introduces this as an OPTIONAL sidecar. Single param `loadboard_rate`. Returns `adjusted_floor`. Only fires when pickup ≤24h away. |
| `book_load` | Tool → Predefined Webhook POST → HR Write-to-Twin (`bookings` table) | NEW — central v15 pivot per `docs/v15-book-load-tool-spec.md`. |

Post-call chain currently in v14 (per `ui-build-guide.md` Phase 3 + memory `project_v14_loop_architecture.md`):

| Component | Type | Status under v15 |
|---|---|---|
| Initiate New Contact (Transfer Popup, `phone_number=MC-pending`) | Predefined integration | CONFIGURED — keep, retarget to spec-literal transfer wording per §10 |
| Classify (Outcome) | AI Classify | DROP — consolidated into single Case Health Score / Extract node per `v14-classifier-design-2026-04-27.md` §"Decommissioned" |
| Extract | AI Extract (14 params in v14, dropping to 5 in v3) | NEEDS-UPDATE — repoint to `prompts/ai-extract-schema-v3.md` (5 fields, JSON Schema strict mode) |
| Case Health Score | AI Extract-typed node (5 params in v14) | NEEDS-UPDATE — consolidates into the Extract node above per v3 schema (single LLM call emits all 5 fields) |
| Classify Sentiment | AI Classify | DROP — consolidated into Extract |
| Write to Twin (calls_log, 18 cols) | HR Twin Write | NEEDS-UPDATE — drop to 13 cols per `docs/v15-two-table-schema.md`; reparent to Extract; remove `pitched_loadboard_rate`, `agreed_rate`, `num_negotiation_rounds`, `load_id`, `equipment_type` (now in `bookings`) |
| Loop / Custom Code / Paths | v14 multi-load fan-out | DROP — never built per memory `project_v14_loop_architecture.md`; the v15 pivot removes them outright |

---

## Section 3 — Tool inventory diff

### ADD list

1. **`book_load`** — P0. Required to land any booking under v15. Spec already locked at `docs/v15-book-load-tool-spec.md`. Webhook POST → Write-to-Twin chip targeting `bookings`. Three params (`load_id`, `mc_number`, `apply_rate`). Idempotency via Twin `UNIQUE(call_id, load_id)`.
2. **`calculate_rate`** (Run Python sidecar) — P2 / OPTIONAL. v3 prompt §8.3 has a soft fallback: if the sidecar errors or pickup is >24h out, the agent falls back to the static formula `F = L × (1 − negotiation_floor_pct)`. Ship MVP without it; defer until urgency-pricing analytics demand it. Single param `loadboard_rate`. Returns `{adjusted_floor: number}`.

### MODIFY list

1. **`search_loads_by_lane`** — P1. Confirm that the 4 optional location filters skip when empty (multi-state regional pattern in §6 fires `destination_state=""`). Memory `reference_hr_twin_empty_string_filter.md` warns Twin treats empty string as literal `=''`. Either (a) drop the filter from the Twin Read when the param is empty, or (b) push an `OR equals ''` predicate, or (c) handle in agent reasoning. Recommend option (a).
2. **AI Extract node** — P0. Replace the v14 14-param schema with the v3 5-field schema (`call_outcome`, `sentiment`, `case_health_score`, `audit_remarks`, `fmcsa_eligibility_failure_reason`). Switch to JSON Schema strict mode per `reference_hr_extract_strict_schema_rules.md`.
3. **Write-to-Twin (calls_log)** — P0. Drop to the 13-column shape in `docs/v15-two-table-schema.md`. Re-parent from Classify Sentiment → Extract. Drop `pitched_loadboard_rate`, `agreed_rate`, `num_negotiation_rounds`, `load_id`, `equipment_type`, `sentiment_start`, `sentiment_trajectory`, `p90_latency_ms` (last three were nice-to-have v14 additions; not in v15 schema).
4. **Voice Agent prompt body** — P0. Replace existing prompt with `prompts/voice-agent-system-prompt-v3.md` body verbatim. Initial message stays in the Voice Agent node (`Thank you for calling {{company_name}}, this is {{agent_name}}. How can I help?`) per §2.

### DROP / AUDIT list

1. **`negotiate_evaluate` tool** — P0 DROP. v3 §8 moves negotiation math into the prompt body. The Run Python sidecar `Calculate Carrier Cost` is no longer referenced. Remove the tool node + its child Python node. (Optional: rename the Run Python child + repurpose it as `calculate_rate` — saves rebuilding from scratch.)
2. **Classify (Outcome) node** — P0 DROP. Consolidated into Extract under v3.
3. **Classify Sentiment node** — P0 DROP. Consolidated into Extract under v3.
4. **Loop / Custom Code / Paths nodes** — N/A. Per memory `project_v14_loop_architecture.md` these were never built; the v14→v15 pivot landed before that branch shipped. No deletion needed unless prototype scaffolding remains in the workflow editor.

---

## Section 4 — Missing tools / capabilities to consider

Brainstormed against the v3 prompt's gaps. Each candidate evaluated for "is the value worth the HR-side build cost given MVP scope?".

| Tool | Purpose | Params | When agent calls | Tier | Complexity |
|---|---|---|---|---|---|
| `get_carrier_history` | Twin Read against `bookings ⋈ calls_log` filtered by `mc_number`; returns prior call count, last booking date, last sentiment, total revenue | `mc_number` | Right after FMCSA passes — lets the agent recognize repeat callers ("welcome back, last we had you on Dallas-Atlanta") | **Tier-2** | Low — Read-from-Twin filter, one node |
| `submit_callback` | Persist a callback request when no-match or FMCSA-pass-but-walked away. Writes to a small `callbacks` table | `mc_number`, `callback_phone`, `lane_summary`, `equipment_type` | After §6 zero-match relaxation exhausted, before polite end | **Tier-2** | Medium — needs new `callbacks` Twin table; in MVP captured as transcript-only field |
| `get_load_details` | Re-fetch a full load row by `load_id` after agreement, in case the cached `search_loads_by_lane` snapshot is stale (rate change, claimed, hold flag) | `load_id` | Optional pre-flight check immediately before `book_load` | **Tier-3** | Low (mirror of `find_available_loads`) but adds latency at the worst moment |
| `check_load_availability` | Atomic "is this load still bookable?" — cheaper variant of `get_load_details`, returns boolean + reason | `load_id` | Same trigger as above | **Tier-3** | Low; only useful once `loads` table gets a `claimed_by` column |
| `get_lane_market_rate` | Returns recent booked-rate distribution (median, p25, p75) on a lane for context during negotiation | `origin_state`, `destination_state`, `equipment_type` | Round 2/3 when sentiment is positive but gap is wide | **Tier-3** | Medium — needs analytic SQL window over `bookings` |
| `submit_complaint` | Capture frustrated-carrier escalation, writes to `complaints` table or sets a flag on `calls_log` | `mc_number`, `complaint_summary` | When sentiment turns very_negative and carrier asks to speak to a manager | **Tier-3** | Medium — overlaps with `audit_remarks` already produced post-call |
| `check_pickup_urgency` | Date math sidecar — returns hours-until-pickup given an ISO datetime + `Time.Now` | `pickup_datetime` | Internal helper for `calculate_rate` deferral logic in §8.3 | **Tier-3** | Trivial; arguably belongs inline in the prompt or in the `calculate_rate` body |
| `check_blacklist` | Look up MC against an internal blacklist table (carriers we've banned) | `mc_number` | Right after FMCSA pass, before pitch | **Tier-3** | Low — Read-from-Twin against a `carrier_blacklist` table; needs the table to exist |
| `extend_negotiation_round` | Manager-override sidecar: agent flags a high-value carrier for additional rounds beyond `max_negotiation_rounds` | `load_id`, `current_offer`, `manager_override_reason` | Only on flagged repeat callers when sentiment is positive at round 3 | **Tier-3 (post-MVP)** | Medium; opens jailbreak surface |
| `finalize_call` | "Call-end terminal tool" pattern per memory `project_call_end_tool_pattern.md` — agent fires once at end, captures structured terminal state, then HR ends the call gracefully | `terminal_state` (enum) | Right before transfer wording | **Tier-2 (polish)** | Low; solves awkward "transferring..." silence |

**Recommendation for MVP build:** ADD only `book_load` (already locked). Optionally `calculate_rate` if pickup-urgency analytics are wanted at submission time. Everything else stays Tier-2/Tier-3 because the prompt + post-call Extract chain already cover their information needs at MVP grain.

---

## Section 5 — HR built-in components — re-evaluation under v15

Memory note: the v14 classifier doc does not in fact contain a "Considered + deferred" matrix; the closest equivalent is the implicit deferral list in `project_v14_loop_architecture.md` and the skip-list in `docs/iac/ui-build-guide.md`. Re-evaluating each component against v15:

| HR component | v14 status | v15 re-evaluation | Recommendation |
|---|---|---|---|
| **Transfer Popup** (Initiate New Contact) | CONFIGURED — Phase 3a | Still required for §10 spec-literal transfer wording | **Keep — confirm `phone_number=MC-pending` and TTL=10d are still acceptable defaults** |
| **Capacity nodes** (Past Capacity, Find Matching Carriers) | Skipped per UI-build skip-list | v15 doesn't change the analysis — these are enrichment nodes that overlap with `get_carrier_history`. Carrier history isn't a Tier-1 KPI. | Keep deferred |
| **Conditions / Paths nodes** | Built v14 for multi-load fan-out, dropped in v15 pivot | v15 architecture is a flat DAG — Voice Agent → tools → Voice Agent end → Extract → Write-to-Twin | Keep deferred. Re-activate only when a real branching post-call decision shows up |
| **Loop nodes** | Planned v14, never built | v15 pivots away from per-load looping | Keep deferred |
| **Phone Calls Direct transfer** | Skipped (mock transfer per spec) | Spec literal wording stays the requirement: *"Transfer was successful and now you can wrap up the conversation."* | Keep deferred — out of MVP scope per `docs/FDE-TECHNICAL-CHALLENGE.md` line 41 |
| **Email / Text** | Skipped | No requirement in v3 prompt or spec | Keep deferred |
| **Schedule Sleep** | Skipped | Useful for callback follow-up Tier-2; not in v15 | Keep deferred |
| **Locate** | Skipped | Useful for IP-based location enrichment of inbound caller; not in v15 | Keep deferred |
| **Data → Contacts / Memories** | Skipped | Repeat-caller history is a Tier-2 want; would be served by `get_carrier_history` | Keep deferred — but Memories is the cleanest HR-native path if we re-activate later |
| **AI Extract → JSON Schema strict mode** | New in v15 | Required by `prompts/ai-extract-schema-v3.md` per `reference_hr_extract_strict_schema_rules.md` | **Activate now** |
| **Predefined Webhook (b329e750-…)** | Used for `verify_carrier` | Reuse for `book_load` per `docs/v15-book-load-tool-spec.md` Step 1 | **Activate now for `book_load`** |

---

## Section 6 — Wiring punch list (HR UI build, post-prompt-publish)

Ordered by dependency. Items that must run UI-only per memory `reference_hr_post_batch_corruption.md`. Use the `@` picker for every variable reference per memory `feedback_hr_variable_resolution.md`.

1. **Twin DDL — create `bookings` table** (Twin SQL editor, single-statement-at-a-time per memory `reference_hr_procedural_quirks.md`). Run `data/twin_schema_v15_bookings.sql`. Verify `SELECT COUNT(*) FROM bookings = 0`.
2. **Twin DDL — `calls_log` cleanup**. Run `data/twin_schema_v15_calls_log_cleanup.sql`. Drops 8 columns and promotes `call_id` to `UNIQUE`. Verify with `information_schema.columns`.
3. **Update Voice Agent prompt body**. HR UI → workflow editor → Voice Agent → Prompt child node → Prompt body field → paste body of `prompts/voice-agent-system-prompt-v3.md`. Confirm initial message stays as `Thank you for calling {{company_name}}, this is {{agent_name}}. How can I help?` (use `@` picker for the two variables).
4. **Delete `negotiate_evaluate` tool node + its `Calculate Carrier Cost` Run Python child** (or rename to repurpose as `calculate_rate` if shipping the optional sidecar — see step 9).
5. **Add `book_load` tool node under Voice Agent → Prompt**. Component: Predefined Webhook (`b329e750-2e0e-4618-ba65-e04bb6a93c5f`). Configure per `docs/v15-book-load-tool-spec.md` Step 2:
   - Tool name: `book_load`
   - Description: paste verbatim from spec
   - Parameters (3): `load_id` (string), `mc_number` (string), `apply_rate` (integer)
   - Webhook URL: HR Twin Write endpoint for `bookings` (or proxy through FastAPI if going that route)
   - Headers: `Authorization: Bearer <Twin token>`, `Content-Type: application/json`
6. **Add Write-to-Twin under `book_load`** (component "Write to Twin", parent = the `book_load` tool node). Target table `bookings`. Column mapping (use `@` picker for each, stringify numeric per `reference_hr_procedural_quirks.md`):
   - `call_id` ← `@<Voice Agent>.call_id`
   - `mc_number` ← `@book_load.mc_number`
   - `load_id` ← `@book_load.load_id`
   - `apply_rate` ← `@book_load.apply_rate` (stringify per quirk)
   - `created_at` ← omit (server `DEFAULT NOW()`)
7. **Delete the v14 `Classify` (Outcome) node**. Children re-parent to its grandparent.
8. **Delete the v14 `Classify Sentiment` node**. Re-parent its child `Write to Twin` to the new Extract node (step 10).
9. *(OPTIONAL — defer if not shipping urgency pricing in MVP)* **Add `calculate_rate` Run Python sidecar** under Voice Agent → Prompt. Component: Tool → Run Python child. Tool config:
   - Name: `calculate_rate`
   - Description: "Compute pickup-urgency-adjusted floor when pickup is within 24 hours. Silent helper; do not speak aloud."
   - Param: `loadboard_rate` (number)
   - Run Python child: input data `{loadboard_rate, pickup_datetime, negotiation_floor_pct}`; code computes urgency multiplier and returns `{adjusted_floor: number}`. Per `reference_hr_run_python_node_ui.md` use `output = {…}` not `with` blocks; no networking imports.
10. **Update AI Extract node** (parent: Initiate New Contact / Transfer Popup, per existing chain). Switch to JSON Schema strict mode. Paste schema + prompt from `prompts/ai-extract-schema-v3.md`. Five fields only: `call_outcome`, `sentiment`, `case_health_score`, `audit_remarks`, `fmcsa_eligibility_failure_reason`. Bind input `@<Voice Agent>.transcript` via `@` picker.
11. **Reparent Write-to-Twin (calls_log)** to the Extract node (delete old parent link to Classify Sentiment).
12. **Update Write-to-Twin (calls_log) column map** to the v15 13-column shape from `docs/v15-two-table-schema.md`:
    - `call_id` ← `@<Voice Agent>.call_id`
    - `mc_number` ← `@Extract.response.<inferred from transcript>` (NB: v3 Extract drops `mc_number` as a separate field — pull from `@<Voice Agent>` envelope or restore field)
    - `carrier_name` ← same caveat (v3 schema drops `carrier_name`; either restore in Extract schema or pull from FMCSA branch). **AUDIT-FLAG:** v15 schema lists `mc_number` and `carrier_name` as calls_log columns, but v3 Extract schema dropped both. Resolve before publish — either re-add to Extract schema or wire from a different source.
    - `call_outcome` ← `@Extract.response.call_outcome`
    - `sentiment` ← `@Extract.response.sentiment`
    - `case_health_score` ← `@Extract.response.case_health_score`
    - `audit_remarks` ← `@Extract.response.audit_remarks`
    - `fmcsa_eligibility_failure_reason` ← `@Extract.response.fmcsa_eligibility_failure_reason`
    - `callback_phone` ← AUDIT-FLAG (dropped from v3 Extract per schema explicit "deliberately does NOT capture")
    - `duration_seconds` ← `@<Voice Agent>.duration`
    - `transcript` ← `@<Voice Agent>.transcript`
    - `created_at` ← omit (server default)
13. **Test web call (single-load happy path)** per `docs/v15-book-load-tool-spec.md` Scenario 1. Verify one row in `bookings`, one row in `calls_log`, `book_load` fired BEFORE transfer wording in the transcript.
14. **Test web call (multi-load)** per Scenario 2. Verify two rows in `bookings` for one `call_id`.
15. **Test web call (FMCSA fail)** per Scenario 7. Verify zero rows in `bookings`, one row in `calls_log` with `call_outcome=carrier_not_qualified`.
16. **Test web call (book_load idempotency)** per Scenario 5 — fire twice with same `(call_id, load_id)`, verify `UNIQUE` rejects the second cleanly.
17. **Publish to Development**, capture web-call URL into `docs/references/happyrobot/web-call-url.txt`.

Total MVP punch-list items: **17** (15 if `calculate_rate` skipped).

---

## Section 7 — Workflow topology validation

### Post-pivot DAG

```
Web call trigger
   └─> Voice Agent (with Prompt child)
         ├─ tool: verify_carrier        → Webhook GET (FMCSA)
         ├─ tool: find_available_loads  → Read-from-Twin (loads)
         ├─ tool: search_loads_by_lane  → Read-from-Twin (loads)
         ├─ tool: calculate_rate (opt)  → Run Python (sidecar)
         └─ tool: book_load             → Webhook POST → Write-to-Twin (bookings)

   (call ends — Voice Agent terminates)

   └─> Initiate New Contact (Transfer Popup, mock transfer)
         └─> AI Extract (5-field strict JSON Schema, parent of post-call write)
               └─> Write to Twin (calls_log, 13 cols)
```

Valid DAG: yes. No cycles. Each node has at most one parent (HR DAG rule). Tool sub-nodes hang off the Prompt and resolve mid-call without blocking the post-call chain.

### Orphan / leftover nodes from v14 to delete

- `Classify` (Outcome) — DELETE (consolidated into Extract).
- `Classify Sentiment` — DELETE (consolidated into Extract).
- `Case Health Score` standalone node — DELETE if a separate node exists; v3 Extract subsumes it.
- `negotiate_evaluate` tool + `Calculate Carrier Cost` Python child — DELETE (or repurpose Python child as `calculate_rate`).
- Loop / Custom Code / Paths — verify these were never built and remove any prototype remnants.

### Mid-call book_load chain

```
Voice Agent (Prompt body §9 trigger)
   → book_load tool node fires
       → Webhook POST to Twin write endpoint (or via FastAPI proxy)
           → Write-to-Twin chip writes one row to `bookings`
       ← tool returns {status: "booked"} (or non-success → retry once → fallback line)
   → Voice Agent resumes; speaks recap + spec-literal transfer wording
```

Confirmed: `book_load` returns control to the Voice Agent. The Voice Agent then proceeds to §10 transfer wording. Idempotency: `UNIQUE(call_id, load_id)` on the Twin side absorbs duplicate fires.

### Post-call chain

```
Voice Agent end
   → Initiate New Contact (Transfer Popup integration, spec-literal wording)
   → AI Extract (5 strict fields)
   → Write to Twin (calls_log, 13 cols)
   → Workflow ends
```

Confirmed: linear, no branching, no Loop. One row per call lands in `calls_log`. Booking rows already landed mid-call.

### AUDIT-FLAGS surfaced during validation

1. **`mc_number` + `carrier_name` source mismatch**: v15 `calls_log` schema requires both columns, but v3 Extract schema (`prompts/ai-extract-schema-v3.md`) explicitly drops them. Either re-add to Extract or wire from `@<Voice Agent>` envelope / FMCSA branch. **P0 — resolve before publish.**
2. **`callback_phone` source mismatch**: v15 `calls_log` schema lists it; v3 Extract schema explicitly drops it ("Re-add when no-match callback funnel becomes Tier-1"). Either restore in Extract or accept the column will be NULL at MVP. **P1 — decide before publish.**
3. **`search_loads_by_lane` empty-string filters**: per memory `reference_hr_twin_empty_string_filter.md`, Twin's `equals ''` is literal. Verify the multi-state regional pattern in §6 actually returns rows. **P1 — test before publish.**
4. **HR Voice Agent `call_id` exposure**: confirm the `@` picker exposes a `call_id` variable on the Voice Agent output (used by the `book_load` Write-to-Twin chip). If not, fall back to `current.run_id` per `ui-build-guide.md` Phase 4 column map. **P0 — verify before testing.**

---

## Output report

- **Tools to ADD**: 2 (`book_load` P0, `calculate_rate` P2 optional).
- **Tools to MODIFY**: 4 (`search_loads_by_lane`, AI Extract, Write-to-Twin calls_log, Voice Agent prompt body).
- **Tools to DROP**: 3 (`negotiate_evaluate` + Python child, `Classify` Outcome node, `Classify Sentiment` node).
- **MVP punch-list items**: 17 (or 15 without optional sidecar).
- **Top 3 Tier-2 candidate tools**: `get_carrier_history` (repeat-caller recognition, low complexity), `submit_callback` (no-match capture funnel, medium complexity), `finalize_call` (terminal-state pattern fixes awkward transfer silence, low complexity).
- **AUDIT-FLAGS to resolve before publish**: 4 (mc_number/carrier_name source, callback_phone source, search_loads_by_lane empty-string filters, Voice Agent `call_id` exposure).
