# HappyRobot — Platform Essentials

What HappyRobot is, what nodes you'll use in `inbound-carrier-v4`, and what'll bite you. Read before building the workflow.

> **Deep platform reference** lives at `C:\Users\Andre\happyrobot-kb\` (outside repo). This file is the **opinionated project-scoped subset** for the inbound-carrier take-home. For anything not here, drill into the KB: `MANIFEST.md` has a topic index + verb-first lookups.

**KB quick-drill**:
- Workflow / node DAG / versioning → [platform/overview.md](file:///C:/Users/Andre/happyrobot-kb/platform/overview.md), [environments-versioning.md](file:///C:/Users/Andre/happyrobot-kb/platform/environments-versioning.md)
- Node catalog (every type) → [authoring/nodes-core.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-core.md), [nodes-builtin.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-builtin.md), [nodes-control-flow.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-control-flow.md), [nodes-integration.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-integration.md)
- **Variable syntax rules → [authoring/variables.md](file:///C:/Users/Andre/happyrobot-kb/authoring/variables.md)** (critical: `{{<persistent_id>.var}}` only; use `@` picker, never hand-type)
- Voice-agent model / voice / ASR / TTS / turn-taking → [voice/](file:///C:/Users/Andre/happyrobot-kb/voice/)
- Gotchas across all domains → [GOTCHAS.md](file:///C:/Users/Andre/happyrobot-kb/GOTCHAS.md)
- Open questions for Andres → [OPEN-QUESTIONS.md](file:///C:/Users/Andre/happyrobot-kb/OPEN-QUESTIONS.md)

## The platform in one paragraph

HappyRobot is an AI orchestration platform for voice agents. Your **workflow** is a DAG of **nodes** (trigger → agents → tool calls → webhooks → classifiers → extract → enrichment). A **voice agent node** runs an LLM + TTS + ASR pipeline during a live call; it can call out to HTTP endpoints (external APIs like ours) OR run Python Code natively via **tool-call nodes**. When a workflow is **published**, it becomes immutable — to change it, fork a new version. After the call ends, HR runs a post-call chain (classify + extract + compute + audit) and fires a **`call.ended` webhook** with the full `CallLogRequest` to our `/v1/calls/log`.

## Core concepts (v4)

### Workflow = DAG of nodes

Directed acyclic graph. Each node has typed inputs/outputs. Downstream nodes reference upstream variables via `{{<persistent_id>.variable_id}}` — **always use the `@` picker to insert these**; HR's template engine needs the exact persistent_id UUID. Hand-typing `{{mc_number}}` or `{{trigger.mc_number}}` silently renders as empty at runtime.

Tested before publishing — untested nodes block publish with a ⚠️ indicator.

### Immutable publish + forked versions

Published workflows cannot be edited. Our pattern:
- **Version 3** = published baseline. Stays untouched as rollback.
- **`inbound-carrier-v4`** = forked from Version 3 via Unlock. All v4 work happens here. Published to **Development** first; later to Production.

### Web-call trigger (no phone number required)

Auto-generates a browser-dialable URL. Exposes auto-populated variables at runtime:
- `room_name` — unique WebRTC room ID per call (our correlation key in `calls.json`).
- `to_number` — literal string `"web"` (distinguishes web-call runs from telephony).
- `from_number` — literal string `"web"`.

Plus any custom payload fields declared in the trigger's schema (we declare `session_tag` for demo-video call tagging).

### Tool calls are synchronous

HR fires the request and **waits** before continuing the conversation. Carrier hears silence (or filler) during the wait. Latency budget: p50 <500ms, p95 <2s, hard ceiling 2500ms.

Our 4 tools under the Prompt node:

| Tool | Type | Target |
|---|---|---|
| `verify_carrier` | HTTP GET | HR-provided FMCSA demo: `https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}?webKey=...` |
| `find_available_loads` | HTTP GET | Our `/v1/loads/{reference_number}` |
| `search_loads_by_lane` | HTTP GET | Our `/v1/loads/search` |
| `negotiate_evaluate` | Python Code (security sidecar) | Runs in HR's Custom Code sandbox; main Prompt never sees floor/target/discount |

### Post-call chain + `call.ended` webhook

The chain fires after the call terminates:

```
Classify Outcome (8 tags) → Classify Sentiment (4 tags) → Extract
  → Computations (max_buy, discount_pct)
  → Case Health Score (int 0–100)
  → Carrier Sales Auditor (audit_remarks)
  → Transfer Popup (BOOKED only)
  → Enrichment (Split-up, From Past Capacity, Find Matching Carriers, From Truckstop)
  → POST `call.ended` → our `/v1/calls/log`
```

`call.ended` is the ONLY path HR uses to write data back to us post-call (tool calls during the call are the other HR→us path). No HMAC signing; Bearer auth only. Idempotency is our responsibility on the receiving side (by `call_id` + `room_name`).

### "AI-worker-as-gatekeeper" framing (HR's own positioning)

From HR's blog [ai-workers-for-logistics](https://www.happyrobot.ai/blog/ai-workers-for-logistics):

> "A gatekeeper, qualifying inbound inquiries and routing only legitimate opportunities to human sales representatives."

That framing — agent as qualifier + router, human as closer — is the right narrative for our broker doc.

## Two critical invariants (v4)

1. **Negotiation policy numbers stay inside the `negotiate_evaluate` sidecar.** The main Prompt gets `loadboard_rate` (needed for pitch) BUT never gets `floor_rate`, `target_rate`, `max_buy`, or the discount percentages — those are computed inside the Python Code tool and never returned to the Prompt's context. Prompt injection attempts cannot extract what isn't in the context window. Policy is tunable via the 4 workflow variables without touching the sidecar code.
2. **Secrets never touch HR's visible fields.** `API_BEARER_TOKEN` is an HR workflow secret (referenced via `{workflow_secret:API_BEARER_TOKEN}` in tool headers; same value set on Fly). `FMCSA_WEB_KEY` = HR demo endpoint's key — already public in the webhook URL, so not sensitive for us.

## Data HR stores vs data we store

| Artifact | HR stores | We store |
|---|---|---|
| Audio recording | Yes (pre-signed URL) | No — we link |
| Full transcript | Yes | Just a summary (from Extract) |
| Extracted structured data | Yes + pushes to us via `call.ended` webhook | Canonical copy in `data/calls.json` |
| Metrics / analytics | Yes (HR's UI — **we're forbidden to use it per spec**) | Computed from `data/calls.json` via `/v1/dashboard/*` |
| Sentiment / outcome tags | Via Classify nodes | Canonical copy in `data/calls.json` (from Extract) |
| Audit remarks | Via Carrier Sales Auditor | Canonical copy in `data/calls.json` (in `audit_remarks` array) |
| Enrichment (Split-up, Capacity) | Via enrichment group | Canonical copy in `data/calls.json` (in `enrichment_data`) |
| Carrier contact memory (in-call recall) | Yes (Contact Intelligence enabled) | Our aggregate via `GET /v1/carrier-profile/{mc_number}` (complementary) |

The dashboard reads ONLY from our `/v1/dashboard/*`. It never calls HR — required by the take-home.

---

## Node taxonomy (what we actually use in v4)

Only the node types that appear in `inbound-carrier-v4`. For the full HR node catalog see [nodes-builtin.md](file:///C:/Users/Andre/happyrobot-kb/authoring/nodes-builtin.md).

### 1. Web-call trigger (AI Agent type, the root node)
- Auto-generated URL; no payload schema strictly required. We declare an optional `session_tag` field to tag demo calls.
- Exposes `room_name`, `to_number="web"`, `from_number="web"` + any declared schema fields.

### 2. Inbound Voice Agent (container)
- LLM + TTS + ASR pipeline for the live call. Holds the Prompt node + tool children.
- Configured: Languages=en-US, Voice=Paul, noise reduction=on, background=Call center, recording=on, max duration=600s, Contact Intelligence enabled (interaction_limit=3).

### 3. Prompt node (nested inside Voice Agent)
- Model: `gpt-4.1` (default, ~800ms).
- Body: freight-persona prompt (see `voice-agent-prompt.md`) parameterized by 4 workflow variables (`company_name`, `agent_name`, `max_negotiation_rounds`, and implicitly `negotiation_floor_pct` via the sidecar).
- Children: 4 tool nodes.

### 4. Tool nodes (4, children of Prompt)
- `verify_carrier` → Webhook GET (HR demo FMCSA).
- `find_available_loads` → Webhook GET (our API).
- `search_loads_by_lane` → Webhook GET (our API).
- `negotiate_evaluate` → Python Code (security sidecar).

### 5. Mock transfer — Agent node
- Single-utterance Agent placed after the Inbound Voice Agent container. Says the transfer line + ends the call. Per spec, actual SIP transfer is out of scope.

### 6. AI Classify (×2)
- **Classify Outcome**: 8-tag enum (BOOKED / CARRIER_DECLINED_RATE / CARRIER_DECLINED_UNAVAILABLE / BROKER_DECLINED_INELIGIBLE / BROKER_DECLINED_NO_MATCH / NEGOTIATION_STALLED / CALLBACK_SCHEDULED / ABANDONED).
- **Classify Sentiment**: 4-tag enum (POSITIVE / NEUTRAL / NEGATIVE / FRUSTRATED).

### 7. AI Extract
- Full `CallLogRequest` schema with `additionalProperties: false` everywhere (JSON Schema strict mode). Schema in `post-call-extraction-prompt.md`.

### 8. Computations (Python Code)
- Post-call. Computes `max_buy = loadboard_rate × (1 − negotiation_floor_pct)` and `discount_pct`. Surfaces `max_buy` for the Auditor; never spoken during the call.

### 9. Case Health Score
- Post-call node. Emits integer 0–100.

### 10. Carrier Sales Auditor (Built-in)
- Domain-specific quality audit against carrier-sales northstars. Emits `audit_remarks` array.

### 11. Transfer Popup (Built-in, on BOOKED path)
- Ships a structured context payload (phone, summary, transcript, load details) — production-ready warm-handoff pattern even though transfer is mocked.

### 12. Enrichment group (conditional)
- **Split-up** (every call): midpoint comparison for A/B analysis.
- **From Past Capacity** (every call): historical hauling record by MC.
- **Find Matching Carriers** (on CARRIER_DECLINED_*): alternative carrier MCs.
- **From Truckstop** (on BROKER_DECLINED_NO_MATCH): Truckstop alternatives.

### 13. Workflow-level webhook — `call.ended`
- POST to our `/v1/calls/log` with the full CallLogRequest payload. Bearer auth. Retry 2 × exponential backoff.

---

## Gotchas (v4)

### Published workflows are immutable
- Fork to a new version via Unlock (we did v3 → v4). Never try to edit a published version in-place.

### 10-minute call duration default
- Hard cap. We set 600s — targets <5 min real calls, 10 min headroom.

### Tool-call timeout default is 10s — too loose for voice
- Set to 2500ms on every tool-call node. Our API targets p95 <1500ms; Python Code tool runs in-platform (<100ms).

### Node test required before publish
- Untested nodes show orange ⚠️; block publish. Click **Test** on every node.

### HR variable references — use the @ picker, never hand-type
- `{{<persistent_id>.variable_id}}` is the only format that resolves. Hand-typed `{{mc_number}}` or `{{verify_carrier.mc_number}}` silently renders as empty string at runtime. Use the `@` picker and HR inserts the correct UUID.

### Secrets are workflow-scoped
- Workflow secret `API_BEARER_TOKEN` lives in v4's settings. When forking from v3, re-add the secret — it doesn't auto-copy. Secrets are never shown back in plaintext after saving.

### Bearer header support is tier-dependent (rumored)
- Some HR tiers may block custom `Authorization` headers on tool-call nodes. Our API accepts `?token=` fallback. Test on first tool-call node.

### No HMAC webhook signing
- `call.ended` is Bearer-auth only. We can't cryptographically verify. Mitigations: idempotency by `call_id` + `room_name`, token rotation, anomaly monitoring.

### FMCSA response for unknown MC
- `content` field is `null` (not a 404). Handle null-check in the Prompt (see `voice-agent-prompt.md` Step 2 FMCSA handler).

### Recording URLs are pre-signed + expiring (1–7 days)
- Dashboard drilldown must gracefully handle expired URLs.

### Eligibility = three-field AND gate
- `allowedToOperate == "Y"` AND `statusCode == "A"` AND `censusType == "C"`. Any one fails → decline.

### Keep prompt under ~800 tokens
- Voice-agent responsiveness degrades above that. Trim Example section first if we hit the cap.

## Sources
- HappyRobot Technical Overview blog
- HappyRobot AI-workers-for-logistics blog
- HappyRobot docs (`docs.happyrobot.ai`) — mirrored to `C:\Users\Andre\happyrobot-kb\` (frozen 2026-04-24).
- Live console inspection with Andres (2026-04-24): IA labels, auto-populated trigger variables, LLM catalog confirmation.

## Unresolved (verify in HR workspace)

- Exact `safetyRating` enum values beyond null / SATISFACTORY / CONDITIONAL / UNSATISFACTORY.
- Whether HR's webhook retry 429s count against platform rate limits.
- Whether Carrier Sales Auditor has sibling types beyond the one we're using.
- Whether `Capacity → From Past Capacity` queries our `/v1/calls/log` data or HR's internal ledger.
