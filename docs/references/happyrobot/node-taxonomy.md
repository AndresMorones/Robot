# HappyRobot — Node Taxonomy

Catalog of every node type you'll use when building `inbound-carrier-v1`. Each entry: purpose, key config fields, outputs available downstream, and a typical-usage note.

Flag: some config field names are inferred from platform conventions; confirm exact UI wording in your HR workspace.

---

## 1. Web-Call Trigger

**Purpose**: entry point for inbound browser-dialed calls.

**Key config**:
- Name (e.g., `inbound_web_call`)
- (Auto-generated, read-only) webhook URL to dial

**Outputs available downstream**:
- `caller_ip` (if HR exposes it)
- Any query-string params appended to the URL (we don't need these for our flow)

**Typical usage**: exactly one per workflow; it's the root node. Capture the generated URL and save in `docs/references/happyrobot/web-call-url.txt`.

---

## 2. Agent Node (voice agent)

**Purpose**: runs an LLM + TTS + ASR loop. Speaks to the caller, listens, decides whether to call a tool or move to the next node.

**Key config**:
- **System prompt** — the voice persona, tone, objectives, decision rules. Source of truth in `.claude/skills/happyrobot-agent-prompt/SKILL.md`; paste into HR on republish.
- **Initial message** — first utterance when the agent starts. Can reference variables from upstream nodes: `"Hi, this is Acme Logistics — may I have your MC number?"`.
- **Voice** — select from HR's library (100+ voices, multiple languages). Pick a US-English voice appropriate for freight-broker tone.
- **Tools available to this agent** — list of tool-call nodes this agent can invoke. Typically scoped per node so the agent can only call what's relevant here.
- **Extracted variables** — named variables the agent extracts from the conversation (e.g., `mc_number`, `equipment_type`, `origin_state`, `destination_state`, `carrier_offer`). These become downstream variables.
- **Exit conditions** — what makes this agent node return control to the workflow (tool-call completion, variable extracted, time limit, etc.).

**Outputs available downstream**: all extracted variables.

**Typical usage**: multiple per workflow — one for greeting/MC-capture, one for lane/equipment capture, one for load pitch + negotiation, one for booking confirmation.

---

## 3. Tool-Call Node

**Purpose**: make a synchronous HTTP call to an external endpoint (our FastAPI) during the conversation. Response fields become downstream variables.

**Key config**:
- **URL** — your endpoint (e.g., `https://robot-api.fly.dev/v1/fmcsa/verify`)
- **Method** — POST / GET
- **Headers** — `Content-Type: application/json`, `Authorization: Bearer {workflow_secret:API_BEARER_TOKEN}` (fallback `?token=<...>` in the URL if custom headers are blocked on your tier)
- **Body / query params** — variable-substituted from upstream context. Syntax is template-based (e.g., `{"identifier": "{{mc_number}}", "identifier_type": "MC"}`)
- **Timeout** — default 10s is too loose; set to 2500 ms
- **Retries** — 1 recommended
- **Output schema** — set by testing the node with a sample payload (Test tab)

**Outputs available downstream**: all top-level keys of the JSON response body become variables accessible by name.

**Typical usage**: four in our workflow — `fmcsa_verify`, `loads_search`, `negotiate_evaluate`, and implicitly `calls_log` (fired via the post-call webhook, not during the call).

Details in `docs/references/happyrobot/tool-calls/patterns.md`.

---

## 4. Condition Node

**Purpose**: route the workflow based on comparison of variables to literal values. The workflow's deterministic control flow.

**Key config**:
- **Expression** — e.g., `{eligible} == true`, `{matches.length} > 0`, `{action} == "COUNTER"`
- **Branch mapping** — which downstream node each branch leads to (if/else, or switch-style)

**Outputs available downstream**: none of its own; it just routes.

**Typical usage**: four in our workflow — eligibility gate (after `fmcsa_verify`), match gate (after `loads_search`), action gate (after each `negotiate_evaluate` round), round-count gate (to cap at 3 rounds).

---

## 5. Webhook Node (outbound, during-flow)

**Purpose**: fire-and-forget HTTP call (typically POST) to an external URL, usually without waiting for response in the conversational loop.

**Key config**: URL, method, headers, body — similar to tool-call node.

**Typical usage**: rarely during a call (we prefer synchronous tool calls); sometimes used for side-effecting notifications (Slack ping, etc.). Our workflow uses 0 in-flow webhooks.

Note: the **post-call `call.ended` webhook** is a separate workflow-level configuration, not a node. See `webhooks/call-ended.md`.

---

## 6. Transfer Node

**Purpose**: hand off the call to a human or another destination. For the take-home we mock this — see `transfer-mock.md`.

**Key config**:
- **Destination** — SIP URI, phone number, or "mock" (end-call with message)
- **Pre-transfer message** — what the agent says before hanging off/ending
- **Transfer mode** — cold (blind) / warm (attended). For mock we just say the message and end.

**Typical usage**: one in our workflow, at the end of the BOOKED branch, configured as mock.

---

## 7. Post-Call Extraction (workflow-level, not a node)

**Purpose**: after the call ends, run a configured LLM prompt over the full transcript to extract structured fields.

**Key config**:
- **Prompt** — the template that tells the LLM what to extract, in what schema. Source of truth in `docs/references/happyrobot/post-call-extraction.md`.
- **Output schema** — we force `CallLogRequest` JSON. HR doesn't (publicly) advertise schema validation, so our prompt must be airtight.

**Output**: the extracted JSON is sent to the `call.ended` webhook target.

Details in `post-call-extraction.md`.

---

## 8. `call.ended` Webhook (workflow-level, not a node)

**Purpose**: HR POSTs a JSON payload to a configured URL after the call ends (after post-call extraction runs).

**Key config**:
- **URL** — `https://robot-api.fly.dev/v1/calls/log`
- **Headers** — `Authorization: Bearer ...` (+ same `?token=` fallback as tool calls)
- **Payload** — HR merges call metadata + extracted JSON; we parse it as `CallLogRequest`

Details in `webhooks/call-ended.md`.

---

## Our workflow's node count (for reference)

| Node | Count | Notes |
|---|---|---|
| Web-Call Trigger | 1 | Root |
| Agent (greeting + MC capture) | 1 | Extracts `mc_number` |
| Tool Call — `fmcsa_verify` | 1 | Hits our API |
| Condition — eligibility | 1 | Routes by `eligible` + `manual_review_required` |
| Agent (lane + equipment capture) | 1 | Extracts `origin_state`, `destination_state`, `equipment_type`, `earliest_pickup` |
| Tool Call — `loads_search` | 1 | Hits our API |
| Condition — match? | 1 | Routes by `matches.length > 0` |
| Agent (pitch + negotiation round) | 1 (reused in loop) | Extracts `carrier_offer`, delivers counter |
| Tool Call — `negotiate_evaluate` | 1 (reused in loop) | Hits our API |
| Condition — action branch | 1 (reused in loop) | Routes ACCEPT/COUNTER/REJECT/ESCALATE |
| Condition — round cap | 1 | Breaks loop at round 3 |
| Agent (booking confirmation) | 1 | Reached only on BOOKED |
| Transfer (mock) | 1 | Graceful end on BOOKED and ESCALATE |
| Agent (polite decline / callback) | 1 | Reached on ineligible, no-match, API_UNAVAILABLE |

Total ≈ 10–12 distinct node instances (some reused in loops). See `design-notes-for-our-workflow.md` for the full wired graph.

## Unresolved / needs confirmation

- Exact variable-substitution syntax (`{var}` vs `{{var}}`) in tool-call bodies.
- Whether condition nodes support compound expressions (`A == true AND B > 0`) natively or require chained conditions.
- Whether there's a "loop" primitive or if looping is done via condition + back-edge only.
