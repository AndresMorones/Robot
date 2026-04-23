# HappyRobot — Platform Concepts

Core mental models needed before building anything in the HappyRobot UI. Read this first.

## The platform in one paragraph

HappyRobot is an AI orchestration platform for voice agents. Your **workflow** is a DAG of **nodes** (trigger → agents → tool calls → conditions → webhooks → transfer). A **voice agent node** runs an LLM + TTS + ASR pipeline during a live call; it can call out to your HTTP endpoints via **tool-call nodes**. When a workflow is **published**, it becomes immutable and gets a public **web-call trigger URL** that a carrier can dial from a browser. After the call ends, HappyRobot runs a **post-call extraction** LLM pass and fires a **`call.ended` webhook** with the extracted data to your backend.

## Key concepts

### Workflow = DAG of nodes

A workflow is a directed acyclic graph. Each node has typed inputs and outputs. Downstream nodes can reference variables produced by upstream nodes using template syntax (typically `{{variable_name}}` in HR's UI — confirm exact syntax in your HR workspace).

Branching is done via **condition nodes**, not by LLM whim. Example: `if eligible == true → load-pitch path; else → polite-decline path`. Conditions compare variables (usually the response body of an upstream tool call) against literal values.

Nodes must be **tested before publishing** to define their output schema (so downstream nodes know what variables to expect). If you skip node-level testing, the workflow typically refuses to publish.

### Immutable publish + `-v1` / `-v2` versioning

**Published workflows cannot be edited**. To change a live workflow you must either:
- **Stop** it (puts in-flight calls in a weird state; avoid mid-traffic) and re-edit + republish; or
- Create a new workflow named `inbound-carrier-v2` and cut traffic over by updating the caller-facing URL.

Naming convention: always suffix `-v1`, `-v2`, etc. Maintain a `changelog.md` in `docs/references/happyrobot/` documenting what changed and why.

> Design implication for us: the **negotiation state machine** lives in our FastAPI (`api/app/services/negotiation.py`), NOT in HR workflow conditions. Otherwise every policy tweak requires a republish. HR conditions only gate coarse branches (eligible / not-eligible, match / no-match, ACCEPT / COUNTER / REJECT / ESCALATE).

### Web-call trigger

The trigger type we use. Creating a web-call trigger node auto-generates a publicly-dialable URL of the form:

```
https://workflows.platform.happyrobot.ai/hooks/<workflow_id>
```

Opening this URL in a browser starts a WebRTC voice session with the workflow. There is **no phone number purchase** required for the take-home. Capture the URL once (Setup → Test in the trigger node) and record it in `docs/references/happyrobot/web-call-url.txt`.

### Tool calls are synchronous

When the voice agent decides to call a tool, HR makes a **synchronous HTTP request** to the configured URL and waits for the response before continuing the conversation. The carrier hears silence (or filler audio) during the wait.

**Latency budget: ~2–3 seconds**. Beyond that the agent feels broken. Design API endpoints to return within 500 ms hot-path, 2 s worst-case. FMCSA-cache-miss is our tight case — see `docs/references/happyrobot/tool-calls/patterns.md`.

### Post-call extraction + `call.ended` webhook

After the call terminates, HR runs a **post-call LLM pass** on the transcript to extract structured data (you configure the prompt; ours emits a `CallLogRequest` JSON). HR then fires a **webhook** at a URL you configure — typically `POST https://robot-api.fly.dev/v1/calls/log`.

The webhook is the **only path** HR uses to write data back to us after the call. Synchronous tool calls during the call are the other HR→us path.

### AI-worker-as-gatekeeper framing (HR's own positioning)

From HappyRobot's own marketing on [ai-workers-for-logistics](https://www.happyrobot.ai/blog/ai-workers-for-logistics), they position voice agents as:

> "A gatekeeper, qualifying inbound inquiries and routing only legitimate opportunities to human sales representatives."

That framing — agent as qualifier + router, human as closer — is the right narrative for our broker build doc. The agent filters FMCSA-ineligible carriers, confirms equipment + lane match, negotiates within a predefined policy band, and only escalates legit opportunities (ACCEPT / ESCALATE_HUMAN outcomes) to the human rep.

## Data HR stores vs data we store

| Artifact | HR stores | We store |
|---|---|---|
| Audio recording | Yes (pre-signed URL returned via API / webhook) | No — we just link to HR's URL |
| Full transcript | Yes | Just a summary (from post-call extraction) |
| Extracted structured data | Yes + pushed to us via webhook | Canonical copy in `data/calls.json` |
| Metrics / analytics | Yes (platform UI — we're NOT allowed to use this per the take-home) | Computed from `data/calls.json` in `/v1/dashboard/*` |
| Call metadata (start/end time, duration) | Yes | Mirrored in our CallRecord |
| Sentiment / intent | Yes (HR native, under-documented taxonomy) | Our own taxonomy via the extraction prompt |

The dashboard build reads ONLY from `/v1/dashboard/*` (fed by `data/calls.json`). It never calls HR. Guaranteed by the take-home's "don't use HR analytics" rule.

## Two critical invariants

1. **The negotiation floor/target never leave our API.** Only `loadboard_rate` (the ceiling = what we charge the shipper) is exposed to HR as part of a load record. The floor and target live in `data/load-policies.json` and are consumed only by `/v1/negotiate/evaluate`.
2. **Secrets never touch HR's visible fields.** `API_BEARER_TOKEN` is an HR workflow secret (referenced as `{workflow_secret:API_BEARER_TOKEN}` in tool-call headers). `FMCSA_WEB_KEY` is a Fly secret only — HR never sees it.

## Sources

- HappyRobot Technical Overview blog
- HappyRobot AI-workers-for-logistics blog
- HappyRobot docs (`docs.happyrobot.ai`) — note: some pages gated by access code; publicly accessible pages were the primary source. Confirm any specific UI behavior in your workspace.

## Unresolved / needs confirmation in Andres's workspace

- Exact template syntax for variable references in tool-call bodies (`{{var}}` vs `{var}` vs something else).
- Whether "Stop" a published workflow cleanly terminates in-flight calls or lets them finish.
- Whether HR enforces a schema on the post-call extraction prompt's JSON output (see `post-call-extraction.md`).
