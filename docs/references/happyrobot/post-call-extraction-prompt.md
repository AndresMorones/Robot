# HappyRobot — Post-Call Extraction Prompt

After the call ends, HR runs an LLM pass over the transcript to extract structured data. The output is JSON-parsed and sent in the `call.ended` webhook payload. We force the schema via prompt (HR doesn't publicly advertise schema validation).

This prompt is configured at the **workflow-level Post-Call setting** — distinct from the in-call voice-agent prompt (see `voice-agent-prompt.md`).

## The prompt template (paste into HR's "Post-Call" setting)

```
You are a data-extraction assistant for a freight-brokerage voice-call system. Given the transcript of a carrier call and associated metadata, extract structured data as a single JSON object matching this EXACT schema. Emit ONLY the JSON object — no preamble, no explanation, no markdown fences.

{
  "call_id": "<HR call id — passed through>",
  "started_at": "<ISO 8601 UTC timestamp>",
  "ended_at": "<ISO 8601 UTC timestamp>",
  "mc_number": "<carrier MC normalized to 'MC-123456' format, or null>",
  "carrier_name": "<carrier company name from transcript, or null>",
  "load_id": "<load_id pitched, or null if no load pitched>",
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
  "transcript_summary": "<2–4 sentence plain-language summary>",
  "transcript_url": "<passed through from HR metadata>",
  "recording_url": "<passed through from HR metadata>",
  "agent_metadata": {"workflow_version": "<passed through>"}
}

Rules:
- All field names MUST match exactly (case-sensitive).
- `outcome` MUST be one of the listed enum values.
- If a field can't be determined, use null (nullable fields) or the lowest/neutral value (enums).
- Numeric fields must be bare numbers, not strings.
- Emit valid JSON: no trailing commas, no comments, no NaN/undefined.
- Do not emit any text before or after the JSON object.
```

## Outcome inference guidelines

When setting `outcome`:
- **BOOKED** — explicit rate agreement + carrier confirmation (or transfer triggered after agreement).
- **CARRIER_DECLINED_RATE** — 1+ negotiation rounds, carrier says rate too low / "no deal" / "can't do it."
- **CARRIER_DECLINED_UNAVAILABLE** — carrier says already loaded / no equipment / wrong lane.
- **BROKER_DECLINED_INELIGIBLE** — FMCSA verification failed; agent politely declined.
- **BROKER_DECLINED_NO_MATCH** — `loads_search` returned zero matches.
- **NEGOTIATION_STALLED** — 3 rounds ran without agreement, no explicit decline.
- **CALLBACK_SCHEDULED** — explicit callback time/reason captured.
- **TRANSFERRED_TO_REP** — transfer node fired (BOOKED or ESCALATE path).
- **CALL_ABANDONED** — call dropped / hangup / no clear outcome.
- **NO_LOAD_AVAILABLE** — agent stated upfront "we don't have loads right now" (pre-search).

The model's enum judgment isn't perfect; some fuzziness is acceptable. A future re-labeling UI is out of scope.

## Sentiment scoring

The `sentiment_score` float reflects the carrier's overall tone:
- **+1.0** enthusiastic, collaborative, eager
- **+0.5** positive, engaged
- **0.0** neutral
- **-0.5** hesitant, skeptical, price-resistant
- **-1.0** frustrated, dismissive, unprofessional

The `sentiment_flags` are orthogonal operational signals (not redundant with score).

## Malformed-JSON handling

If HR's LLM emits malformed JSON:
- HR likely falls back to raw string in the webhook payload (unverified — confirm on first real call).
- Our `/v1/calls/log` validates against `CallLogRequest` Pydantic; on validation fail returns 422; HR retries once; if still bad, we drop and emit `calls.log.malformed_payload` log.
- **Prevention**: the "Emit ONLY the JSON" instruction is critical. If LLM wraps in ```json fences, we'd need to strip server-side or stiffen the prompt. Iterate after first real call.

## Versioning

When we change the extraction prompt, note in `changelog.md` with date + reason. The prompt is semantic — changing it mid-collection-period subtly shifts outcome distributions.

## Unresolved (verify in workspace)
- Whether HR supports JSON-mode / structured-output on the post-call LLM (would remove fence-stripping risk).
- Exact passthrough syntax for `transcript_url`, `recording_url`, `workflow_version` into the prompt output.
- Whether HR re-runs extraction on webhook retry (idempotent on our side either way).
