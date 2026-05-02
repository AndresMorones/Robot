---
title: Post-call AI Extract Schema
hr_node: AI Extract (post-call, after voice agent ends)
workflow: inbound-carrier-v4
last_synced: 2026-04-25
mode: JSON Schema (strict, additionalProperties: false on every object)
fields: 16
---

> Runs once per call after the voice agent ends. Reads the full transcript + tool outputs and produces a structured record that flows into the Write Twin → `calls_log` table. The system prompt's Conversation Contract section is designed to surface every field below in extractable form.

> **MVP scope note (2026-04-25):** the LIVE HR Extract node currently has a different shape (14 fields focused on negotiation/load capture). This document is the canonical post-MVP target. Migration to this schema is **deferred to Tier-2** — for MVP, `callback_phone` is captured by the agent in the transcript but not extracted as a structured field. To verify what's live, query `/api/v2/versions/<v4_id>/nodes/<extract_id>/available-vars` (the @ picker view).

## Extraction prompt

Paste this in the AI Extract node's prompt field:

```
You are extracting structured data from a freight carrier call transcript.

The agent followed strict instructions designed to surface specific data fields:
- Always speaks load reference numbers aloud when pitching ("LOAD-0001, going from...")
- Always confirms callback phone numbers back to the carrier ("Got it, [phone] — someone will reach out")
- Uses canonical decline phrasings that map to FMCSA eligibility failure enum values
- Confirms agreed rates verbally ("we have a deal at $X")

For each field in the JSON Schema, pull the value precisely as instructed in its description.
Use null for fields where the data wasn't present in the transcript — do NOT guess or fabricate values.
For enum fields, return only one of the listed allowed values (or null if no value applies).
Phone numbers should be returned as digits only with no formatting (e.g., "5558675309").
Dollar amounts should be returned as numbers without currency symbols or commas (e.g., 2250 not "$2,250.00").
```

## JSON Schema (paste into HR's Extract node — strict mode)

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "mc_number",
    "dot_number",
    "legal_name",
    "dba_name",
    "caller_name",
    "caller_role",
    "allowed_to_operate",
    "status_code",
    "safety_rating",
    "carrier_operation_code",
    "fmcsa_eligibility_failure_reason",
    "load_reference",
    "pitched_loadboard_rate",
    "agreed_rate",
    "negotiation_rounds_used",
    "callback_phone"
  ],
  "properties": {
    "mc_number": {
      "type": ["string", "null"],
      "description": "The carrier's MC number as captured from the call. Numeric digits only (e.g., '250819'). Null if not captured."
    },
    "dot_number": {
      "type": ["integer", "null"],
      "description": "DOT number from FMCSA verify_carrier response (carrier.dotNumber). Null if FMCSA returned null content or eligibility wasn't checked."
    },
    "legal_name": {
      "type": ["string", "null"],
      "description": "Legal name from FMCSA (carrier.legalName), as read back to the caller for confirmation. Null if FMCSA returned null content."
    },
    "dba_name": {
      "type": ["string", "null"],
      "description": "DBA name from FMCSA (carrier.dbaName). Null if not present in FMCSA response."
    },
    "caller_name": {
      "type": ["string", "null"],
      "description": "First name (or full name) of the person on the call, captured by the agent's identity question 'Who do I have on the line?'. Null if not asked or carrier didn't answer."
    },
    "caller_role": {
      "type": ["string", "null"],
      "enum": ["driver", "dispatcher", "owner_operator", "dispatch_service", "unknown", null],
      "description": "Role the caller stated when asked 'Are you the driver, dispatcher, owner-operator, or with a dispatch service?'. Use 'unknown' if asked but answer was unclear. Null if not asked."
    },
    "allowed_to_operate": {
      "type": ["string", "null"],
      "enum": ["Y", "N", null],
      "description": "FMCSA allowedToOperate field at call time. 'Y'=authorized, 'N'=not authorized. Null if FMCSA not retrieved or content was null."
    },
    "status_code": {
      "type": ["string", "null"],
      "enum": ["A", "I", "R", null],
      "description": "FMCSA statusCode at call time. 'A'=active, 'I'=inactive, 'R'=revoked. Null if FMCSA not retrieved or content was null."
    },
    "safety_rating": {
      "type": ["string", "null"],
      "enum": ["Satisfactory", "Conditional", "Unsatisfactory", null],
      "description": "FMCSA safetyRating at call time. Null is common (rating not assigned to all carriers)."
    },
    "carrier_operation_code": {
      "type": ["string", "null"],
      "enum": ["A", "B", "C", null],
      "description": "FMCSA carrierOperation.carrierOperationCode. 'A'=Interstate, 'B'=Intrastate Hazmat, 'C'=Intrastate Non-Hazmat. Null if FMCSA not retrieved."
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
        null
      ],
      "description": "If the agent declined the carrier on FMCSA grounds, which check failed. Map from the agent's decline phrasing: 'not finding any carrier registered'→MC_NOT_FOUND; 'authority isn't currently active'→NOT_AUTHORIZED; 'MC status as inactive'→INACTIVE (also REVOKED if explicitly stated); 'out-of-service order'→OUT_OF_SERVICE; 'compliance flags... compliance team will follow up'→UNSAFE_RATING; 'authority is set up as a broker'→LIKELY_BROKER; 'registered as a broker or shipper'→NOT_A_CARRIER. Null if eligibility passed or wasn't checked."
    },
    "load_reference": {
      "type": ["string", "null"],
      "description": "Load reference number that was pitched (e.g., 'LOAD-0001'). Pull from the agent's pitch utterance like 'I've got LOAD-0001, going from...'. Null if no load was pitched."
    },
    "pitched_loadboard_rate": {
      "type": ["number", "null"],
      "description": "The loadboard rate the agent pitched in dollars. Pull from utterance like 'Rate is $2,400'. Return as number, no commas or currency symbols. Null if no load was pitched."
    },
    "agreed_rate": {
      "type": ["number", "null"],
      "description": "Final agreed rate in dollars if the deal was BOOKED. Pull from agent's confirmation utterance like 'we have a deal at $2,232'. Return as number. Null if call did not result in a booking."
    },
    "negotiation_rounds_used": {
      "type": "integer",
      "description": "Count of distinct broker counter-offers made during the call (the agent's counter-offers, not the carrier's). 0 if no negotiation occurred (carrier accepted ask immediately, or call ended pre-negotiation, or no load was pitched). Maximum is the workflow's max_negotiation_rounds setting (3)."
    },
    "callback_phone": {
      "type": ["string", "null"],
      "description": "Callback phone number captured when the agent offered a callback (UNSAFE_RATING decline, no-load match, or carrier-requested callback). The agent confirms phone numbers back to the caller — pull from the agent's confirmation utterance like 'Got it, 555-867-5309 — someone will reach out'. Return as digits only with no formatting (e.g., '5558675309'). Null if no callback was offered or carrier declined to provide a number."
    }
  }
}
```

## Field-to-source map (for debugging extraction misses)

| Field | Surfaced by Prompt section | Common reason for null |
|---|---|---|
| `mc_number` | Step 1 (carrier states it) | Carrier refused; call ended pre-MC |
| `dot_number`, `legal_name`, `dba_name` | Step 2 verify_carrier output | MC not found in FMCSA |
| `caller_name`, `caller_role` | Step 2 identity capture | Eligibility failed before identity asked |
| `allowed_to_operate`, `status_code`, `safety_rating`, `carrier_operation_code` | verify_carrier response | MC not found / FMCSA not called |
| `fmcsa_eligibility_failure_reason` | Step 2 decline phrasing | Eligibility passed (then null is correct) |
| `load_reference`, `pitched_loadboard_rate` | Step 3 pitch wording | No-match path / eligibility failed |
| `agreed_rate` | Step 5 acceptance confirmation | Did not BOOK |
| `negotiation_rounds_used` | Counted from broker counter-offers | 0 if no negotiation |
| `callback_phone` | Step 2 Check 5 OR Step 3 no-match | No callback offered |

## Validation tests after configuring

Run a test web-call for each of these scenarios and check the Extract output:

1. **Happy booking**: should populate `mc_number, dot_number, legal_name, dba_name, caller_name, caller_role, all 4 FMCSA enum fields with values, load_reference, pitched_loadboard_rate, agreed_rate, negotiation_rounds_used`. `callback_phone` and `fmcsa_eligibility_failure_reason` should be null.
2. **MC inactive decline**: `mc_number, dot_number, legal_name, dba_name, allowed_to_operate, status_code='I', fmcsa_eligibility_failure_reason='INACTIVE'`. All other fields null.
3. **No-match callback**: identity captured + `callback_phone='5558675309'` (or whatever was given). `load_reference, agreed_rate` null.
