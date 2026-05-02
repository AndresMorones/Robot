# HappyRobot — Post-Call Extraction Chain (inbound-carrier-v4)

After the carrier call ends, the `inbound-carrier-v4` workflow runs a deterministic post-call chain that classifies the call, extracts structured data, computes economics, scores quality, runs the domain auditor, optionally enriches with alternative carriers, and finally POSTs everything to our `/v1/calls/log` endpoint.

The full chain:

```
Classify Outcome (8 tags)
  → Classify Sentiment (4 tags)
    → Extract (full CallLogRequest)
      → Computations (max_buy, discount_pct)
        → Case Health Score (int 0–100)
          → Carrier Sales Auditor (audit_remarks)
            → Transfer Popup (BOOKED only)
              → Enrichment group (outcome-gated):
                  · Split-up (always)
                  · From Past Capacity (always)
                  · Find Matching Carriers (CARRIER_DECLINED_*)
                  · From Truckstop (BROKER_DECLINED_NO_MATCH)
                → POST /v1/calls/log
```

This file is the **domain-specific** freight-carrier extraction schema + prompt templates. For the full HR platform knowledge base (node configs, trigger mechanics, webhook semantics, model catalog, etc.) see the local mirror at `C:\Users\Andre\happyrobot-kb\`. In particular:

- AI Extract node config + strict JSON Schema mode → [happyrobot-kb/authoring/nodes-core.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-core.md)
- AI Classify node config → same file
- Built-in auditor (`Carrier Sales Auditor`) → [happyrobot-kb/authoring/auditors.md](file:///C:/Users/Andre/happyrobot-kb/authoring/auditors.md)
- `call.ended` webhook mechanics → [happyrobot-kb/data-storage/webhooks-outbound.md](file:///C:/Users/Andre/happyrobot-kb/data-storage/webhooks-outbound.md)

The prompts + schema below are what gets pasted into the workflow nodes by Andres in the HR UI.

---

## 1. Classify Outcome prompt template

Paste-ready content for the **first** Classify node in the post-call chain. 8 mutually-exclusive outcome tags.

```
You are a call-outcome classifier for a freight-brokerage voice-agent system. Given the transcript of a carrier call, classify the call into EXACTLY one of these 8 outcome tags:

- BOOKED — Carrier agreed to book; rate confirmed; transfer triggered.
- CARRIER_DECLINED_RATE — Carrier declined because the rate didn't work (1+ rounds ran).
- CARRIER_DECLINED_UNAVAILABLE — Carrier already loaded / no equipment / wrong lane.
- BROKER_DECLINED_INELIGIBLE — FMCSA verification failed; we politely declined.
- BROKER_DECLINED_NO_MATCH — No matching load found for their lane/equipment.
- NEGOTIATION_STALLED — 3 rounds ran, no agreement, no explicit decline.
- CALLBACK_SCHEDULED — Callback requested and captured.
- ABANDONED — Call dropped / hung up / no meaningful conversation OR repeated prompt-injection attempt.

Return EXACTLY one tag. No preamble. No explanation.
```

The output of this node is referenced downstream as `{{<classify_outcome_id>.response}}` and feeds the `outcome` field in Extract plus the outcome-gated enrichment branches.

---

## 2. Classify Sentiment prompt template

Paste-ready content for the **second** Classify node. 4 mutually-exclusive sentiment tags, scored against the carrier's overall affect across the full call.

```
You are a sentiment classifier for freight-carrier calls. Given the transcript of a carrier call, classify the carrier's OVERALL sentiment across the full call into EXACTLY one of these 4 tags:

- POSITIVE — Collaborative, enthusiastic, engaged; rapport built.
- NEUTRAL — Transactional, professional, no strong affect.
- NEGATIVE — Hesitant, skeptical, price-resistant, declining.
- FRUSTRATED — Dismissive, angry, unprofessional, escalation-worthy.

Classify the carrier's sentiment, not the agent's. Return EXACTLY one tag. No preamble. No explanation.
```

Downstream reference: `{{<classify_sentiment_id>.response}}` → feeds the `sentiment` field in Extract.

---

## 3. Extract prompt template

Paste-ready content for the **AI Extract** node. The schema in section 4 is attached to the node in strict mode. This prompt is the system-message half; the user message is the transcript plus the upstream classifier / Computations / Health / Auditor outputs, wired via `{{persistent_id.response.field}}` references.

```
You are a data-extraction assistant for a freight-brokerage voice-call system. Given the transcript of a carrier call plus the upstream Classify/Computations/Health/Auditor outputs, extract structured data matching the attached JSON Schema.

Emit ONLY the JSON object — no preamble, no explanation, no markdown fences.

Rules:
- All field names MUST match exactly (case-sensitive).
- `outcome` MUST be one of the 8 enum values from Classify Outcome.
- `sentiment` MUST be one of the 4 enum values from Classify Sentiment.
- If a field can't be determined from the transcript, use null (for nullable fields) or the neutral/lowest enum value.
- Numeric fields must be bare numbers, not strings.
- `call_id` and `room_name` are passed through from HR trigger metadata.
- `audit_remarks` is the full array from Carrier Sales Auditor — do not modify.
- `enrichment_data` is populated from the post-call enrichment nodes when they fire.
- Emit valid JSON: no trailing commas, no comments, no NaN/undefined.
```

---

## 4. Extract JSON Schema (strict mode)

Paste into the AI Extract node's **JSON Schema** field. `additionalProperties: false` is set at every object level so the extractor cannot invent keys. Nullable fields use `["type", "null"]` union form (draft-07 + OpenAI strict-mode compatible).

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "call_id", "room_name", "started_at", "ended_at",
    "outcome", "sentiment", "sentiment_flags", "transcript_summary",
    "case_health_score", "max_buy", "discount_pct", "audit_remarks"
  ],
  "properties": {
    "call_id": {"type": "string"},
    "room_name": {"type": "string", "description": "WebRTC room ID from Web call trigger; correlation key"},
    "started_at": {"type": "string", "description": "ISO 8601 UTC"},
    "ended_at": {"type": "string", "description": "ISO 8601 UTC"},
    "mc_number": {"type": ["string", "null"], "description": "Normalized numeric MC, e.g. '738144'"},
    "carrier_name": {"type": ["string", "null"], "description": "FMCSA legalName"},
    "load_id": {"type": ["string", "null"]},
    "outcome": {
      "type": "string",
      "enum": [
        "BOOKED",
        "CARRIER_DECLINED_RATE",
        "CARRIER_DECLINED_UNAVAILABLE",
        "BROKER_DECLINED_INELIGIBLE",
        "BROKER_DECLINED_NO_MATCH",
        "NEGOTIATION_STALLED",
        "CALLBACK_SCHEDULED",
        "ABANDONED"
      ]
    },
    "sentiment": {
      "type": "string",
      "enum": ["POSITIVE", "NEUTRAL", "NEGATIVE", "FRUSTRATED"]
    },
    "sentiment_flags": {
      "type": "object",
      "additionalProperties": false,
      "required": ["price_sensitivity", "professionalism", "urgency", "repeat_carrier", "frustration"],
      "properties": {
        "price_sensitivity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "professionalism": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "repeat_carrier": {"type": "boolean"},
        "frustration": {"type": "boolean"}
      }
    },
    "negotiation_rounds": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["round_number", "party", "offer_amount", "timestamp"],
        "properties": {
          "round_number": {"type": "integer"},
          "party": {"type": "string", "enum": ["BROKER", "CARRIER"]},
          "offer_amount": {"type": "integer"},
          "timestamp": {"type": "string"}
        }
      }
    },
    "agreed_rate": {"type": ["integer", "null"]},
    "max_buy": {
      "type": "integer",
      "description": "From Computations node: loadboard_rate * (1 - negotiation_floor_pct)"
    },
    "discount_pct": {
      "type": "number",
      "description": "From Computations: (loadboard_rate - agreed_rate) / loadboard_rate, or null if no agreement"
    },
    "case_health_score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "From Case Health Score node"
    },
    "audit_remarks": {
      "type": "array",
      "description": "From Carrier Sales Auditor",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["northstar_name", "grade"],
        "properties": {
          "northstar_name": {"type": "string"},
          "grade": {"type": "string", "enum": ["passed", "failed", "not_applicable"]},
          "correction": {"type": ["string", "null"]},
          "correction_reason": {"type": ["string", "null"]}
        }
      }
    },
    "enrichment_data": {
      "type": ["object", "null"],
      "additionalProperties": false,
      "description": "From post-call enrichment nodes (Split-up, From Past Capacity, Find Matching Carriers, From Truckstop). Optional per outcome.",
      "properties": {
        "split_up_midpoint": {"type": ["integer", "null"]},
        "split_up_delta_from_sidecar": {
          "type": ["integer", "null"],
          "description": "Positive = Split-up counter was higher than our sidecar's; negative = lower"
        },
        "past_capacity": {
          "type": ["array", "null"],
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["lane", "count"],
            "properties": {
              "lane": {"type": "string"},
              "count": {"type": "integer"}
            }
          }
        },
        "find_matching_carriers": {
          "type": ["array", "null"],
          "items": {"type": "string", "description": "MC numbers of alternative carriers"}
        },
        "truckstop_alternatives": {
          "type": ["array", "null"],
          "items": {"type": "string", "description": "MC numbers from Truckstop query"}
        }
      }
    },
    "transcript_summary": {
      "type": "string",
      "description": "2-4 sentence plain-language summary"
    },
    "transcript_url": {
      "type": ["string", "null"],
      "description": "Passed through from HR metadata"
    },
    "recording_url": {
      "type": ["string", "null"],
      "description": "Passed through from HR metadata"
    },
    "agent_metadata": {
      "type": ["object", "null"],
      "additionalProperties": false,
      "properties": {
        "workflow_version": {"type": ["string", "null"]}
      }
    }
  }
}
```

---

## 5. Outcome tag inference guidelines

One-sentence criterion per tag. Used as a sanity check when the extracted `outcome` looks wrong in a post-mortem — also copied verbatim into the Classify Outcome prompt above so the classifier sees the same definitions.

- **BOOKED** — explicit rate agreement + carrier confirmation (or transfer triggered post-agreement).
- **CARRIER_DECLINED_RATE** — 1+ negotiation rounds ran; carrier said rate too low / "no deal" / "can't do it".
- **CARRIER_DECLINED_UNAVAILABLE** — carrier said already loaded / no equipment / wrong lane.
- **BROKER_DECLINED_INELIGIBLE** — FMCSA verification failed (MC_NOT_FOUND, NOT_AUTHORIZED_TO_OPERATE, NOT_ACTIVE, WRONG_ENTITY_TYPE).
- **BROKER_DECLINED_NO_MATCH** — loads search returned zero matches for their lane/equipment.
- **NEGOTIATION_STALLED** — 3 rounds ran without agreement, no explicit decline.
- **CALLBACK_SCHEDULED** — explicit callback time/reason captured.
- **ABANDONED** — call dropped / hangup / no clear outcome OR repeated prompt-injection (2+ attempts → end call → tag ABANDONED).

Classifier judgment is imperfect; some fuzziness is acceptable. A future re-labeling UI is out of scope for the take-home.

---

## 6. Sentiment tag inference guidelines

- **POSITIVE** — Collaborative tone, enthusiastic, quick to agree, rapport-building language.
- **NEUTRAL** — Transactional, professional, no strong affect, matter-of-fact.
- **NEGATIVE** — Hesitant, skeptical, price-resistant, "not gonna work" language.
- **FRUSTRATED** — Dismissive, angry, cursing, unprofessional, escalation-worthy.

Notes:
- Sentiment is about the **CARRIER**, not the agent. Agent tone is separately graded by the Auditor.
- Classify the **whole call**, not individual turns. A late-call flip from POSITIVE → NEGATIVE after a rate miss classifies as NEGATIVE overall.
- `sentiment_flags.frustration: true` does not automatically imply `sentiment: FRUSTRATED` — the flags are orthogonal operational signals (e.g. a carrier can be briefly frustrated about a lane mismatch but still end the call POSITIVE).

---

## 7. Computations / Case Health Score / Auditor / Enrichment field reference

Each downstream node writes into specific fields on `CallLogRequest`. This section is the contract between the HR workflow and our API.

### 7.1 Computations node

Post-call **Python Code** node. Reads `loadboard_rate` from the pitched load, `negotiation_floor_pct` workflow variable, and `agreed_rate` (when the call is BOOKED). Emits:

- `max_buy` *(int)* — `loadboard_rate * (1 - negotiation_floor_pct)`. The absolute ceiling we'd have accepted. **Never spoken during the call** (hard rule — carriers never learn our floor). Used by the Auditor to grade whether the agent left money on the table or blew through the floor.
- `discount_pct` *(float)* — `(loadboard_rate - agreed_rate) / loadboard_rate` for BOOKED calls. `null` for all other outcomes. Feeds the dashboard's "margin captured" KPI.

Both values land verbatim in the extracted JSON via `{{<computations_id>.response.max_buy}}` / `{{<computations_id>.response.discount_pct}}` references in the Extract node's prompt wiring.

### 7.2 Case Health Score node

Post-call node (node type TBD with Andres — likely an AI Classify with numeric output or a dedicated Python Code that calls an LLM). Outputs a single `int 0–100` reflecting overall call quality along five implicit dimensions:

1. MC verified smoothly (no repeated re-prompting).
2. Pitch was cohesive (load summary sounded natural, not robotic).
3. Negotiation stayed within policy (no floor breach, no > 3 rounds, no premature concession).
4. Outcome made sense for the conversation trajectory.
5. Caller wasn't left frustrated.

Scale:
- **0** — disaster (we booked below floor, caller hung up mid-pitch, FMCSA error surfaced to caller).
- **50** — acceptable, forgettable.
- **100** — textbook call.

Lands in `case_health_score`. Feeds the dashboard's Quality view + is a primary driver of the weekly ops review.

### 7.3 Carrier Sales Auditor

HR's built-in domain auditor, configured at `Built-in → Auditor → Carrier Sales Auditor`. Fires post-call. Grades the call against a set of **northstars** (quality criteria configured in the HR UI — e.g. "Agent confirmed MC number", "Agent never revealed max_buy", "Agent offered a counter within policy"). Emits:

```json
[
  {
    "northstar_name": "Agent confirmed MC number",
    "grade": "passed",
    "correction": null,
    "correction_reason": null
  },
  {
    "northstar_name": "Agent never revealed max_buy",
    "grade": "failed",
    "correction": "Agent said 'our top is $2,300' which is the max_buy value",
    "correction_reason": "max_buy is internal-only; agent should counter with a specific offer, not disclose the ceiling"
  }
]
```

Grades are restricted to `passed | failed | not_applicable`. `correction` + `correction_reason` are only populated on `failed`. The full array lands in `audit_remarks` unchanged. Feeds the dashboard's Quality view (per-northstar pass rate) and is the single most useful artifact for coaching.

### 7.4 Enrichment group (outcome-gated)

Fires post-call, each sub-node gated on specific outcomes. All outputs land inside `enrichment_data`.

| Node | Fires on | Writes to | Purpose |
|---|---|---|---|
| **Split-up** | all outcomes | `split_up_midpoint`, `split_up_delta_from_sidecar` | A/B: compute midpoint between last broker counter and last carrier offer; compare to what our sidecar negotiation engine would have countered. Positive delta = Split-up was higher than us; negative = lower. |
| **From Past Capacity** | all outcomes | `past_capacity` | This carrier's historical hauling record keyed by lane. Empty-but-not-null means "we've seen them before but not on relevant lanes". |
| **Find Matching Carriers** | `CARRIER_DECLINED_RATE`, `CARRIER_DECLINED_UNAVAILABLE` | `find_matching_carriers` | 3 alternative carrier MCs for broker-team outreach on this same load. |
| **From Truckstop** | `BROKER_DECLINED_NO_MATCH` | `truckstop_alternatives` | Truckstop-listed alternative loads/carriers for the lane the caller wanted. Surfaces to dashboard's "alternative carrier inventory" view so the broker team can still fulfill. |

Fields not written by a node that didn't fire stay `null`. Dashboard readers must handle the null case.

---

## 8. Malformed-JSON handling (API side)

If HR's Extract node emits malformed JSON (rare in practice — JSON Schema strict mode prevents most issues):

- HR's webhook layer may wrap the Extract response as a raw string. Our `/v1/calls/log` handler is defensive:
  1. Tries `payload.extracted` key first (HR's documented wrapper).
  2. Falls back to root if absent.
  3. Strips markdown fences (```json ... ```) if the LLM wrapped the JSON despite the prompt instruction.
- On Pydantic `CallLogRequest` validation failure: return `422` with structured error detail. HR retries once (idempotent on our side — `call_id` is the dedup key).
- On second failure: emit structured log `calls.log.malformed_payload` (with raw body truncated to 2 KB) and drop. We do NOT 500 — a malformed payload should never block HR's workflow queue.

Prevention strongly preferred: the "Emit ONLY the JSON" instruction in the Extract prompt + the strict JSON Schema attached to the node should cover ≥99% of cases. Iterate on the prompt if the first real call surfaces a parsing edge case.

---

## 9. Versioning

Changing this extraction prompt or schema subtly shifts outcome distributions (and thus KPI trendlines). When we change either:

- Record the change in `docs/references/happyrobot/changelog.md` with date + rationale + which fields moved.
- Flag any analytics impact to the dashboard consumer (Andres / reviewer) before pushing — especially if outcome or sentiment enums change.
- HR workflows are immutable once published, so every schema change ships as a new workflow version (`inbound-carrier-v5`, etc.) and a corresponding ADR in `docs/decisions/`.

---

## 10. Unresolved

- Whether **Carrier Sales Auditor**'s emitted `audit_remarks` format exactly matches the schema in section 4 — need to verify with a real call (Andres to paste one post-step-13). If HR's actual shape differs, we adapt the schema, not the auditor.
- Whether **Case Health Score** is a node Andres adds to the workflow, or one already wired in his existing build (mentioned in an earlier message without detail). Node type (AI Classify vs custom Python Code) is TBD.
- Whether HR's **Extract node** supports JSON Schema strict mode natively end-to-end, or if we need to enforce via prompt instruction + post-extract validation on our API side. KB suggests strict mode is supported; first real call will confirm.
- Exact semantics of `enrichment_data.past_capacity` when **no history** exists for the carrier — `null` (no record lookup attempted) vs empty array `[]` (lookup ran, returned no matches). Preference is empty-array-on-miss so the dashboard can distinguish "new carrier" from "enrichment node didn't fire".
- Whether HR re-runs the extraction chain on webhook retry, or only re-POSTs the already-extracted JSON (idempotent on our side either way via `call_id`).
