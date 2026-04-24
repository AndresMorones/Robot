# Design Notes for `inbound-carrier-v1`

**Start here** when actually building the workflow in HR. This is the prescriptive build guide; `platform-essentials.md` is descriptive reference for context.

## Prerequisites

- FastAPI deployed to Fly.io with endpoints live: `/v1/fmcsa/verify`, `/v1/loads/search`, `/v1/negotiate/evaluate`, `/v1/calls/log`.
  - Alternative: local API + ngrok tunnel during dev; swap URLs to Fly before publish.
- `API_BEARER_TOKEN` generated and stored in (a) Fly secret on `robot-api`, (b) HR workflow secret.
- `FMCSA_WEB_KEY` stored in Fly secret.
- You've skimmed `platform-essentials.md`.

---

## Step-by-step workflow construction

### Step 1 — Create the workflow
1. HR platform → New Workflow → Name: `inbound-carrier-v1`.
2. Workflow Settings → Secrets → Add `API_BEARER_TOKEN` (paste value; store in your password manager — HR won't show it back).
3. Post-Call + Webhooks settings configured later (Steps 12–13).

### Step 2 — Add Web-Call Trigger
1. Add node → Web-Call Trigger → Name: `inbound_web_call`.
2. Test the node → copy the auto-generated URL → save to `docs/references/happyrobot/web-call-url.txt`.

### Step 3 — Greeting + MC-capture agent
1. Add Agent node → Name: `greet_and_capture_mc`.
2. System prompt: paste the "Greeting + MC Capture" section (from `voice-agent-prompt.md` source-of-truth).
3. Initial message: `"Hi, this is Acme Logistics. May I have your MC or DOT number?"`
4. Voice: pick US-English professional (preview in Voice Playground first).
5. Extract variable: `mc_number` (normalize to `MC-123456` format).
6. Tools available: (none here).
7. Exit condition: `mc_number` extracted.
8. Test with a sample utterance → confirm `mc_number` output.

### Step 4 — Tool call: `fmcsa_verify`
Configure per "Tool-call patterns" reference below. URL: `https://robot-api.fly.dev/v1/fmcsa/verify`. Body:
```json
{"identifier": "{{mc_number}}", "identifier_type": "MC"}
```
Test with a real MC from `data/fmcsa-fixtures/`. Confirm response has `eligible`, `reason_codes`, `carrier_name`, `manual_review_required`.

### Step 5 — Condition: eligibility gate
1. Add Condition node → Name: `eligibility_gate`.
2. Expression — route on `{eligible}` and `{manual_review_required}`:
   - `{eligible} == true AND {manual_review_required} == false` → continue (Step 6).
   - `{eligible} == true AND {manual_review_required} == true` → callback branch (Step 10a).
   - Else → polite decline (Step 10b).
3. If HR doesn't support compound expressions, chain two conditions.

### Step 6 — Lane + equipment capture agent
1. Add Agent node → Name: `capture_lane_equipment`.
2. System prompt: "Lane & Equipment" section.
3. Extract: `origin_state`, `destination_state`, `equipment_type` (enum), `earliest_pickup` (date).
4. Exit: all 4 extracted (or "anywhere" → null).

### Step 7 — Tool call: `loads_search`
URL: `https://robot-api.fly.dev/v1/loads/search`. Body:
```json
{
  "origin_state": "{{origin_state}}",
  "destination_state": "{{destination_state}}",
  "equipment_type": "{{equipment_type}}",
  "pickup_after": "{{earliest_pickup}}",
  "max_results": 3
}
```
Test with a sample matching seeded `data/loads.json`.

### Step 7b — Condition: match gate
- `{matches.length} > 0` → pitch + negotiation (Step 8). Else → no-match branch (Step 10c).

### Step 8 — Pitch + negotiation loop

**8a. Pitch agent** (Agent node → `pitch_and_round_1`)
- Pitches `{matches[0]}` including `loadboard_rate`.
- Extracts: `carrier_interested` (bool), `carrier_offer` (int).
- Sets workflow variable `round_number = 1`.

**8b. Tool call: `negotiate_evaluate`**
URL: `/v1/negotiate/evaluate`. Body:
```json
{
  "load_id": "{{matches[0].load_id}}",
  "round_number": "{{round_number}}",
  "carrier_offer": "{{carrier_offer}}",
  "prior_broker_offers": "{{prior_broker_offers}}"
}
```
Response fields used: `action`, `broker_counter`, `should_transfer`.

**8c. Condition: action branch**
- `ACCEPT` → confirmation agent (Step 9).
- `REJECT` → outcome = CARRIER_DECLINED_RATE → end (Step 10).
- `ESCALATE_HUMAN` → transfer mock (Step 11).
- `COUNTER` → deliver-counter agent (8d).

**8d. Deliver counter agent**
- Reads `{broker_counter}` to the carrier.
- Extracts new `carrier_offer`.
- Appends to `prior_broker_offers`. Increments `round_number`.

**8e. Round-cap condition**
- `{round_number} > 3` → outcome = NEGOTIATION_STALLED → end (Step 10).
- Else → loop to Step 8b.

### Step 9 — Booking confirmation agent
- Reached only on ACCEPT.
- Says "Deal at $X. Let me have dispatch send the BOL."
- Extracts dispatch email / phone.
- → Step 11 (transfer mock).

### Step 10 — Polite-decline / callback branches
- **10a callback**: capture name + callback number → end.
- **10b polite decline**: "I'm sorry, we can't work with you right now" (don't reveal why) → end.
- **10c no-match**: "Nothing in your lane right now — can I take a callback?" → capture → end.

### Step 11 — Transfer mock
See "Transfer mock" reference below.

### Step 12 — Post-Call extraction
- Workflow Settings → Post-Call → paste the prompt from `post-call-extraction-prompt.md`.
- Test with a sample transcript if HR supports offline testing.

### Step 13 — `call.ended` webhook
- Workflow Settings → Webhooks → add `call.ended`.
- URL: `https://robot-api.fly.dev/v1/calls/log`.
- Headers: same auth as tool calls.
- See "`call.ended` webhook" reference below.

### Step 14 — Publish
- Verify every node is green-checked (tested).
- Click Publish.
- Confirm web-call URL still works.

### Step 15 — Smoke test
- One real web-call end-to-end with a known MC.
- Watch `fly logs -a robot-api` in another terminal.
- Verify: `fmcsa_verify` fires, `loads_search` fires, ≥1 `negotiate_evaluate` fires, `call.ended` lands, CallRecord appears in `data/calls.json`.
- Capture transcript + webhook payload → save to `smoke-tests/2026-MM-DD-<scenario>.md`.

### Versioning reminder
Material change post-publish → create `inbound-carrier-v2`. Don't stop-edit-republish v1 during demo. Record in `changelog.md`.

### Common first-build issues
1. **Tool-call headers rejected**: pivot every node to `?token=` query-string URL. Update all 4 nodes consistently.
2. **Variable syntax mismatch**: try `{var}` / `{{var}}` / `${var}` until substitution works. Document in workspace.
3. **Compound expression fail**: chain two conditions instead.
4. **Response-field mapping breaks**: always test tool-call nodes before wiring downstream conditions.
5. **Publish blocked on orange exclamation**: click through each node looking for the warning.

---

## Reference: Tool-call patterns

Click-precise patterns for configuring every tool-call node in our workflow.

### URL
- Production: `https://robot-api.fly.dev/v1/{endpoint}`
- Local dev: `https://<random>.ngrok-free.app/v1/{endpoint}` (tunnel via `ngrok http 8000`); swap to Fly before publish.

### Method
POST for all our tool calls.

### Headers — auth
**Preferred (Bearer header)**:
```
Authorization: Bearer {workflow_secret:API_BEARER_TOKEN}
Content-Type: application/json
```

The `{workflow_secret:...}` syntax references the secret stored at workflow level (Step 1 above). Set once; reference everywhere.

**Fallback (query-string token)** if your tier blocks custom Authorization headers:
```
URL: https://robot-api.fly.dev/v1/{endpoint}?token={workflow_secret:API_BEARER_TOKEN}
Headers: Content-Type: application/json   (only)
```

Our `app/deps.py::require_bearer` accepts both. Query-string path emits a `auth.query_string_used` warning so we can quantify fallback usage.

**Never** hard-code the token value. Always reference via `{workflow_secret:...}`.

### Timeout
**2500 ms** on every tool-call node. (HR default is often 10s — too loose; voice agent feels broken beyond 3s of silence.)

### Retries
**1 retry** on 5xx or timeout. No retry on 4xx.

If double-fail (primary + retry both fail): tool node returns failure state → downstream condition routes to soft-apology + callback branch. Voice agent reads pre-canned: "Our system's a little slow right now — let me take a callback."

### Variable mapping (request body)
Template-substitute upstream variables. Syntax candidate: `{{var}}` (most common); also try `{var}` or `${var}` if substitution doesn't work. **Confirm in your workspace on first test.**

### Response parsing
HR auto-parses JSON response body. Top-level keys become downstream variables. **Test the node before wiring any downstream condition** — the test run is what tells HR the response schema.

### Error handling design contract
Our endpoints don't 5xx on expected upstream failures:
- `/v1/fmcsa/verify` returns 200 with `manual_review_required: true` instead of 5xx when FMCSA is down.
- `/v1/loads/search` returns 200 with `matches: []` instead of 5xx on empty result.

So the tool-call node doesn't fail; the workflow condition node handles fallback gracefully.

The only endpoints that can actually 5xx are `/v1/negotiate/evaluate` (bug in our code) and `/v1/calls/log` (storage failure). Both handled via retry + soft-apology.

### Idempotency
Our API endpoints are idempotent where it matters:
- `fmcsa_verify` — 24h cache by identifier
- `loads_search` — pure read
- `negotiate_evaluate` — pure function, stateless
- `calls_log` — upsert by `call_id`; replay returns `created: false`

So HR's retry policy is safe.

### Latency budget
| Endpoint | Target p50 | Hard max |
|---|---|---|
| `fmcsa/verify` (cache hit) | <50 ms | 500 ms |
| `fmcsa/verify` (cache miss) | 300 ms | 2000 ms |
| `loads/search` | <50 ms | 500 ms |
| `negotiate/evaluate` | <10 ms | 100 ms |
| `calls/log` | <50 ms | 1000 ms |

If any hot endpoint approaches hard max, agent flow stalls audibly.

---

## Reference: Transfer mock

Per the take-home spec: "Transfer is out of scope as it won't work with the web call, you can mock a message."

### Implementation pattern (Agent node, NOT real Transfer node)

Use an **Agent node** with a single utterance + exit-on-completion. Reason: a real Transfer node with a dummy SIP destination may try to dial and surface a "transfer failed" error in the call log. An Agent node that just says a line and ends produces clean log output.

### Agent-node mock config
- **Name**: `transfer_mock`
- **System prompt**: `"Say exactly: 'Great, I've got everything I need. I'm connecting you now to our dispatch team to finalize the paperwork. Please hold for a moment.' Then stop speaking and exit this node."`
- **Initial message**: (leave empty — the system prompt drives the utterance)
- **Voice**: same as the main agent (continuity)
- **Extracted variables**: none
- **Exit condition**: "after single utterance complete" (or whatever HR labels its one-shot mode)

After this node, the workflow reaches a terminal state. HR ends the call, fires `call.ended`, our API records `outcome: TRANSFERRED_TO_REP` (or `BOOKED` on the BOOKED→transfer path; the post-call extraction disambiguates via transcript).

### What the HR call log shows
Clean: final agent utterance, normal call-end status, duration recorded, no failed-dial error.

### For the broker doc
Document honestly: "transfer is wired at the workflow level as a graceful end-call; real SIP transfer is out of scope for the take-home demo but would slot into the same workflow position."

### Real-transfer-in-production (worth mentioning in broker doc's future-sprint section)
HR supports SIP-based transfer via Twilio / Telnyx / direct trunk. Configure a Transfer node with real SIP URI; warm vs cold transfer is a node setting. Zero code changes on our side.

### Unresolved
- Whether HR's Transfer node has a built-in "mock" or "end-call-gracefully" mode that does this without using an Agent node.
- Whether the Agent-node approach triggers `call.ended` the same way (test on first build).

---

## Reference: `call.ended` webhook

The only path HR uses to write data back to us after the call. **Workflow-level setting**, not a node.

### When it fires
After the call terminates AND post-call extraction completes. HR waits for extraction so the payload carries the structured data, not just metadata.

### Configuration
- **URL**: `https://robot-api.fly.dev/v1/calls/log`
- **Method**: POST
- **Headers**: `Authorization: Bearer {workflow_secret:API_BEARER_TOKEN}` + `Content-Type: application/json`
  - Fallback: `?token={workflow_secret:...}` in URL
- **Retries**: enable platform retries (we're idempotent)
- **Timeout**: HR default fine; our endpoint p95 < 500 ms

### Payload shape (approximate; verify on first real call)

```json
{
  "event": "call.ended",
  "call_id": "hr_call_abc123",
  "workflow_id": "inbound-carrier-v1",
  "workflow_version": "1",
  "started_at": "2026-04-23T18:02:00Z",
  "ended_at": "2026-04-23T18:09:35Z",
  "duration_seconds": 455,
  "status": "completed",
  "transcript_url": "https://hr-assets.example.com/transcripts/...?sig=...",
  "recording_url": "https://hr-assets.example.com/recordings/...?sig=...",
  "extracted": { /* CallLogRequest JSON from post-call extraction */ }
}
```

Our `/v1/calls/log` handler tries `.extracted` first, then falls back to root — handles both nesting shapes HR might use.

### Authentication
Bearer token only. **No HMAC signing in HR's public webhook docs** — we can't cryptographically verify the request. Mitigations: idempotency by `call_id`, scoped-token, rotation on suspicion, anomaly monitoring.

### Idempotency (critical)
HR retries on 5xx / timeout. If our API 5xx's once and recovers, HR may POST the same `call.ended` twice. Our `/v1/calls/log`:
- Keys by `call_id`. First call: creates, returns `{call_id, created: true, stored_at}`. Replay: no-op, returns `{call_id, created: false, stored_at}`.
- We do NOT merge partial updates. If HR sends a different payload for the same `call_id`, we keep the first record and log a warning.

### Debugging chain
1. API log emits `calls.log.received` with `call_id`, payload size, status.
2. `data/calls.json` gets a new record (atomic write).
3. `/v1/dashboard/*` reflects on next fetch.

If webhook fails to land: check `fly logs -a robot-api` for auth or parse errors.
If lands but dashboard doesn't update: verify `call_id` in `data/calls.json` (`fly ssh` + grep).

### Unresolved
- Exact payload nesting (verify by logging first real webhook).
- HR retry count + backoff (idempotency makes this a non-issue).
- Whether HR fires multiple events per call (`call.started`, `call.transferred`, `call.ended`) — we'd see extra logs if so.
