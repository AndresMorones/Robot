---
title: Post-call AI Extract Schema (v3.2)
hr_node: AI Extract (post-call, after voice agent ends) — feeds Write-to-Twin alongside dedicated Classify Sentiment + Case Health Score nodes
workflow: inbound-carrier-v15 (target)
last_synced: 2026-04-27
mode: JSON Schema (strict, additionalProperties: false on every object)
fields: 2
---

> **v3 → v3.2 diff (2026-04-27 evening)**
>
> 1. **Split the post-call chain into 3 dedicated nodes.** v3 had one Extract node emitting all 5 fields; v3.2 keeps Extract responsible only for outcome reasoning. `sentiment` moves to a dedicated Classify Sentiment node; `case_health_score` and `audit_remarks` move to a dedicated Case Health Score node. All three nodes fan into the same Write-to-Twin chip on the `calls_log` table — one row per call, post-call grain.
> 2. **Dropped `sentiment`, `case_health_score`, `audit_remarks` from this schema.** They're owned by their respective nodes downstream.
> 3. **Surviving fields: `call_outcome` and `fmcsa_eligibility_failure_reason`** (2 total). Strict-mode rules per `reference_hr_extract_strict_schema_rules.md`: both fields are in the top-level `required` array; `fmcsa_eligibility_failure_reason` is nullable; `additionalProperties: false`.
> 4. **Extraction prompt rewritten** to focus only on outcome + FMCSA-failure reasoning. Sentiment heuristics and CHS deduction rubric removed — they now live in their own node prompts.
>
> **v2 → v3 diff (preserved for context):** Dropped `loads_discussed` array entirely (booking record persists mid-call via `book_load` into `bookings` table); dropped per-load fields and FMCSA snapshot fields.

## JSON Schema (paste into Extract node JSON Schema field)

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "call_outcome",
    "fmcsa_eligibility_failure_reason"
  ],
  "properties": {
    "call_outcome": {
      "type": "string",
      "enum": [
        "load_booked",
        "no_match",
        "carrier_not_qualified",
        "call_abandoned"
      ],
      "description": "The outcome of the call as a single canonical category. Reason about the overall conversation flow, not specific phrases. (1) load_booked = at least one load was agreed AND the agent fired the booking handoff successfully (or attempted twice and used the dispatch fallback); applies even on multi-load calls where any load got booked. (2) no_match = FMCSA verification PASSED but no load was agreed (no lane match, all rounds exhausted, carrier walked away mid-negotiation, or zero matches led to a callback capture). (3) carrier_not_qualified = the FMCSA 7-check AND-gate failed for any reason — inactive, unauthorized, out-of-service, wrong authority type, unsafe rating, broker authority, not a carrier, MC not found, identity mismatch, or FMCSA lookup failed and agent gave up. This category overrides any apparent earlier agreement; if the carrier was disqualified, the call is carrier_not_qualified regardless of how the conversation continued. (4) call_abandoned = the call ended before a clear outcome could be determined — carrier hung up early, dropped audio, the agent never got to verify the MC, or the carrier disengaged before any meaningful exchange happened."
    },
    "fmcsa_eligibility_failure_reason": {
      "type": ["string", "null"],
      "enum": [
        "MC_NOT_FOUND",
        "NOT_AUTHORIZED",
        "INACTIVE",
        "REVOKED",
        "OUT_OF_SERVICE",
        "UNSAFE_RATING",
        "LIKELY_BROKER",
        "NOT_A_CARRIER",
        "IDENTITY_MISMATCH",
        "FMCSA_LOOKUP_FAILED",
        null
      ],
      "description": "If call_outcome is carrier_not_qualified, which FMCSA check (or related verification step) failed. Reason about the underlying FMCSA condition, not the agent's literal decline phrasing — the agent intentionally varies wording per call. Map the verification step's outcome to the canonical reason: MC_NOT_FOUND = FMCSA returned null content even after a readback retry, OR carrier could not produce a valid MC. NOT_AUTHORIZED = allowedToOperate was 'N'. INACTIVE = statusCode was 'I'. REVOKED = statusCode was 'R'. OUT_OF_SERVICE = oosDate was non-null. UNSAFE_RATING = safetyRating was literally 'Unsatisfactory'. LIKELY_BROKER = brokerAuthorityStatus was 'A'. NOT_A_CARRIER = censusTypeId was non-null and not 'C'. IDENTITY_MISMATCH = legalName readback failed and DBA retry also did not match the carrier's claimed identity. FMCSA_LOOKUP_FAILED = the verify_carrier tool itself errored or timed out twice and the agent gave up. Null when the carrier passed FMCSA verification (or when the call ended before verification could even be attempted, in which case call_outcome should be call_abandoned)."
    }
  }
}
```

## Extraction prompt (paste into Extract node prompt field)

```
You are classifying the outcome of a freight broker voice-agent call.

You have read the full transcript end-to-end before scoring any field. You reason about the conversation FLOW — what the carrier wanted, what the FMCSA verification revealed, what the agent did with the result, how the negotiation unfolded, how the call ended — not about specific phrases. The agent intentionally varies wording every call (per §13 of the voice-agent system prompt), so phrase-pattern matching mis-classifies whenever the agent rephrases.

Determinism: the same transcript yields the same two outputs. Treat ambiguous cases by following the rules below, not by guessing.

You are responsible for exactly TWO fields. Sentiment, case-health score, and audit remarks are produced by separate downstream nodes — do not include them here.

1. call_outcome — pick exactly one of the four canonical categories. carrier_not_qualified is a semantic OVERRIDE: if the FMCSA 7-check AND-gate failed for any reason, the outcome is carrier_not_qualified regardless of any earlier apparent agreement. load_booked applies whenever the agent and carrier converged on a final rate AND the agent attempted the booking handoff (success or dispatch-fallback both qualify on at least one load); multi-load calls where any one load booked count as load_booked. no_match means FMCSA passed but the carrier walked away or no lane was found. call_abandoned is the residual — the call ended before any clear outcome could be reached.

2. fmcsa_eligibility_failure_reason — set ONLY when call_outcome is carrier_not_qualified. Pick the underlying FMCSA condition that disqualified the carrier (or IDENTITY_MISMATCH / FMCSA_LOOKUP_FAILED for the related verification breakdowns). Reason about the verification step's actual outcome, NOT the agent's decline wording. Null when the carrier passed FMCSA, when the call was abandoned before verification, or when no FMCSA failure applies.

Output strict JSON matching the schema. Both fields are required. Use null only on fmcsa_eligibility_failure_reason when applicable. Do not invent or guess; reason from the transcript.
```

## Field-to-source map (for debugging)

| Field | Surfaced by | Common reason for default value |
|---|---|---|
| `call_outcome` | Conversation flow + FMCSA verification step + book_load attempt | Always populated; `call_abandoned` is the residual when nothing else fits |
| `fmcsa_eligibility_failure_reason` | FMCSA 7-check AND-gate outcome OR related breakdown | Null when FMCSA passed or call abandoned pre-verify |

## Sister-node fields (NOT in this schema — owned downstream)

These fields ARE persisted to `calls_log` but are produced by dedicated nodes, not this Extract:

| Field | Owning node | Notes |
|---|---|---|
| `sentiment` | Classify Sentiment node | 5-tag enum: very_negative / negative / neutral / positive / very_positive |
| `case_health_score` | Case Health Score node | Integer 0-100, deduction-from-100 model per `project_chs_deduction_model.md` |
| `audit_remarks` | Case Health Score node | 1-2 sentence reasoning that pairs with `case_health_score` |

All three nodes (Extract + Classify Sentiment + Case Health Score) run post-call in parallel and fan into the same Write-to-Twin chip on `calls_log`.

## What this schema deliberately does NOT capture

- Per-load detail (load_id, equipment_type, original_rate, apply_rate) — lives in `bookings` table, written mid-call by `book_load`
- Sentiment / CHS / audit remarks — owned by sister nodes (see above)
- FMCSA snapshot fields (legal_name, dot_number, status_code, etc.) — not material for MVP dashboard; can be re-derived from the FMCSA call if ever needed
- Caller name and role — not material for MVP dashboard
- Callback phone — captured in transcript for the agent's own use; not extracted as structured field for MVP
- Number of negotiation rounds used — derivable from transcript review when needed; not a Tier-1 dashboard metric for MVP

## Validation tests after configuring

Run a test web-call for each scenario and check the Extract output:

1. **Happy single-load booking** — `call_outcome="load_booked"`, `fmcsa_eligibility_failure_reason=null`.
2. **MC inactive decline handled cleanly** — `call_outcome="carrier_not_qualified"`, `fmcsa_eligibility_failure_reason="INACTIVE"`.
3. **No-match with callback** — `call_outcome="no_match"`, `fmcsa_eligibility_failure_reason=null`.
4. **Multi-load booking (carrier books two)** — `call_outcome="load_booked"`, `fmcsa_eligibility_failure_reason=null`.
5. **MC not found after retry** — `call_outcome="carrier_not_qualified"`, `fmcsa_eligibility_failure_reason="MC_NOT_FOUND"`.
6. **Carrier hangs up after MC capture** — `call_outcome="call_abandoned"`, `fmcsa_eligibility_failure_reason=null`.
7. **FMCSA lookup timed out twice** — `call_outcome="carrier_not_qualified"`, `fmcsa_eligibility_failure_reason="FMCSA_LOOKUP_FAILED"`.
