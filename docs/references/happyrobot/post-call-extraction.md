# Post-Call Extraction

After the call ends, HappyRobot runs a configured LLM prompt over the full transcript (and possibly metadata) to extract structured data. The output is passed to the `call.ended` webhook.

## Configuration

HR exposes a "post-call prompt" field at the workflow level. You paste a prompt that tells the LLM what to extract and in what schema. The LLM's response is parsed as JSON (HR attempts JSON parse; format errors fall back to a raw string in the webhook).

## Our extraction prompt (source of truth)

The prompt should emit a JSON object matching our `CallLogRequest` Pydantic schema. Keep it airtight — HR doesn't (publicly) advertise schema validation, so any slop in our prompt means malformed JSON in `data/calls.json`.

Template (paste into HR's post-call extraction field):

```
You are a data-extraction assistant for a freight-brokerage voice-call system. Given the transcript of a carrier call and associated metadata, extract structured data as a single JSON object matching this EXACT schema. Emit ONLY the JSON object — no preamble, no explanation, no markdown fences.

{
  "call_id": "<HR call id — passed through>",
  "started_at": "<ISO 8601 UTC timestamp>",
  "ended_at": "<ISO 8601 UTC timestamp>",
  "mc_number": "<carrier MC as spoken, normalized to 'MC-123456' format, or null>",
  "carrier_name": "<carrier company name from transcript, or null>",
  "load_id": "<load_id the carrier was pitched, or null if no load pitched>",
  "outcome": "<one of: BOOKED, CARRIER_DECLINED_RATE, CARRIER_DECLINED_UNAVAILABLE, BROKER_DECLINED_INELIGIBLE, BROKER_DECLINED_NO_MATCH, NEGOTIATION_STALLED, CALLBACK_SCHEDULED, TRANSFERRED_TO_REP, CALL_ABANDONED, NO_LOAD_AVAILABLE>",
  "negotiation_rounds": [
    {"round_number": <int>, "party": "BROKER"|"CARRIER", "offer_amount": <int dollars>, "timestamp": "<ISO 8601>"}
  ],
  "agreed_rate": <int dollars, or null>,
  "sentiment_score": <float between -1.0 and 1.0>,
  "sentiment_flags": {
    "price_sensitivity": "LOW"|"MEDIUM"|"HIGH",
    "professionalism": "LOW"|"MEDIUM"|"HIGH",
    "urgency": "LOW"|"MEDIUM"|"HIGH",
    "repeat_carrier": <boolean>,
    "frustration": <boolean>
  },
  "transcript_summary": "<2-4 sentence plain-language summary of the call>",
  "transcript_url": "<passed through from HR metadata>",
  "recording_url": "<passed through from HR metadata>",
  "agent_metadata": {"workflow_version": "<passed through>"}
}

Rules:
- All field names MUST match exactly (case-sensitive).
- `outcome` MUST be one of the listed enum values.
- If a field can't be determined from the transcript, use null (for nullable fields) or the lowest/neutral value (for enums like sentiment_flags).
- Numeric fields (`agreed_rate`, `offer_amount`, `sentiment_score`) must be bare numbers, not strings.
- Emit valid JSON: no trailing commas, no comments, no undefined/NaN.
- Do not emit any text before or after the JSON object.
```

## Outcome inference guidelines (include in the prompt above or as a secondary prompt)

When setting the `outcome` field:
- **BOOKED** — transcript contains explicit agreement on a rate + carrier confirmation of booking (or transfer triggered).
- **CARRIER_DECLINED_RATE** — 1+ rounds of negotiation, carrier says rate too low / "no deal" / "can't do it" without agreement.
- **CARRIER_DECLINED_UNAVAILABLE** — carrier says they're already loaded / no equipment available / wrong lane.
- **BROKER_DECLINED_INELIGIBLE** — FMCSA verification failed (transcript shows our agent said something like "I'm sorry, we can't work with you right now"); check context.
- **BROKER_DECLINED_NO_MATCH** — loads_search returned zero matches; agent told carrier "nothing in your lane."
- **NEGOTIATION_STALLED** — 3 rounds ran without agreement, no explicit decline — conversation just petered out.
- **CALLBACK_SCHEDULED** — carrier or agent explicitly set a callback time/reason.
- **TRANSFERRED_TO_REP** — transfer node fired (BOOKED or ESCALATE path).
- **CALL_ABANDONED** — call dropped / carrier hung up / no clear outcome.
- **NO_LOAD_AVAILABLE** — agent said upfront "we don't have loads right now" (pre-search path).

The model's judgment here isn't perfect; we accept some fuzziness for enum. A human can re-label any mis-classified call via a later UI (not in take-home scope).

## Sentiment scoring

The `sentiment_score` float should reflect the carrier's overall tone:
- **+1.0** enthusiastic, collaborative, eager
- **+0.5** positive, engaged
- **0.0** neutral
- **-0.5** hesitant, skeptical, price-resistant
- **-1.0** frustrated, dismissive, unprofessional

Independently set flags (`price_sensitivity`, `professionalism`, `urgency`, `repeat_carrier`, `frustration`). These aren't redundant with the score — they're orthogonal operational signals.

## Malformed-JSON handling

HR (based on public docs) parses the model output as JSON. If parsing fails:
- **HR behavior (likely)**: falls back to raw string; the webhook payload has the text in some `raw_output` field instead of structured JSON. (Unverified — confirm on first real call.)
- **Our API behavior**: `/v1/calls/log` validates the incoming JSON against the `CallLogRequest` Pydantic model. If validation fails, return 422 with structured error; HR retries once; if still invalid, we drop it and emit `calls.log.malformed_payload` log.

**Prevention**: the prompt's "Emit ONLY the JSON" instruction is critical. If the LLM wraps in ```json ... ``` fences, we'd need to strip them server-side or make the prompt sterner. Test once with a real call, iterate the prompt.

## Versioning

When we change the extraction prompt, note it in `docs/references/happyrobot/changelog.md` with a date and reason. The prompt is semantic — changing it midway through a data-collection period can subtly shift outcome distributions.

## Unresolved / needs confirmation

- **Whether HR supports JSON-mode / structured-output** on the post-call LLM. If yes, switching to it removes the fence-stripping risk. Check your HR workspace.
- **Exact variable passthrough syntax** for `transcript_url`, `recording_url`, `workflow_version` into the prompt output (HR may auto-inject these, or may require explicit reference).
- **Whether HR runs the extraction once or re-runs on webhook retry** (idempotent on our side either way, but affects cost).
