> **SUPERSEDED 2026-04-27 evening** — v14 multi-load Loop architecture replaced by v15 two-table booking pattern. See `docs/v15-architecture-2026-04-27.md` for the locked design. This document retained for archaeological context.

# v14 Post-Call Classifier Design — locked 2026-04-27 (revised)

User direction 2026-04-27: simplify CHS into general categories, keep modular structure, retain audit_remarks for dashboard logs. Single LLM-driven node emits all 4 outputs.

## Architecture lock

Post-call chain (in execution order):

```
Voice Agent
  → AI Extract            (6 transcript-only fields, already locked)
  → Case Health Score     (single LLM node — emits 4 fields: chs + outcome + sentiment + audit_remarks)
  → Write to Twin
```

ONE classifier node replaces the previous "Classify Outcome + Classify Sentiment + CHS Run Python" trio. Cleaner, one LLM call per call, deterministic by prompt design.

## Why single-node

- **Simpler chain** — 1 hop instead of 3
- **Consistent grading** — same LLM sees outcome/sentiment/score together; can correlate them
- **audit_remarks comes free** — LLM naturally writes the reasoning summary
- **Modular categories** — each rubric category in the prompt description is a "tick" (easy to add/remove without rewriting math)
- **Determinism** — prompt explicitly says "same transcript → same outputs"; LLMs at temperature ~0 stable enough for grading
- **No regex maintenance** — no Python deduction patterns to keep current with prompt evolution

## CHS — DEDUCTION-FROM-100, 4 GENERAL CATEGORIES

### Framing

CHS measures **customer experience quality**, not agent compliance. Legitimate business outcomes (FMCSA decline, no-match) don't deduct. Deductions fire when:
- Customer disengaged (hung up, no answer)
- Customer dissatisfied (sentiment turned negative or worse)
- Agent broke role (leaks, repetition, accepting injections)
- Conversation flow had friction (no readback, round numbers, dragged-out negotiation)

### 4 deduction categories (general, not exhaustive)

| Category | Heavy hits (~15-30) | Light hits (~3-10) |
|---|---|---|
| **1. Customer engagement** | disconnect mid-call, no-answer, agent silent >10s | (rarely light) |
| **2. Customer satisfaction** | very_negative end, sentiment inversion | negative end, escalation phrase |
| **3. Agent professionalism** | tool/floor/var leak, accepted authority injection, repetition loop | (rarely light) |
| **4. Conversation flow** | (rarely heavy) | no readback before transfer, round-number counters, 4+ rounds |

### Threshold semantic

- **90-100**: clean, well-handled, customer satisfied
- **70-89**: minor issues, still OK
- **<70**: badly handled (review required)
- **<50**: serious breakdown
- **<30**: catastrophic multi-failure

### Do NOT deduct

- Legitimate FMCSA decline correctly handled
- no_match with proper callback
- Neutral sentiment on transactional calls
- Carrier mildly displeased about FMCSA decline (sentiment captures it via the soft "negative end" deduction)

## Sentiment 5-tag

`very_negative`, `negative`, `neutral`, `positive`, `very_positive`. Polarity scale, weight call ending.

## Outcome 4-tag with semantic FMCSA override

`load_booked`, `no_match`, `carrier_not_qualified`, `call_abandoned`.

Critical override (semantic, NOT phrase-based): if the FMCSA verification step revealed the carrier was NOT eligible (any reason — inactive, unauthorized, out-of-service, wrong authority type, safety rating, not found, identity mismatch, lookup failed and agent gave up), `call_outcome` = `carrier_not_qualified` regardless of any earlier apparent agreement.

The classifier reasons about the conversation FLOW (did MC capture happen → did verification fire → what did it reveal → did the agent proceed correctly), NOT specific wording. The voice agent intentionally varies phrasing per call (§12 of voice-agent-system-prompt-v2), so phrase-pattern matching is brittle and would mis-classify whenever the agent rephrases.

## audit_remarks

1-2 sentence human-readable reasoning. Used for:
- Dashboard drilldown view (per-call inspection by Maria, Engineer Andres)
- M-031 metric in the catalog
- Future Tier-2 self-improvement loop (LLM reflects on grading patterns)

## Twin DDL deltas

If `audit_remarks` column doesn't exist:
```sql
ALTER TABLE calls_log ADD COLUMN audit_remarks TEXT;
```

`case_health_score` BIGINT, `sentiment` TEXT, `call_outcome` TEXT should already exist per Phase 3 spec.

## Write-to-Twin chip rebinds (4 chips)

| Twin column | Source |
|---|---|
| `case_health_score` | Case Health Score → response.case_health_score |
| `call_outcome` | Case Health Score → response.call_outcome |
| `sentiment` | Case Health Score → response.sentiment |
| `audit_remarks` | Case Health Score → response.audit_remarks |

Reparent Write to Twin: parent = Case Health Score.

## Decommissioned

- Separate `Classify Sentiment` node — DELETE (consolidated into CHS)
- Separate `Classify Outcome` node — DELETE (consolidated into CHS)
- `scripts/hr-tools/case_health_score.py` Run Python — NOT USED in v14 (kept on disk for reference; replaced by LLM-driven prompt classifier)

## AI Extract — flow-aware semantic reasoning (locked 2026-04-27 evening)

Same rigour as CHS: Extract reasons about conversation flow + outcomes, not literal phrasings. The voice agent intentionally varies wording (§12 of voice-agent-system-prompt-v2), so phrase pattern-matching mis-extracts whenever the agent rephrases.

### 6 fields, semantic descriptions

1. **load_id** — the load reference discussed in the call
2. **equipment_type** — equipment type carrier was working with (5-tag enum)
3. **original_rate** — agent's listed/asking rate when pitching (broker's anchor price, before negotiation)
4. **apply_rate** — final mutually-agreed rate after negotiation (may equal original_rate)
5. **carrier_name** — carrier company legal name as confirmed in the call (proper case)
6. **fmcsa_eligibility_failure_reason** — underlying FMCSA condition that disqualified the carrier (8-tag enum), derived from understanding verification outcome NOT agent wording

### Rules

- Read the full transcript before extracting; don't field-by-field in isolation
- **Track conversation flow — capture FINAL committed values, not interim ones**. Carriers may pivot loads, correct origins, change equipment mid-call. The agent may pitch one load, then pivot to another after rejection. Negotiation rounds shift the apply_rate. Always extract the value the carrier and agent ended up engaging with — not the first one mentioned.
- Empty/null when no clear evidence in transcript
- Numbers are whole-dollar integers (no symbols/decimals/commas)
- For fmcsa_eligibility_failure_reason: reason about the underlying FMCSA condition, not the literal phrasing
- Same transcript yields same extraction (determinism)

## Pairs with

- `prompts/voice-agent-system-prompt-v2.md` (the master prompt being graded against)
- `docs/dashboard-metric-catalog.md` (M-020, M-021, M-031 use these outputs)
- Memory: `project_chs_deduction_model.md`, `project_phase3_calls_log_v2.md`
