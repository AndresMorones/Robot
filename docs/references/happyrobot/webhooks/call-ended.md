# `call.ended` Webhook

The only path HappyRobot uses to write persistent data back to our API after a call completes. Configured at the **workflow level** (not as a node in the graph).

## When it fires

After the call terminates (natural end, transfer, timeout, or hangup) AND after the post-call extraction LLM pass has run. HR waits for extraction to complete before firing the webhook so the payload carries the extracted structured data, not just raw metadata.

## Configuration in HR

- **URL**: `https://robot-api.fly.dev/v1/calls/log`
- **Method**: POST
- **Headers**: `Authorization: Bearer {workflow_secret:API_BEARER_TOKEN}` + `Content-Type: application/json`
  - Fallback if custom headers blocked: `?token={workflow_secret:...}` in URL
- **Retries**: enable platform retries (HR retries on 5xx/timeout — our endpoint is idempotent, safe)
- **Timeout**: HR-side default is fine; our `/v1/calls/log` target is p95 < 500 ms

## Payload shape (what HR sends us)

Expected to be approximately (exact field names TBD — verify on first real call):

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
  "extracted": { /* our CallLogRequest JSON from post-call extraction */ }
}
```

Our `/v1/calls/log` endpoint accepts a `CallLogRequest` — our extraction prompt should output that shape nested under `extracted` (or at the top level, depending on how HR merges the extracted JSON with the metadata). Our endpoint should be flexible enough to parse both shapes: either the extraction JSON is the whole body, or it's nested under `extracted` / `data`.

**Design decision**: our handler tries `.extracted` first, then falls back to the root. Either way it reconstructs a `CallLogRequest`.

## Authentication

Single Bearer token (same as tool-call nodes). No HMAC signing in HR's public webhook docs.

**Implication**: we can't cryptographically verify the request came from HR. Mitigations:
- Scope the Bearer token to "HR + dashboard + reproduce scripts only."
- If we ever publish the URL / token gets leaked, rotate immediately.
- Our `/v1/calls/log` endpoint enforces idempotency by `call_id` — duplicate calls from an attacker replaying won't corrupt state, just no-op.

## Idempotency

**Critical**: HR retries on 5xx / timeout. If our API 5xx's once and then recovers, HR may POST the same `call.ended` twice. Our `/v1/calls/log`:
- Keys the record by `call_id`.
- First call: creates, returns `{call_id, created: true, stored_at}`.
- Replay (same `call_id`): no-op (record exists), returns `{call_id, created: false, stored_at}`.

We do **not** merge partial updates. If for some reason HR sends a different payload for the same `call_id` (shouldn't happen, but), we keep the first record and log a warning.

## Debugging

When a webhook fires:
1. Our API log emits a `calls.log.received` event with `call_id`, extracted-payload size, status.
2. `call_outcome_total{outcome=...}` Prometheus counter increments.
3. `data/calls.json` gets a new record appended (atomic write).
4. Dashboard query endpoints (`/v1/dashboard/*`) reflect the new record on next fetch (no manual invalidation — they just query fresh).

If a webhook fails to land: check `fly logs -a robot-api` for auth or parse errors, and `fly logs -a robot-dashboard` is irrelevant (dashboard is read-only).

If a webhook lands but dashboard doesn't update: verify `call_id` exists in `data/calls.json` (`fly ssh` + `cat /data/calls.json | grep call_id`) — then the dashboard fetch is stale or cached wrong.

## Unresolved / needs confirmation

- **Exact payload shape** — whether extracted fields are nested under `extracted`, merged at root, or named differently. Verify by logging the first real webhook payload.
- **Retry count + backoff** — HR's public docs don't specify. Our idempotency makes this a non-issue either way.
- **Whether HR fires multiple webhook events per call** (e.g., `call.started`, `call.transferred`, `call.ended`) — we currently only configure the endpoint; we'd learn about other events if they fire (extra log entries).
