# HappyRobot — Platform Essentials

What HappyRobot is, what nodes you'll use, and what'll bite you. Read before building the workflow.

## The platform in one paragraph

HappyRobot is an AI orchestration platform for voice agents. Your **workflow** is a DAG of **nodes** (trigger → agents → tool calls → conditions → webhooks → transfer). A **voice agent node** runs an LLM + TTS + ASR pipeline during a live call; it can call out to HTTP endpoints via **tool-call nodes**. When a workflow is **published**, it becomes immutable and gets a public **web-call trigger URL** that a carrier can dial from a browser. After the call ends, HappyRobot runs a **post-call extraction** LLM pass and fires a **`call.ended` webhook** with the extracted data to your backend.

## Core concepts

### Workflow = DAG of nodes
Directed acyclic graph. Each node has typed inputs/outputs. Downstream nodes reference upstream variables via template syntax (`{{var}}` typical; **confirm in your workspace**). Branching is done via **condition nodes**, not LLM whim. Nodes must be **tested before publishing** — the test defines output schema for downstream typecheck.

### Immutable publish + `-v1` / `-v2` versioning
Published workflows cannot be edited. To change one: stop + edit + republish (interrupts in-flight calls — avoid mid-traffic), OR create `inbound-carrier-v2` (cleaner; keeps v1 call data uncorrupted). Always suffix `-v1`, `-v2`. Maintain `changelog.md` here.

> **Design implication**: the **negotiation state machine** lives in our FastAPI (`api/app/services/negotiation.py`), NOT in HR conditions. Otherwise every policy tweak requires a republish. HR conditions only handle coarse branches (eligible / not, match / not, ACCEPT / COUNTER / REJECT / ESCALATE).

### Web-call trigger
Auto-generates: `https://workflows.platform.happyrobot.ai/hooks/<workflow_id>`. Browser-dialed (WebRTC). No phone-number purchase. Capture once → save to `web-call-url.txt`.

### Tool calls are synchronous
HR fires the HTTP request and **waits** before continuing the conversation. Carrier hears silence (or filler) during the wait. **Latency budget: ~2–3s.** Beyond that the agent feels broken. Design endpoints for p50 <500ms, p99 <2s.

### Post-call extraction + `call.ended` webhook
After the call ends, HR runs a configured LLM prompt over the transcript to extract structured fields. The extracted JSON is sent via webhook to `https://robot-api.fly.dev/v1/calls/log`. Webhook is the **only** path HR uses to write data back to us after the call. (Synchronous tool calls during the call are the other HR→us path.)

### "AI-worker-as-gatekeeper" framing (HR's own positioning)

From HR's blog [ai-workers-for-logistics](https://www.happyrobot.ai/blog/ai-workers-for-logistics):

> "A gatekeeper, qualifying inbound inquiries and routing only legitimate opportunities to human sales representatives."

That framing — agent as qualifier + router, human as closer — is the right narrative for our broker doc.

## Two critical invariants

1. **Negotiation floor/target never leave our API.** Only `loadboard_rate` (the ceiling we charge the shipper) is exposed to HR via load records. Floor + target live in `data/load-policies.json`, consumed only by `/v1/negotiate/evaluate`.
2. **Secrets never touch HR's visible fields.** `API_BEARER_TOKEN` is an HR workflow secret (referenced via `{workflow_secret:API_BEARER_TOKEN}`). `FMCSA_WEB_KEY` is a Fly secret only — HR never sees it.

## Data HR stores vs data we store

| Artifact | HR stores | We store |
|---|---|---|
| Audio recording | Yes (pre-signed URL) | No — we link |
| Full transcript | Yes | Just a summary (from extraction) |
| Extracted structured data | Yes + pushes to us via webhook | Canonical copy in `data/calls.json` |
| Metrics / analytics | Yes (HR UI — **we're forbidden to use it**) | Computed from `data/calls.json` in `/v1/dashboard/*` |
| Sentiment / intent | Yes (HR native, under-documented) | Our taxonomy via the extraction prompt |

The dashboard reads ONLY from our `/v1/dashboard/*`. It never calls HR — required by the take-home.

---

## Node taxonomy

Every node type you'll use. Field-label wording is inferred; confirm in your workspace.

### 1. Web-Call Trigger
**Purpose**: entry point for inbound browser-dialed calls.
- Config: name; (auto-generated, read-only) webhook URL.
- Outputs: `caller_ip` if exposed; URL query-string params if appended.
- Usage: exactly one per workflow; the root node.

### 2. Agent Node (voice agent)
**Purpose**: LLM + TTS + ASR loop. Speaks, listens, decides whether to call a tool or advance.
- Config: system prompt; initial message; voice; tools available to this agent; extracted variables; exit conditions.
- Outputs: all extracted variables.
- Usage: several per workflow (greeting, lane capture, pitch+negotiation, booking confirm).

### 3. Tool-Call Node
**Purpose**: synchronous HTTP call to our FastAPI during the conversation.
- Config: URL, method, headers, body (template-substituted from upstream variables), timeout (2500ms), retries (1).
- Outputs: top-level keys of JSON response body become downstream variables.
- Usage: 4 in our workflow — `fmcsa_verify`, `loads_search`, `negotiate_evaluate`, plus the `call.ended` post-call webhook (workflow-level, not a node).
- **Click-precise patterns**: see `design-notes-for-our-workflow.md` § "Tool-call patterns."

### 4. Condition Node
**Purpose**: route based on variable comparison. Deterministic control flow.
- Config: expression (e.g., `{eligible} == true`); branch mapping.
- Usage: 4 in our workflow — eligibility gate, match gate, action branch, round-count cap.

### 5. Transfer Node
**Purpose**: hand off the call. We **mock** this; see `design-notes-for-our-workflow.md` § "Transfer mock."
- Config: destination (SIP URI / phone / mock); pre-transfer message; mode (cold/warm).

### 6. Webhook Node (in-flow, fire-and-forget)
**Purpose**: outbound HTTP without blocking the conversation. **We don't use any in-flow webhooks** — we prefer synchronous tool calls. The `call.ended` webhook is workflow-level, not a node.

### 7. Post-Call Extraction (workflow-level setting, not a node)
**Purpose**: LLM prompt over the transcript after call ends, emitting our `CallLogRequest` JSON.
- Config: prompt (source of truth in `voice-agent-prompting.md` § "Post-call extraction prompt").

### 8. `call.ended` Webhook (workflow-level setting, not a node)
**Purpose**: HR POSTs JSON to our `/v1/calls/log` after the call ends.
- Config: URL, headers (Bearer + `?token=` fallback), payload.
- Spec: see `design-notes-for-our-workflow.md` § "`call.ended` webhook."

### Our workflow's node count

| Node | Count |
|---|---|
| Web-Call Trigger | 1 |
| Agent — greeting + MC capture | 1 |
| Tool Call — `fmcsa_verify` | 1 |
| Condition — eligibility | 1 |
| Agent — lane + equipment capture | 1 |
| Tool Call — `loads_search` | 1 |
| Condition — match? | 1 |
| Agent — pitch + deliver counter | 1 (reused in loop) |
| Tool Call — `negotiate_evaluate` | 1 (reused in loop) |
| Condition — action branch | 1 (reused in loop) |
| Condition — round cap | 1 |
| Agent — booking confirmation | 1 |
| Transfer (mock — implemented as Agent node) | 1 |
| Agent — polite decline / callback capture | 1 |

Total ≈ 10–12 distinct node instances (some reused in loops). See `design-notes-for-our-workflow.md` for the wired graph.

---

## Gotchas

### Published workflows are immutable
- Stop + edit + republish (interrupts in-flight calls — avoid during demo) OR create `-v2`.
- For our project, prefer `-v2` for material changes — preserves v1 call data.

### 10-minute call duration default
- Hard cap. Configurable per workflow. Our flow targets <5 min.

### Tool-call timeout default is 10s — too loose
- **Set to 2500ms** on every tool-call node. Our API must hit p95 <1500ms.

### Workflow test tab is required before publish
- Untested nodes show orange exclamation; block publish.

### Secrets are workflow-scoped
- Adding `API_BEARER_TOKEN` to v1 doesn't auto-copy to v2. Re-add. Secrets never shown back in plaintext after saving.

### Bearer header support is tier-dependent (rumored)
- Some HR tiers may block custom `Authorization` headers on tool-call nodes. Our API accepts `?token=` as fallback. Test on first tool-call node.

### No HMAC webhook signing
- `call.ended` is Bearer-auth only. We can't cryptographically verify. Mitigations: idempotency by `call_id`, token rotation, anomaly monitoring.

### "We're forbidden to use HR's analytics UI"
- Take-home requirement. Our dashboard reads from `data/calls.json`. Scoring signal — they want product vision, not rebrand.

### Recording URLs are pre-signed + expiring
- Duration unconfirmed (24h–7d). Dashboard drilldown handles expired-URL state gracefully.

### Transcript: online vs offline-enhanced
- Post-call extraction runs on the offline (better) transcript. Use that in `transcript_summary`.

### FMCSA cold-cache is the tightest latency pinch
- First call for a new MC: 200ms–2s. HR timeout is 2500ms. Mitigation: warm top-20 MCs on API startup.

### Don't autoscale Fly beyond 1 machine
- `calls.json` lives on a single Fly volume. Multiple machines = split-brain writes.

### Voice selection affects perception
- HR offers 100+ voices. Pick US-English professional + warm; preview in Voice Playground first.

### Interruption handling is prompt-dependent
- HR's pipeline supports interruption, but the agent's response to it is shaped by the system prompt. Always include "yield immediately if interrupted."

## Sources
- HappyRobot Technical Overview blog
- HappyRobot AI-workers-for-logistics blog
- HappyRobot docs (`docs.happyrobot.ai`) — some pages gated by access code; confirm UI behavior in your workspace.

## Unresolved (verify in your HR workspace)
- Exact template syntax: `{var}` vs `{{var}}` vs `${var}`
- Whether condition nodes support compound expressions (`A AND B`) or require chained conditions
- Whether stopping a published workflow cleanly terminates in-flight calls
- Whether HR enforces JSON schema on the post-call extraction output
