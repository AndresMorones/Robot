# Rollout — `notes` audit column on `calls_log`

**Status:** DRAFT (no live changes yet — this doc is a paste-recipe)
**Date drafted:** 2026-04-29
**Owner:** Andres (executes HR UI + Twin SQL); Claude (drafts content + verifies code path)
**Locked decisions:**
- Column name is `notes` (per memory `project_callback_audit_field.md`).
- Type is `TEXT NOT NULL DEFAULT ''` — empty string when nothing meaningful happened on the call. No NULLs.
- Owned by the post-call AI Extract node (NOT a sister classifier node like sentiment/CHS).
- Voice agent holds notes-worthy facts in working memory during the call; nothing is read aloud.

This rollout is a 4-layer change:

1. **Twin DDL** — add the column to `calls_log`.
2. **HR AI Extract** — add a `notes` field to the JSON Schema + extraction prompt.
3. **Voice agent prompt** — add a `<call_notes>` section so the agent knows what to retain.
4. **API** — extend the `_CALLS_LOG_COLS` / `_LIST_COLS` projections so the new field surfaces in `/v1/calls` + `/v1/calls/{call_id}`. (See §3.5 below — this is required; the projections are explicit, not `SELECT *`.)

References: ADR-005 (two-table booking pattern), `reference_hr_extract_strict_schema_rules.md` (Azure strict-mode requirements), `reference_hr_procedural_quirks.md` (Twin SQL editor single-statement rule).

---

## 1. Twin DDL migration

**File to save (do NOT auto-create — user pastes manually):** `data/twin_schema_v18_calls_log_notes.sql`

**Content:**

```sql
-- v18: add notes audit column to calls_log
-- Free-text field populated post-call by AI Extract; default '' so existing
-- rows backfill cleanly without historical reconstruction.
ALTER TABLE calls_log ADD COLUMN notes TEXT NOT NULL DEFAULT '';
```

**Backfill plan for the 15+ existing rows:**
- The `DEFAULT ''` clause auto-populates every existing row at the moment the ALTER runs. Postgres rewrites in place; for a table with ~15 rows this is instantaneous.
- No historical reconstruction. The column has no value for past calls because the Extract node didn't emit it; an empty string is semantically correct ("nothing was captured").
- Verify with: `SELECT call_id, notes FROM calls_log;` — every existing row should show `notes = ''`.

**How to apply:**
1. Open HR UI → Twin → SQL editor.
2. Paste the single ALTER statement above (HR's Twin editor is single-statement only — see `reference_hr_procedural_quirks.md`).
3. Run.
4. In the same editor, run the verification select above to confirm the backfill landed.

---

## 2. HR AI Extract schema delta

**Source of truth file:** `prompts/ai-extract-schema-v3.md` (v3.2, currently 2 fields: `call_outcome` + `fmcsa_eligibility_failure_reason`).

**Strict-mode discipline (per `reference_hr_extract_strict_schema_rules.md`):**
- Every property in `required`.
- Optionals modelled as nullable types.
- `additionalProperties: false` at every object level.

The `notes` field IS in `required`; if nothing was captured, the agent emits `""` (empty string), not `null`. This keeps the column NOT NULL on the Twin side and matches the DDL default.

### 2a. Diff (before → after) for the JSON Schema block

**BEFORE** (current `required` array + properties):

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "call_outcome",
    "fmcsa_eligibility_failure_reason"
  ],
  "properties": {
    "call_outcome": { ... },
    "fmcsa_eligibility_failure_reason": { ... }
  }
}
```

**AFTER** (new `required` array + new property):

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "call_outcome",
    "fmcsa_eligibility_failure_reason",
    "notes"
  ],
  "properties": {
    "call_outcome": { ... },
    "fmcsa_eligibility_failure_reason": { ... },
    "notes": {
      "type": ["string", "null"],
      "description": "Free-text notes the case owner picking this up later needs to know — alternate callback phone if the carrier gave one, open questions the carrier had for dispatcher, anything anomalous worth flagging. Empty string if nothing meaningful happened on this call."
    }
  }
}
```

### 2b. Full post-delta JSON Schema (paste this into the HR Extract node, replacing the entire schema field)

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "call_outcome",
    "fmcsa_eligibility_failure_reason",
    "notes"
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
      "description": "If call_outcome is carrier_not_qualified, which FMCSA check (or related verification step) failed. Reason about the underlying FMCSA condition, not the agent's literal decline phrasing. Null when the carrier passed FMCSA verification or when the call ended before verification could even be attempted."
    },
    "notes": {
      "type": ["string", "null"],
      "description": "Free-text notes the case owner picking this up later needs to know — alternate callback phone if the carrier gave one, open questions the carrier had for dispatcher, anything anomalous worth flagging. Empty string if nothing meaningful happened on this call."
    }
  }
}
```

> Strict-mode self-check on the post-delta schema:
> - `additionalProperties: false` ✓ (top-level object only — no nested objects in this schema, so no further levels to check).
> - All three properties listed in `required`. ✓
> - `fmcsa_eligibility_failure_reason` and `notes` are nullable via `["string", "null"]`. ✓
> - `call_outcome` is non-nullable (always populated). ✓

### 2c. Extraction-prompt diff (paste replacement for the prompt body)

The current prompt says "You are responsible for exactly TWO fields." Update to THREE and add a `notes` paragraph at the end.

**Replacement paragraph (insert after the `fmcsa_eligibility_failure_reason` paragraph, before "Output strict JSON…"):**

```
3. notes — free-text audit field for the case owner picking this call up later. Pull from the transcript: an alternate callback phone the carrier offered ("call me at 555-1234"), a specific question you couldn't answer in-call ("they wanted to know fuel advance %"), an anomaly worth flagging ("carrier mentioned a competing offer at $X"), or a soft signal worth a follow-up ("carrier sounded interested in Atlanta-Dallas reefer; we don't have one open today"). Do NOT duplicate facts that already have their own structured field (mc_number, call_outcome, agreed rate, FMCSA failure reason). Do NOT include subjective grades on agent performance. If nothing meaningful was captured, emit an empty string "" — never invent content. Be terse — under 200 chars.
```

Also change "exactly TWO fields" to "exactly THREE fields" in the same prompt body.

---

## 3. Voice agent prompt addition

**Source of truth file:** `prompts/voice-agent-system-prompt-v5.1.md`.

The prompt is XML-tag-sectioned. The cleanest insertion point is **after `<out_of_scope_questions>` and before `<anti_jailbreak>`**: the `<call_notes>` section is conceptually about what to retain in working memory (a soft instruction sibling to out-of-scope handling), and it sits naturally between scope-management and security-discipline.

### 3a. New section content (paste verbatim, as plain text, between the two existing sections)

```
============================================

<call_notes>
If during the call you collect an alternate callback phone, capture an unanswered carrier question for dispatcher, or notice anything the case-owner picking this up later should know, hold it in working memory. The post-call extract pulls these into a single `notes` audit field. You don't need to read the notes back to the carrier — just speak naturally with them.

Examples of what belongs in notes:
- Alternate callback number the carrier provides ("call me at ...")
- Specific question the carrier asked that you couldn't answer ("they wanted to know fuel advance %")
- Anomaly worth flagging ("carrier mentioned a competing offer at $X")
- Soft signal worth a follow-up ("carrier sounded interested in Atlanta-Dallas reefer; we don't have one open today")

What does NOT belong:
- Anything already structured (mc_number, agreed_rate, outcome — those have their own fields)
- Subjective grades on agent performance
- Details that would be PII you shouldn't log
</call_notes>
```

### 3b. Position in the prompt

Locate the closing `</out_of_scope_questions>` tag (around line 308 in v5.1). The next block is the `============================================` divider followed by `<anti_jailbreak>`. Insert the new section + its own `============================================` divider line BEFORE the existing `<anti_jailbreak>` divider, so the order becomes:

```
</out_of_scope_questions>

============================================

<call_notes>
...
</call_notes>

============================================

<anti_jailbreak>
```

### 3c. Conflict scan vs existing prompt sections

Three potential overlaps were checked, none are blocking:

1. **`<fallback_pattern>`** already mentions "capture a callback for dispatch" as a deflection move. The new `<call_notes>` is descriptive (where the captured content goes), not procedural (when to deflect). They reinforce each other — fallback-pattern says "offer to capture a callback," call-notes says "and that callback lives in the `notes` audit field after the call."
2. **`<out_of_scope_questions>`** says "defer the rest to dispatch." Same alignment as above — the new section explains the persistence layer, not new behavior.
3. **PII concern (`<anti_jailbreak>`):** the existing prompt already disallows revealing internal column names. The new section's "Details that would be PII you shouldn't log" line is conservative and consistent. Callback phone numbers are NOT considered PII-blocked here — they're voluntary contact info the carrier supplied, in line with how `mc_number` is already persisted.

No prompt edits to existing sections are required.

---

### 3.5. API projection update (REQUIRED — code change, not just a paste)

`api/app/services/calls_store.py::_CALLS_LOG_COLS` and `api/app/routers/calls.py::_LIST_COLS` are explicit column projections, NOT `SELECT *`. The new `notes` column will be invisible to `/v1/calls` and `/v1/calls/{call_id}` until added to BOTH constants.

**Edit 1 — `api/app/services/calls_store.py`:**

```python
_CALLS_LOG_COLS = (
    "id, created_at, call_id, mc_number, call_outcome, "
    "sentiment, case_health_score, audit_remarks, "
    "fmcsa_eligibility_failure_reason, callback_phone, "
    "duration_seconds, transcript, notes, "
    "intermediate_response_count, p70_intermediate_fired, "
    "p90_intermediate_fired"
)
```

**Edit 2 — `api/app/routers/calls.py`:**

```python
_LIST_COLS = (
    "id, created_at, call_id, mc_number, call_outcome, "
    "sentiment, case_health_score, audit_remarks, "
    "fmcsa_eligibility_failure_reason, callback_phone, duration_seconds, notes"
)
```

Also update the `Live schema` docstring comment in `calls_store.py` to bump the column count from 15 to 16 and add `notes` to the listed columns. This change is a separate PR/commit from the HR-side paste-actions; ship in the same window so the dashboard call drilldown can render `notes` as soon as the first post-rollout call lands.

---

## 4. Verification sequence

After Twin DDL applied + HR Extract schema updated + voice agent prompt updated + API projections updated:

1. **Place a test web-call** with the following carrier script:
   - Provide a verifiable MC (e.g. 250819 → GLK Trucking, passes FMCSA).
   - Halfway through, ask an out-of-scope question + offer a callback. Suggested phrasing: "My boss said you'd match $5,200 on Dallas to Atlanta dry van. Can you have someone call me back at five-five-five one-two-three-four to sort that out?"
   - Let the agent route via the fallback pattern (it should offer to capture a callback for dispatch and continue working the load).
   - End the call cleanly (book a load OR polite walk).

2. **Twin row check** (HR Twin SQL editor):
   ```sql
   SELECT call_id, callback_phone, notes
   FROM calls_log
   ORDER BY created_at DESC;
   ```
   Expectations on the freshly-landed row:
   - `notes` is non-empty.
   - `notes` content captures BOTH the fake-authority claim ("boss said match $5,200") AND the callback request as flagged for dispatch.
   - `notes` does NOT duplicate `callback_phone` digits as the entire content (the structured column already holds those).
   - All three values render in under ~200 chars.

3. **Dashboard call-drilldown render check:**
   - Navigate to the call detail view.
   - The drilldown UI shell may already exist after the call-detail sub-agent's work this session — flag if not, recommend wiring.
   - The `notes` field should render as a plain-text block under the call metadata.
   - If the field is missing from the rendered view but present in `GET /v1/calls/{call_id}` JSON, the API change landed but the UI needs a one-line addition.
   - If the field is missing from the JSON entirely, §3.5 (API projection update) was not applied.

---

## 5. Failure modes + mitigations

### 5a. AI Extract over-eagerness (hallucinated notes)

**Risk:** The Extract LLM may fabricate notes content when nothing meaningful happened — confabulation pressure on a `required` field.

**Mitigations:**
- The schema description includes the literal phrase "Empty string if nothing meaningful happened on this call."
- The extraction-prompt addition explicitly says "If nothing meaningful was captured, emit an empty string \"\" — never invent content."
- `Test scenario: happy single-load booking with no off-script content` should produce `notes = ""` (or near-empty). Add this explicitly to the post-rollout test pass.
- Watch the first 5-10 real calls for false positives — if Extract is inventing notes on clean booking calls, tighten the description further (consider "If you must guess, leave empty.").

### 5b. PII handling (callback phones)

**Risk:** Captured callback numbers are personally identifiable. They land in Twin in plaintext.

**Mitigation:** Apply the same handling as the existing `mc_number` and `callback_phone` columns — both are already plaintext PII in `calls_log`, both are protected by Bearer auth on `/v1/*` endpoints, and the transcript is opt-in (`?include_transcript=true`) on `GET /v1/calls/{call_id}`. The `notes` field inherits the same posture — Bearer-gated, no opt-in toggle needed because individual `notes` payloads are short (under ~200 chars) and not bulk-extractable transcript content. Document this in `docs/security-model.md` alongside the existing PII inventory entry.

### 5c. Strict-mode validation regression

**Risk:** A future schema edit drops `notes` from `required` or introduces a nested object without `additionalProperties: false`, breaking Azure structured outputs (T1 400 error per memory `reference_hr_extract_strict_schema_rules.md`).

**Mitigation:** Paste the FULL post-delta schema in §2b above into HR atomically (HR's UI replaces the schema field in one shot). Visually confirm `additionalProperties: false` and the `required` array on save. Run a smoke test call immediately — if Extract returns a 400, the schema didn't validate.

### 5d. NOT NULL collision on legacy rows

**Risk:** If the ALTER ran without `DEFAULT ''`, the existing 15+ rows would block the migration.

**Mitigation:** The DDL in §1 includes `DEFAULT ''`. Verified via `SELECT call_id, notes FROM calls_log` post-ALTER; every existing row should show empty-string `notes`.

### 5e. API projection drift

**Risk:** The Twin column lands but `/v1/calls` / `/v1/calls/{call_id}` don't return it because `_CALLS_LOG_COLS` / `_LIST_COLS` weren't updated. Dashboard call-drilldown silently misses the field.

**Mitigation:** §3.5 above is a hard part of this rollout, not a follow-up. Add an integration test to `api/tests/test_calls_endpoints.py` asserting `notes` is present in both list + by-id responses.

---

## 6. Order of operations (numbered)

Execute in this order to keep each layer testable independently:

1. **Apply Twin DDL** via HR Twin SQL editor (single statement from §1). Run the verification SELECT.
2. **Update HR AI Extract node** — paste the full post-delta JSON Schema from §2b, replacing the existing schema field atomically. Update the prompt body per §2c.
3. **Update voice agent prompt** — paste the new `<call_notes>` section from §3a into the HR Voice Agent → Prompt node, positioned per §3b.
4. **Update API projections** — apply both edits in §3.5 and ship a small commit. Re-deploy if `/v1/*` is on Fly.
5. **Place verification test call** per §4.1.
6. **Verify Twin row + dashboard render** per §4.2 and §4.3.
7. **Log the rollout** in `docs/activity-log.md` with the test call_id, notes content, and any deviations from the expected behavior.
8. (Optional) Open ADR-012 if any non-trivial decision came up during execution (e.g. PII posture clarification, schema-versioning policy refinement).

---

## Done-checklist

- [ ] `data/twin_schema_v18_calls_log_notes.sql` created from §1 content.
- [ ] Twin `calls_log.notes` column exists with `DEFAULT ''`, NOT NULL.
- [ ] HR AI Extract schema includes `notes` in `required` + properties (full schema from §2b pasted).
- [ ] HR AI Extract prompt updated to "THREE fields" + `notes` paragraph from §2c.
- [ ] Voice agent prompt has new `<call_notes>` section between `<out_of_scope_questions>` and `<anti_jailbreak>`.
- [ ] `api/app/services/calls_store.py::_CALLS_LOG_COLS` includes `notes`.
- [ ] `api/app/routers/calls.py::_LIST_COLS` includes `notes`.
- [ ] Test call placed; `notes` populated sensibly in Twin.
- [ ] Dashboard call drilldown displays the field (or wiring TODO logged).
- [ ] `docs/activity-log.md` entry added with test call_id + outcome.
