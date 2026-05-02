# v15 `book_load` Tool — design spec

Locked 2026-04-27 evening as part of the v14 → v15 architecture pivot.

## Purpose

Replace the post-call "extract a `loads_discussed` array" pattern with a mid-call tool call from the voice agent. The moment the carrier and the agent agree on a final rate for a specific load, the agent fires `book_load`, which writes one row to the `bookings` table via an HR Write-to-Twin component. Each agreement is a separate tool fire.

Spec quote driving the placement (verbatim from `docs/FDE-TECHNICAL-CHALLENGE.md` line 41):

> "If a price is agreed, transfer the call to a sales rep. Transfer is out of scope as it won't work with the web call, you can mock a message like 'Transfer was successful and now you can wrap up the conversation'."

`book_load` fires BEFORE the mock-transfer wording — the booking has to land in the database before the call ends, otherwise the agreement is lost on a hangup.

## Tool name

`book_load`

## Tool description (what the HR LLM sees on the Voice Agent's tool list)

```
Books a freight load for a verified carrier. Call this the moment the carrier and you reach final agreement on a rate for a specific load. This is a hard requirement — the booking is not committed to our records until this tool returns success. Call BEFORE confirming the deal aloud or saying any "transferring you" wording. On multi-load calls, fire one book_load per agreed load.

Pre-conditions: the FMCSA 7-check verification step must have already passed for this carrier earlier in this call. The load_id must come from the search_loads_by_lane or find_available_loads result set you already pitched in this call — never invent. The apply_rate must be at or above the floor; never propose a value below it.
```

Keep the description tight. The HR LLM uses the description to decide WHEN to call the tool, so anchoring it to "the moment of agreement" + "before any deal/transfer wording" is load-bearing.

## Parameter table

| Name | Type | Description (what the LLM sees) | Example | Carrier-speech-to-canonical examples |
|---|---|---|---|---|
| `load_id` | string | The load reference number you pitched. Use exact casing returned by search_loads_by_lane or find_available_loads (typically `LOAD-XXXX`). Never invent. Strip whitespace. | `"LOAD-0188"` | Agent pitched "LOAD-0188" → `"LOAD-0188"`. Pitched "LOAD dash zero one eight eight" (ASR variant) → `"LOAD-0188"`. Pitched "load forty-two" but search returned `"LOAD-0042"` → `"LOAD-0042"` (use the canonical form from the tool result, not the carrier's shorthand). |
| `mc_number` | string | The carrier's MC number, digits only. Same value passed to verify_carrier earlier in this call. No "MC" prefix, no spaces, no dashes. | `"148373"` | Carrier said "MC 148373" → `"148373"`. Carrier said "MC dash 250819" → `"250819"`. Carrier said "MC 47.11" → `"4711"` (already cleaned during MC capture in §3 of the prompt). |
| `apply_rate` | integer | The final agreed-upon rate in whole dollars. No currency symbol, no decimals, no commas, no thousand separators. The number you and the carrier converged on, NOT the original loadboard rate (unless they accepted at listed). | `2328` | Agreed at "$2,328" → `2328`. Agreed at "twenty-three twenty-eight" → `2328`. Agreed at "twenty-five hundred" → `2500`. Agreed at listed rate of $2,400 → `2400`. Never `2328.00`, never `"$2,328"`, never `"2,328"`. |

All three parameters are required. The HR LLM should reject internally if any is missing or empty, not call with a placeholder.

## Output

The tool returns a status field. Treat as success if status is `"booked"` (or HTTP 2xx if invoked as a webhook). Treat anything else as failure for retry purposes.

The Write-to-Twin component downstream of `book_load` is what actually inserts into the `bookings` table. The tool itself is the trigger — the persistence is the Twin write. Idempotency is enforced by the `UNIQUE (call_id, load_id)` constraint on `bookings` (per `docs/v15-two-table-schema.md`); a duplicate fire returns the same success state without double-writing revenue.

## When-to-call rule (hard rule for the voice prompt)

Call `book_load` exactly when ALL of these are true:

1. The 7-check FMCSA AND-gate (§4 of voice-agent-system-prompt-v3) passed earlier in this call.
2. You pitched a specific load with a specific listed rate.
3. The carrier and you converged on a final rate (at listed, or after up to 3 negotiation rounds).
4. The carrier said an unambiguous yes / done / "I'll take it" / "let's do it" / equivalent at that final rate.

Ambiguous signals ("uh-huh", "sure I guess", silence) — DO NOT fire. Ask one short confirm and wait for clean yes.

The full hard-rule text lives in §9 of `prompts/voice-agent-system-prompt-v3.md`. This spec is the tool-side mirror.

## When NOT to call

- Before the FMCSA 7-check passed.
- With a `load_id` that wasn't pitched in this call.
- With an `apply_rate` below the floor `F`.
- For the same `(load_id, mc_number)` pair more than twice (idempotency key).
- On ambiguous yes signals.
- "Just to test the booking flow" — there is no test fire; every fire writes to bookings.

## Failure handling

| Situation | Agent move |
|---|---|
| First call returns failure (timeout, error, non-success status) | Brief filler ("one sec, system blip"). Re-fire `book_load` ONCE with the same three parameters. |
| Second call also fails | Stop retrying. Speak the dispatch fallback: *"Tell you what — let me get my dispatch team to confirm this directly."* Then proceed to the spec's mock transfer wording so the carrier is never stuck on hold. The post-call audit_remarks captures the unbooked-but-agreed state for review. |
| Tool returns success on retry | Resume the §10 transfer flow. |

Hard caps: never more than 2 attempts per `(load_id, mc_number)`. Never escalate the failure to the carrier with internal-system language. The fallback line treats it as a routine handoff.

## HR UI build steps

The tool lives as a child node under the Voice Agent prompt node. HR's component naming for this pattern is "Tool" with an HTTP webhook backend that fires the Write-to-Twin component.

### Step 1 — Add the tool to the Voice Agent

1. Open `inbound-carrier-v15` in the HR workflow editor.
2. Click the Voice Agent node.
3. In the right-hand config pane, scroll to the "Tools" section.
4. Click "+ Add tool".
5. Pick the **Predefined Webhook** template (HR component id `b329e750-2e0e-4618-ba65-e04bb6a93c5f`) — per memory `reference_hr_procedural_quirks.md`, prefer Predefined Webhook over Incoming Webhook ~90% of the time when the payload fields are known.

### Step 2 — Configure the tool node

1. Tool name: `book_load` (this is the name the LLM sees in the tool list and uses to invoke).
2. Tool description: paste the description block from this doc verbatim.
3. Parameters: add three parameters in this order with the types and descriptions from the parameter table above. Use the @ picker for any HR variable references in descriptions; do NOT hand-type `{{var}}` (memory `feedback_hr_variable_resolution.md`).
4. Webhook URL: point at the Write-to-Twin endpoint for the `bookings` table. The body shape is `{ "load_id": "{{load_id}}", "mc_number": "{{mc_number}}", "apply_rate": "{{apply_rate}}", "call_id": "{{<call_id_var>}}" }`. Note `apply_rate` is stringified for the Twin POST per memory `reference_hr_procedural_quirks.md` (numeric values must be stringified for the HR Twin POST endpoint even when the column type is numeric).
5. Headers: `Authorization: Bearer <Twin token>`, `Content-Type: application/json`.

### Step 3 — Wire the Write-to-Twin component

1. The Twin write is the implicit body of the webhook above. The target table is `bookings` (per `docs/v15-two-table-schema.md`).
2. Column mapping in the Twin POST body:
   - `call_id` ← HR call_id variable (use @ picker)
   - `mc_number` ← `book_load.mc_number`
   - `load_id` ← `book_load.load_id`
   - `apply_rate` ← `book_load.apply_rate` (stringified)
   - `created_at` ← server default `NOW()` (do NOT pass from HR; the Twin DDL handles it)
3. Idempotency: rely on the `UNIQUE (call_id, load_id)` constraint. A duplicate fire returns success without double-writing.

### Step 4 — Hard-rule reference in the voice prompt

The voice agent's behavior is pinned by §9 of `prompts/voice-agent-system-prompt-v3.md`. No additional HR-side wiring required for the "fire before transfer" rule — it lives in the prompt.

### Step 5 — Test

Run the test scenarios in the next section before enabling the version on the production phone number.

## Test scenarios

### Scenario 1 — Single-load happy path

1. Carrier calls, MC 250819, dry van, Dallas → Atlanta, tomorrow morning.
2. FMCSA passes. Agent pitches LOAD-0001 at $2,400. Carrier accepts at listed.
3. **Expected**: agent fires `book_load("LOAD-0001", "250819", 2400)` BEFORE saying any "we have a deal" or "transferring" wording. Write-to-Twin inserts one row into `bookings`. Tool returns success.
4. Agent then speaks the recap + spec-literal transfer wording.
5. Post-call: `bookings` table has one row `(call_id, "250819", "LOAD-0001", 2400)`. `calls_log` has one row with `call_outcome="load_booked"`.

### Scenario 2 — Multi-load (carrier books two in one conversation)

1. Carrier calls, MC 305472, reefer, Miami. FMCSA passes.
2. Agent pitches LOAD-0003 Miami → NYC at $4,800. Carrier negotiates to $4,580 in 2 rounds. Carrier says "Done."
3. **Expected fire 1**: `book_load("LOAD-0003", "305472", 4580)` — succeeds.
4. Agent: "$4,580 it is. Anything else you want to look at?"
5. Carrier: "Yeah, what else you got out of NYC heading west?"
6. Agent searches, pitches LOAD-0017 NYC → Chicago at $1,950. Carrier accepts at listed.
7. **Expected fire 2**: `book_load("LOAD-0017", "305472", 1950)` — succeeds.
8. Agent then speaks the recap + spec-literal transfer wording (only after the second booking).
9. Post-call: `bookings` table has TWO rows for the same `call_id` with different `load_id` values. `calls_log` has one row with `call_outcome="load_booked"`. `audit_remarks` notes "two loads booked" or summarizes the more material one.

### Scenario 3 — Retry on failure

1. Carrier calls, agreement reached at $2,328 on LOAD-0001.
2. Agent fires `book_load("LOAD-0001", "148373", 2328)`. Tool returns failure (simulated 5xx from Twin).
3. **Expected**: agent says brief filler ("one sec, system blip"). Re-fires the same call once.
4. Second call succeeds. Agent proceeds to recap + transfer.
5. Post-call: one row in `bookings` (the second fire's success — first fire never wrote, since the failure was on the Twin side).

### Scenario 4 — Retry then dispatch fallback

1. Same setup as scenario 3.
2. First fire fails. Second fire also fails.
3. **Expected**: agent does NOT fire a third time. Says: *"Tell you what — let me get my dispatch team to confirm this directly."*
4. Agent then says spec-literal transfer wording. Call ends.
5. Post-call: zero rows in `bookings` for this `call_id`. `calls_log` row has `call_outcome="load_booked"` (the agreement happened) but `audit_remarks` flags the unbooked-but-agreed state ("Agreement reached on LOAD-0001 at $2,328 but booking handoff failed twice; dispatch team to confirm manually."). `case_health_score` deducted lightly (failure was system-side, not agent-side).

### Scenario 5 — Idempotency on webhook retry

1. Carrier calls, agreement reached at $2,328 on LOAD-0001.
2. Agent fires `book_load`. Tool sends webhook to Twin. Twin writes the row successfully but the response packet is lost on the network — HR sees a timeout and retries the same webhook.
3. **Expected**: second webhook hits the `UNIQUE (call_id, load_id)` constraint, Twin returns the existing row's id, no double-write of revenue.
4. Post-call: exactly one row in `bookings` for this `(call_id, load_id)` pair.

### Scenario 6 — Ambiguous yes (DO NOT fire)

1. Carrier responds to pitch with "uh-huh, mmm... sure".
2. **Expected**: agent does NOT fire `book_load`. Agent asks one confirm: "Just want to make sure — $2,400 on LOAD-0001, you're a yes?"
3. If clean yes lands → fire. If carrier hesitates further → return to negotiation or pivot.

### Scenario 7 — FMCSA failed (book_load must NOT fire)

1. Carrier calls, MC 148373, FMCSA returns inactive (statusCode=I).
2. **Expected**: agent declines politely per §4 of the prompt. NEVER calls `book_load`. NEVER pitches a load.
3. Post-call: zero rows in `bookings`. `calls_log` row has `call_outcome="carrier_not_qualified"`, `fmcsa_eligibility_failure_reason="INACTIVE"`.

## Pairs with

- `prompts/voice-agent-system-prompt-v3.md` — §9 (Booking flow) is the prompt-side mirror of this spec.
- `prompts/ai-extract-schema-v3.md` — drops `loads_discussed`; per-load detail lives in `bookings` now.
- `docs/v15-two-table-schema.md` — calls_log + bookings table definitions, idempotency rationale, ER diagram.
- Memory: `feedback_analytics_friendly_enums.md`, `feedback_tool_param_normalization.md`, `feedback_hr_variable_resolution.md`, `reference_hr_procedural_quirks.md`.
