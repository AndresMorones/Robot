# v15 `query_loads` Tool — design spec

Locked 2026-04-27 evening as part of the v14 → v15 architecture pivot. Replaces the prior pair of tools (`search_loads_by_lane` + `find_available_loads`) with a single merged tool that handles both single-load lookup and lane search.

## Tool overview

`query_loads` is the only load-discovery tool the voice agent uses. It runs in one of two modes depending on which parameters the agent fills in:

1. **Single-load lookup mode** — agent passes `load_id` and nothing else. Returns the single load row matching that reference (or empty if not found / already taken). Used when the carrier names a specific load ("calling about LOAD-0188") or when the agent re-pulls a record before booking (per §8.2 re-gather rule).
2. **Lane search mode** — agent passes any combination of origin / destination / equipment / pickup window filters. Returns matching loads from the load board, capped by the underlying Twin component. Used as the default discovery path when the carrier describes a lane.

The agent never has to choose a "mode" explicitly — it just fills in the params it has. **One Twin component, period** — a single Read-from-Twin child handles both modes by applying each filter only when its bound param is non-empty. Memory `reference_hr_twin_empty_string_filter.md` flags that HR Twin's empty-string equality is strict literal; this design relies on HR's per-filter "Skip if empty" / "Apply only if value present" configuration toggle. If HR's Read-from-Twin doesn't expose that toggle, the documented fallback (NOT a second component) is to drop all filters and let the agent reason over the full ≤500-row result set in-context — still one component, lower selectivity but functionally complete at our seed-data scale.

## Tool description (paste-ready for HR)

This is what the HR LLM sees on the Voice Agent's tool list. Paste verbatim:

```
Looks up freight loads from our load board. Use this tool whenever you need to surface load options to the carrier — either when the carrier names a specific load reference (single-load lookup) or when the carrier describes a lane and you need to surface matching options (lane search).

Two modes, one tool:

(1) SINGLE-LOAD LOOKUP — pass `load_id` only, leave the lane filters empty. Use when the carrier names a specific load like "calling about LOAD-0188" or "got anything else on load forty-two", or when you need to re-pull a load record before booking. Normalize the carrier's spoken reference to canonical form before calling: "load 1" → "LOAD-0001", "load forty-two" → "LOAD-0042", "L-O-A-D dash zero one nine two" → "LOAD-0192", "LOAD 188" → "LOAD-0188". Always uppercase "LOAD-", always 4-digit zero-padded suffix. Returns the single matching row or empty if not found / already taken. If empty, do NOT keep guessing other reference numbers — name the gap and offer to check the carrier's lane.

(2) LANE SEARCH — leave `load_id` empty, fill in any combination of origin_state, origin_city, destination_state, destination_city, equipment_type, pickup_window. Use as the default path when the carrier describes a lane ("I'm out of Dallas heading to Atlanta tomorrow morning, dry van"). Skip filters the carrier didn't specify — for "anywhere southeast" leave destination_state empty and reason over the returned rows in your head. Returns the top matching rows ranked by pickup time, then rate.

Pre-conditions: the FMCSA 7-check verification step must have already passed for this carrier earlier in this call. Never call this tool before verification clears.

Normalization rules for inputs:
- load_id — always uppercase "LOAD-" + 4-digit zero-padded suffix. "LOAD 188" / "load 188" / "load number one eighty-eight" → "LOAD-0188".
- origin_state / destination_state — USPS 2-letter uppercase code. "Texas" → "TX", "California" → "CA", "New York" → "NY". If the carrier said only a city ("Houston"), leave the state empty unless you can unambiguously infer it.
- origin_city / destination_city — title case, no state suffix. "dallas, tx" → "Dallas". "fort worth" → "Fort Worth".
- equipment_type — one of exactly: "dry van", "reefer", "flatbed", "stepdeck", "conestoga". Lowercased. Map carrier slang ("van" → "dry van", "step deck" / "drop deck" → "stepdeck", "reefer" / "refrigerated" / "temp control" → "reefer").
- pickup_window — ISO 8601 datetime "YYYY-MM-DDTHH:MM" anchored on Time.Now per §0 of the prompt. Never pass past datetimes. Never pass raw carrier-speech.

Output: an array of load rows (zero or more). Each row carries load_id, origin/destination city+state, equipment_type, pickup_datetime, loadboard_rate, weight, miles, num_of_pieces, dimensions, commodity, notes. Skip null fields silently when pitching aloud. Cap your pitch to 3 options per turn ranked by tightest pickup match.

Cap: max 3 lane-search calls per conversation. Single-load lookups don't count against this cap. Never broaden silently after a zero-result search — let the carrier choose what to relax.
```

## Parameter table

All parameters are optional individually, but the agent MUST pass at least one. The HR Read-from-Twin child filters on whichever fields are non-empty. (See HR UI build steps below for the empty-skip wiring.)

| Name | Type | Description (what the LLM sees) | Example | Carrier-speech-to-canonical |
|---|---|---|---|---|
| `load_id` | string | The load reference number when the carrier names a specific load. Always canonical "LOAD-" + 4-digit zero-padded suffix. Leave empty for lane search. | `"LOAD-0188"` | "load 1" → `"LOAD-0001"`. "load forty-two" → `"LOAD-0042"`. "LOAD 188" → `"LOAD-0188"`. "L-O-A-D dash zero one nine two" → `"LOAD-0192"`. "the first one you mentioned" → canonical id from prior pitch, never invent. |
| `origin_state` | string | USPS 2-letter uppercase state code for pickup. Leave empty if the carrier didn't specify or only gave a city. | `"TX"` | "Texas" → `"TX"`. "California" → `"CA"`. "outta New York" → `"NY"`. "Dallas" alone → leave empty (city-only) OR pass `"TX"` only if unambiguous. |
| `origin_city` | string | Pickup city in title case, no state suffix. Leave empty if the carrier only gave a state or region. | `"Dallas"` | "dallas, tx" → `"Dallas"`. "fort worth" → `"Fort Worth"`. "outta Houston" → `"Houston"`. |
| `destination_state` | string | USPS 2-letter uppercase state code for drop-off. Leave empty for multi-state regional searches ("anywhere southeast") and reason over the rows in-context. | `"GA"` | "Georgia" → `"GA"`. "anywhere southeast" → leave empty. "heading west" → leave empty, reason in-context. |
| `destination_city` | string | Drop-off city in title case, no state suffix. Leave empty if the carrier only gave a state or region. | `"Atlanta"` | "atlanta" → `"Atlanta"`. "the ATL" → `"Atlanta"`. "going up the east coast" → leave empty. |
| `equipment_type` | string | One of exactly: `dry van`, `reefer`, `flatbed`, `stepdeck`, `conestoga`. Lowercased. | `"dry van"` | "van" / "53-footer" → `"dry van"`. "reefer" / "refrigerated" / "temp control" → `"reefer"`. "step deck" / "drop deck" → `"stepdeck"`. "flat" / "deck" → `"flatbed"`. "tarped trailer" / "rolling tarp" → `"conestoga"`. |
| `pickup_window` | string | Earliest acceptable pickup datetime, ISO 8601 "YYYY-MM-DDTHH:MM" anchored on Time.Now. The Twin filters loads with `pickup_datetime >= pickup_window`. | `"2026-04-28T08:00"` | "tomorrow morning" → next-day 08:00 in Time.Now's year. "available now" → next hour. "Tuesday 2pm" → next Tuesday 14:00. "anytime" → tomorrow 08:00. Never raw carrier-speech. Never past dates. |

The HR LLM should reject internally if all 7 parameters are empty rather than calling with an empty payload.

## HR UI build steps

The tool lives as a child node under the Voice Agent prompt node. **One Twin component, locked** — a single Read-from-Twin child handles both modes by skipping filters whose bound param is empty.

### Step 1 — Add the tool to the Voice Agent

1. Open `inbound-carrier-v15` in the HR workflow editor.
2. Click the Voice Agent node.
3. In the right-hand config pane, scroll to the "Tools" section.
4. Click "+ Add tool".
5. Pick the **Tool** template (HR's wrapper for child-node tool calls). Single Read-from-Twin child below.

### Step 2 — Configure the tool node

1. Tool name: `query_loads` (this is what the LLM sees in the tool list).
2. Tool description: paste the description block from this doc verbatim.
3. Parameters: add 7 params in the order from the parameter table above. Mark all as optional. Use the @ picker for any HR variable references in descriptions; do NOT hand-type `{{var}}` (memory `feedback_hr_variable_resolution.md`).

### Step 3 — Add the single Read-from-Twin child

1. Add **one** Read-from-Twin child node under the Tool.
2. Target table: `loads`.
3. Filters (use @ picker for each; mark each as **"Apply only if value provided"** / "Skip if empty" via the per-filter toggle in the HR config UI):
   - `reference_number` equals `query_loads.load_id` (skip if empty)
   - `origin_state` equals `query_loads.origin_state` (skip if empty)
   - `origin_city` equals `query_loads.origin_city` (skip if empty)
   - `destination_state` equals `query_loads.destination_state` (skip if empty)
   - `destination_city` equals `query_loads.destination_city` (skip if empty)
   - `equipment_type` equals `query_loads.equipment_type` (skip if empty)
   - `pickup_datetime` >= `query_loads.pickup_window` (skip if empty)
4. Sort: `pickup_datetime` ascending.
5. Row cap: 25 (LLM-side prompt caps the pitch to 3).

### Step 4 — Test the single-component behavior

Run the test scenarios in the next section. If HR's Read-from-Twin filters strict-match empty strings (returning 0 rows when a param is empty), we DO NOT add a second component. Documented fallback within the same single component:

- Drop ALL filters from the Read-from-Twin (zero filters configured).
- The component returns the full `loads` table (≤25-500 rows depending on seed scale).
- The agent reasons in-context over the full result set per §5/§6 of the prompt — single-load lookup picks the matching `reference_number`; lane search filters by origin/destination/equipment in its head before pitching.
- Per memory `reference_hr_twin_empty_string_filter.md` recommendation: optional fields shouldn't be Twin filters at all when the agent can reason in-context.

This fallback keeps the architecture at **one Twin component**.

## Test scenarios

### Scenario 1 — Single-load by ID, found

1. Carrier: "Calling about LOAD-0042."
2. Agent calls `query_loads(load_id="LOAD-0042")`. All other params empty.
3. **Expected**: returns 1 row matching LOAD-0042. Agent pitches it per §6.

### Scenario 2 — Single-load by ID, not found

1. Carrier: "Got anything on LOAD-9999?"
2. Agent calls `query_loads(load_id="LOAD-9999")`.
3. **Expected**: returns 0 rows. Agent: "That one looks taken — want me to check what else is moving on your lane?" Does NOT silently keep guessing other IDs.

### Scenario 3 — Full-lane search with results

1. Carrier: "Out of Dallas TX heading to Atlanta GA, dry van, tomorrow morning."
2. Agent calls `query_loads(origin_state="TX", origin_city="Dallas", destination_state="GA", destination_city="Atlanta", equipment_type="dry van", pickup_window="2026-04-28T08:00")`.
3. **Expected**: returns 1-3 matching rows ranked by pickup time. Agent pitches the top 1.

### Scenario 4 — Partial-lane search (no equipment, no destination city)

1. Carrier: "Picking up in Houston tomorrow, anywhere in Georgia."
2. Agent calls `query_loads(origin_state="TX", origin_city="Houston", destination_state="GA", pickup_window="2026-04-28T08:00")`. Equipment + destination_city empty.
3. **Expected**: returns matching rows across any equipment / destination city in GA. Agent pitches top 2-3, lets carrier pick.

### Scenario 5 — Multi-state regional with empty destination_state

1. Carrier: "Out of Miami FL, reefer, anywhere southeast tomorrow."
2. Agent calls `query_loads(origin_state="FL", origin_city="Miami", equipment_type="reefer", pickup_window="2026-04-28T08:00")`. Destination empty.
3. **Expected**: returns rows across all destinations. Agent reasons in-context per §5 region table (Southeast: GA, FL, TN, NC, SC, AL, MS), surfaces 2-3 in-region options.

## Pairs with

- `prompts/voice-agent-system-prompt-v4.md` — §5 (load search) and §6 (load pitch) are the prompt-side mirrors of this spec.
- `prompts/ai-extract-schema-v3.md` — Extract no longer enumerates loads; per-load detail lives in `bookings`.
- `docs/v15-book-load-tool-spec.md` — `book_load` consumes a `load_id` from this tool's output.
- `scripts/hr-tools/calculate_rate.py` — `calculate_rate` consumes the `loadboard_rate` and `pickup_datetime` from this tool's output.
- Memory: `feedback_tool_param_normalization.md`, `feedback_analytics_friendly_enums.md`, `feedback_hr_variable_resolution.md`, `reference_hr_twin_empty_string_filter.md`, `reference_hr_procedural_quirks.md`.
