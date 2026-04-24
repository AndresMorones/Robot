# HappyRobot — Voice-Agent System Prompt

The system prompt that runs in each Agent node during a live call. The canonical prompt body lives in `.claude/skills/happyrobot-agent-prompt/SKILL.md` (when we add it). This doc is the design rationale + reference patterns + few-shot transcripts.

> The **post-call extraction prompt** (configured at workflow-level Post-Call setting, runs after the call ends) is a separate concern — see `post-call-extraction-prompt.md`.

## Persona for US freight carriers

The carrier on the line is typically:
- A dispatcher or owner-operator, 30–60 years old, US English (Southern / Midwest / West-Coast accents common)
- Time-pressured: at a truck stop, driving (hands-free), or between loads
- Transactional: wants a load that pays, on a runnable lane, with clean paperwork
- Price-sensitive: fuel, tolls, wait time eat margin
- Often working multiple brokerages simultaneously ("brokerage shopping")

**Tone that works**: confident, efficient, warm-but-direct. Not overly scripted. No corporate jargon.
**Tone that fails**: excessive pleasantries, apologizing, customer-service-bot vibes, reading from a script, over-explaining process.

## Prompt structure

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
