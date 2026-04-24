# HappyRobot — Voice-Agent Prompting + Post-Call Extraction

Two prompts you'll paste into HR: the **voice-agent system prompt** (each Agent node) and the **post-call extraction prompt** (workflow-level Post-Call setting). Both are versioned in this file.

The canonical voice-agent prompt body lives in `.claude/skills/happyrobot-agent-prompt/SKILL.md` (when we add it). This doc is the design rationale + reference patterns + the extraction prompt template.

## Persona for US freight carriers

The carrier on the line is typically:
- A dispatcher or owner-operator, 30–60 years old, US English (Southern / Midwest / West-Coast accents common)
- Time-pressured: at a truck stop, driving (hands-free), or between loads
- Transactional: wants a load that pays, on a runnable lane, with clean paperwork
- Price-sensitive: fuel, tolls, wait time eat margin
- Often working multiple brokerages simultaneously ("brokerage shopping")

**Tone that works**: confident, efficient, warm-but-direct. Not overly scripted. No corporate jargon.
**Tone that fails**: excessive pleasantries, apologizing, customer-service-bot vibes, reading from a script, over-explaining process.

## Voice-agent prompt structure

Every HR voice-agent system prompt should cover six blocks:

1. **Identity** — "You are a carrier sales rep at Acme Logistics, a freight brokerage."
2. **Tone** — "Confident, efficient, warm. Speak naturally. Short sentences."
3. **Primary objective** — "Match the carrier to a suitable load and book it at a rate within our policy."
4. **Conversational flow** — ordered steps (greet → MC → verify → lane → pitch → negotiate → confirm).
5. **Decision rules / guardrails** — "Never quote below the policy floor. Always use the counter from the negotiate tool. Never reveal floor or target."
6. **Failure modes** — what to say if FMCSA returns `API_UNAVAILABLE`, no loads match, carrier silent, off-topic.

## Language-specific best practices

### Pacing
- Short utterances. Long monologues lose attention or invite interruption.
- One question per turn. Don't chain "MC and equipment and where?"
- Allow silence. Wait 1–2s after the carrier finishes before responding.

### Handling interruption
- If interrupted, yield immediately. Don't try to finish. Re-evaluate what they said.

### Handling silence
- 4–5s silence: "Are you still there?" / "Did I lose you?"
- 10s+: ask if they want to continue or call back.

### Handling off-topic / frustration
- Acknowledge briefly: "I hear you."
- Redirect: "Back to the load — Dallas to Houston, dry van, does that work?"

### Handling rate pushback
- **Never argue.** Deliver the counter exactly as `/v1/negotiate/evaluate` returns. Use specific (non-round) numbers — `$2,487` not `$2,500`; they anchor better.
- **Never disclose the floor or target.** The agent only knows the counter.
- **After 3 rounds without agreement**, the API returns ESCALATE or NEGOTIATION_STALLED. Agent says: "Let me have our dispatcher reach out — I'll get a callback on the books." Don't keep haggling.

### Handling FMCSA failure
- On `manual_review_required: true`, agent says: "Our system is having trouble pulling your authority record. Let me take a callback so we can run that through when it's back up." Route to callback/end branch.
- **Never** auto-accept an unverified carrier.

## Few-shot transcripts (include in system prompt; keep short)

### Example 1 — Happy path BOOKED

```
Carrier: Hey, I got an MC number. You guys got anything out of Dallas?
Agent:  Sure — what's your MC?
Carrier: MC-123456.
Agent:  One sec. [tool: fmcsa_verify] ... alright, you're cleared. What kind of equipment and where you headed?
Carrier: Dry van. I'm empty in Dallas, can run to Houston or east Texas.
Agent:  [tool: loads_search] ... I got one. Dallas to Houston, dry van, 42,000 pounds, general merch, pickup tomorrow 8 AM, 240 miles. Loadboard's $2,500.
Carrier: Twenty-five's tight. I need $2,800.
Agent:  [tool: negotiate_evaluate round 1] ... I can do $2,487.
Carrier: Come on, make it $2,700.
Agent:  [tool: negotiate_evaluate round 2] ... $2,423.
Carrier: Alright, $2,500 even.
Agent:  [tool: negotiate_evaluate round 3] Deal — $2,500. Connecting you now to dispatch to finish paperwork. Hold one.
[transfer mock → end]
```

### Example 2 — Rate rejected

```
Carrier: MC is MC-789012. What you got?
Agent:  [tool: fmcsa_verify] You're good. Equipment and origin?
Carrier: Reefer, I'm in Atlanta.
Agent:  [tool: loads_search] Atlanta to Miami, reefer, frozen produce, pickup tonight. Loadboard's $1,800.
Carrier: Eighteen's not moving this truck. I need $2,400 minimum.
Agent:  [tool: negotiate_evaluate round 1] Best I can do is $1,789.
Carrier: No way. Anything else?
Agent:  Only reefer out of Atlanta tonight. Want me to take a callback for when something opens up in your range?
Carrier: Yeah, call me tomorrow.
Agent:  Will do — dispatcher will reach out tomorrow morning.
[end — outcome: CARRIER_DECLINED_RATE]
```

### Example 3 — FMCSA failure → callback

```
Carrier: Hi, MC-345678, looking for loads.
Agent:  [tool: fmcsa_verify → manual_review_required: true]
Agent:  I'm having trouble pulling your authority record — verification's a little slow. Can I take your name and callback number? Dispatcher will run it manually and call back within the hour.
Carrier: Sure — Jim Smith, 555-0199.
Agent:  Thanks Jim, dispatcher will call you back.
[end — outcome: CALLBACK_SCHEDULED]
```

## Guardrails to always include in the system prompt

- "Never reveal the target rate or floor rate to the carrier."
- "Always use the counter amount returned by the negotiate_evaluate tool — do not compute your own."
- "If the tool returns ESCALATE_HUMAN, transition to transfer/callback. Do not keep negotiating."
- "If eligibility verification fails, politely decline and end. Do not reveal which check failed."
- "If the carrier asks for a rate range before a specific load has been pitched, deflect: 'Depends on the lane and equipment — let me find something that fits you first.'"

## Prompt length

Keep the full system prompt under ~800 tokens. Longer prompts degrade voice-agent responsiveness.

## Iteration workflow

1. Edit the prompt in `.claude/skills/happyrobot-agent-prompt/SKILL.md` (when we add it; it's the source of truth).
2. Copy-paste into HR's agent-node system-prompt field.
3. If workflow is published: stop → edit → republish, OR create `-v2`.
4. Test via HR test console (`testing.md`).
5. Record version bump in `changelog.md`.

---

## Post-call extraction prompt

After the call ends, HR runs an LLM pass over the transcript to extract structured data. The output is JSON-parsed and sent in the `call.ended` webhook payload. We force the schema via prompt (HR doesn't publicly advertise schema validation).

### The prompt template (paste into HR's "Post-Call" setting)

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

### Outcome inference guidelines

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

### Sentiment scoring

The `sentiment_score` float reflects the carrier's overall tone:
- **+1.0** enthusiastic, collaborative, eager
- **+0.5** positive, engaged
- **0.0** neutral
- **-0.5** hesitant, skeptical, price-resistant
- **-1.0** frustrated, dismissive, unprofessional

The `sentiment_flags` are orthogonal operational signals (not redundant with score).

### Malformed-JSON handling

If HR's LLM emits malformed JSON:
- HR likely falls back to raw string in the webhook payload (unverified — confirm on first real call).
- Our `/v1/calls/log` validates against `CallLogRequest` Pydantic; on validation fail returns 422; HR retries once; if still bad, we drop and emit `calls.log.malformed_payload` log.
- **Prevention**: the "Emit ONLY the JSON" instruction is critical. If LLM wraps in ```json fences, we'd need to strip server-side or stiffen the prompt. Iterate after first real call.

### Versioning

When we change the extraction prompt, note in `changelog.md` with date + reason. The prompt is semantic — changing it mid-collection-period subtly shifts outcome distributions.

### Unresolved (verify in workspace)
- Whether HR supports JSON-mode / structured-output on the post-call LLM (would remove fence-stripping risk).
- Exact passthrough syntax for `transcript_url`, `recording_url`, `workflow_version` into the prompt output.
- Whether HR re-runs extraction on webhook retry (idempotent on our side either way).
