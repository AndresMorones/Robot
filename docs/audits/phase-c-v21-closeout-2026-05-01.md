# Phase C v21 Closeout — Workflow c22clmeecc87

**Date:** 2026-05-01
**Workflow:** Inbound Carrier Sales New (`019db77a-0548-741c-9ac8-d713bea1a51f`)
**Version:** v21 (`019de023-defd-743d-a265-0633109e2777`, slug `c22clmeecc87`)
**Method:** Direct REST audit via `https://platform.happyrobot.ai/api/v2`. 7 target nodes drilled.

## Per-fix verdicts

| ID | VERDICT | Evidence |
|----|---------|----------|
| F14a | VERIFIED-CLOSED | `verify_carrier.mc_number.required = True` |
| F14b | VERIFIED-CLOSED | `negotiate_rate.loadboard_rate.required = True` |
| F14c | VERIFIED-CLOSED | `negotiate_rate.pickup_datetime.required = True` |
| F16 | **STILL-OPEN** | Log Event has 29 columns; `hangup_reason` / `room_name` / `status` are **all absent** from `columnValues`. |
| F17 | VERIFIED-CLOSED (removed path) | `node_timings_json` not present in Log Event `columnValues`. |
| F21a | VERIFIED-CLOSED | Log Event `call_id` ← `current.run_id` |
| F21b | VERIFIED-CLOSED | Update Booking Record `call_id` ← `current.run_id` |
| F21c | VERIFIED-CLOSED | Send Event Notification webhook payload `call_id` ← `current.run_id` (separate `session_id` field also sent from `9f573f87.session_id`) |
| F25 | **STILL-OPEN** | `<calendar_context>` body still reads `"Today's local time, "` then blank — no `{{time.now_*}}` variable inserted. |
| F11/F23 | **STILL-OPEN** | GET MC Number `apiKey` field still contains literal `cdc33e44d693a3a58451898d4ec9df862c65b954`. (Note: not actively used — call uses `params.webKey` from `use_case_variables.fmcsa_web_key` — but stale literal not removed.) |

## Token bindings — F18-style group_id deep-read

All 10 token columns on Log Event chip read directly from JSON:

| column | group_id | variable_id | match? |
|--------|----------|-------------|--------|
| `extract_input_tokens` | `3272b1bf` | `_llm_usage.input_tokens` | ✓ |
| `extract_output_tokens` | `3272b1bf` | `_llm_usage.output_tokens` | ✓ |
| `extract_reasoning_tokens` | `3272b1bf` | `_llm_usage.reasoning_tokens` | ✓ |
| `extract_cached_input_tokens` | `3272b1bf` | `_llm_usage.cached_input_tokens` | ✓ |
| `extract_uncached_input_tokens` | `3272b1bf` | `_llm_usage.uncached_input_tokens` | ✓ |
| `chs_input_tokens` | `019dcde8` | `_llm_usage.input_tokens` | ✓ |
| `chs_output_tokens` | `019dcde8` | `_llm_usage.output_tokens` | ✓ |
| `chs_reasoning_tokens` | `019dcde8` | `_llm_usage.reasoning_tokens` | ✓ |
| `chs_cached_input_tokens` | `019dcde8` | `_llm_usage.cached_input_tokens` | ✓ |
| `chs_uncached_input_tokens` | `019dcde8` | `_llm_usage.uncached_input_tokens` | ✓ |

All 10 token bindings verified against expected group_ids — F18 retraction stands.

## @-picker hygiene

- Dead variable references (empty group_id or variable_id): **0** ✓
- Hand-typed `{{}}` outside Prompt body: **0** ✓
- Incomplete nodes (`is_complete = false`): **4** — Prompt, GET MC Number, Get Load Details, Web call

## NEW-ISSUES

### N1 — F16 columns never wired (HIGH)
- Title: 3 expected new column bindings absent on Log Event chip.
- Location: Log Event configuration (29 columns; expected 32).
- Fix sketch: Add 3 `columnValues` rows binding `hangup_reason` / `room_name` / `status` to `9f573f87.{call_end_event,room_name,status}`. Verify Twin DDL has these columns first (could not check Twin DDL — no SQL endpoint reachable from REST audit; treat as `NOT-VERIFIABLE` for DDL).

### N2 — F25 calendar_context still blank (HIGH)
- Title: Voice Agent prompt `<calendar_context>` lacks live time variable.
- Location: Prompt node `data.prompt_md` line ~"Today's local time, ".
- Fix sketch: Replace the trailing comma+space with a Plate `<variable>` element bound to `time.now_utc` (or `time.now_america_chicago`). Otherwise the agent has no anchor for "tomorrow / next Tuesday / 2pm" translations and will hallucinate dates (per memory `project_time_handling_critical_deferred.md`).

### N3 — F11/F23 stale apiKey literal (MEDIUM)
- Title: Hardcoded FMCSA legacy API key still in GET MC Number config.
- Location: GET MC Number `configuration.apiKey[0].children[0].text`.
- Fix sketch: Empty the field (replace text with `""`). Not active in the current call path (auth flows through `params.webKey` → `use_case_variables.fmcsa_web_key`), but the literal is a credential leak surface in stored config.

### N4 — 4 nodes flagged is_complete=false (UNKNOWN severity)
- Title: Prompt / GET MC Number / Get Load Details / Web call carry `is_complete: false`.
- Location: workflow node list `is_complete` flag.
- Fix sketch: Could be a workflow-state marker not a data-quality signal. Verify via HR UI whether each node renders a "needs configuration" badge; if so, fix individually. If false-positive sentinel, document for future audits.

## Source-of-truth note

This audit was performed by direct REST `GET` against `/versions/{vid}/nodes/{nid}` for the 7 target nodes (verify_carrier, negotiate_rate, Log Event, Update Booking Record, Send Event Notification, GET MC Number, Prompt). All bindings, parameter `required` flags, and group_id values quoted above are read verbatim from the API JSON response — no inference. Twin DDL was not directly inspectable via REST (would require Twin SQL endpoint or Run-Python sidecar).

## Action items for v21 → publish

1. **MUST-FIX before publish**: F16 (3 columns), F25 (calendar_context).
2. **SHOULD-FIX before publish**: F11/F23 (apiKey literal cleanup).
3. **VERIFY before publish**: 4 incomplete-flagged nodes (open each in HR UI; confirm no missing config badge).
4. **Twin DDL**: Confirm `calls_log` has `hangup_reason TEXT`, `room_name TEXT`, `status TEXT` before wiring F16 (not verifiable from REST).
