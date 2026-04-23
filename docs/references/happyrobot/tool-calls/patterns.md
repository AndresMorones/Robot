# Tool-Call Configuration Patterns

Click-precise patterns for configuring tool-call nodes in the HR UI. Flag: field-label wording is inferred; confirm in your workspace.

## Common configuration for all our tool calls

### URL
Your deployed API endpoint. Use the production Fly URL:
- `https://robot-api.fly.dev/v1/fmcsa/verify`
- `https://robot-api.fly.dev/v1/loads/search`
- `https://robot-api.fly.dev/v1/negotiate/evaluate`

During local development, tunnel via ngrok (`ngrok http 8000`) and use the `https://<random>.ngrok-free.app/v1/...` URL. Update the tool-call nodes to point back to Fly before publishing.

### Method
POST for all our endpoints.

### Headers — auth

**Preferred (Bearer header)**:
```
Authorization: Bearer {workflow_secret:API_BEARER_TOKEN}
Content-Type: application/json
```

The `{workflow_secret:...}` syntax references a secret you store in HR's workflow-level secret manager. Set this secret **once** in the HR UI (Workflow settings → Secrets → Add); then every tool-call node can reference it without hard-coding the value.

**Fallback (query-string token)**: if your HR tier blocks custom `Authorization` headers on tool-call nodes, append the token to the URL:
```
https://robot-api.fly.dev/v1/fmcsa/verify?token={workflow_secret:API_BEARER_TOKEN}
Content-Type: application/json
```

Our `app/deps.py::require_bearer` in FastAPI accepts both modes. The query-string path emits a `auth.query_string_used` structured-log warning so we can quantify how often the fallback fires.

**Never** hard-code the token value directly into a header or URL — always reference via `{workflow_secret:...}`.

### Timeout
Default is often 10s. **Set to 2500 ms (2.5 s)** on every tool-call node. The voice agent gets uncomfortable beyond 3s of silence; 2.5s leaves margin for TTS to start the filler/next utterance.

### Retries
Set to **1 retry** on 5xx or timeout. For 4xx errors, do not retry (they're likely bad inputs — retrying won't help).

If double-fail (primary + 1 retry both fail): the tool-call node returns a failure state. Downstream condition should route to the soft-apology + callback branch. The voice agent reads a pre-canned: "Our system's a little slow right now — let me take a callback."

### Variable mapping — request body

Tool-call nodes template-substitute upstream variables into the request body. Exact syntax depends on HR's version — typical candidates: `{var_name}`, `{{var_name}}`, `${var_name}`. **Confirm in the HR UI on first test.**

Example body for `fmcsa_verify`:
```json
{
  "identifier": "{{mc_number}}",
  "identifier_type": "MC"
}
```

Example body for `loads_search`:
```json
{
  "origin_state": "{{origin_state}}",
  "destination_state": "{{destination_state}}",
  "equipment_type": "{{equipment_type}}",
  "pickup_after": "{{earliest_pickup}}",
  "max_results": 3
}
```

Example body for `negotiate_evaluate`:
```json
{
  "load_id": "{{pitched_load_id}}",
  "round_number": "{{round_number}}",
  "carrier_offer": "{{carrier_offer}}",
  "prior_broker_offers": "{{prior_broker_offers}}"
}
```

### Response parsing

HR auto-parses a JSON response body. Every top-level key becomes a variable available to downstream nodes.

For `fmcsa_verify`, downstream nodes can reference: `{eligible}`, `{reason_codes}`, `{carrier_name}`, `{manual_review_required}`, etc.

For `negotiate_evaluate`, downstream nodes reference `{action}`, `{broker_counter}`, `{rationale}`, `{should_transfer}`.

**Testing the node (required before publish)**: use the Test tab with a realistic sample payload. This is what tells HR the response schema so downstream conditions / agents can typecheck the variable references.

### Error handling

A non-2xx response is treated as a failure. The tool-call node surfaces an `error` variable + the HTTP status. Downstream condition can branch on `{error}` to route to the soft-apology path.

**Our API's design contract**: `/v1/fmcsa/verify` does NOT return 5xx when FMCSA is down — instead it returns 200 with `manual_review_required: true`. This way the tool-call node doesn't fail; the workflow's condition node handles the fallback gracefully. Same pattern on `/v1/loads/search` (returns 200 with `matches: []`).

The only endpoints that can actually 5xx are `/v1/negotiate/evaluate` (bug in our code) and `/v1/calls/log` (storage failure). We handle those via the retry + soft-apology pattern.

## Idempotency

Our API is idempotent where it needs to be:
- `fmcsa_verify` — cached 24h by identifier, so repeated calls are cheap + consistent
- `loads_search` — pure read, no side effects
- `negotiate_evaluate` — pure function, stateless
- `calls_log` — upsert by `call_id`; replay returns `created: false`

This means HR's retry-on-5xx policy is safe. The `calls_log` idempotency matters most — HR may retry the `call.ended` webhook if our API 5xx's, and we must not create duplicate records.

## Latency budget reminder

| Endpoint | Target p50 | Hard max |
|---|---|---|
| `fmcsa/verify` (cache hit) | <50 ms | 500 ms |
| `fmcsa/verify` (cache miss → QCMobile) | 300 ms | 2000 ms |
| `loads/search` | <50 ms | 500 ms |
| `negotiate/evaluate` | <10 ms | 100 ms |
| `calls/log` | <50 ms | 1000 ms |

If any hot endpoint approaches hard max, the agent's conversational flow stalls audibly. We instrument `fmcsa_latency_ms` and alert on p95 > 1500 ms (see `docs/observability.md` when it exists).

## Unresolved / needs confirmation

- **Variable-substitution syntax** — `{var}` vs `{{var}}` vs other. Test on first node and document.
- **Whether HR supports conditional body fields** (e.g., omit a field if variable is null) or requires all fields present.
- **Exact secret-reference syntax** — `{workflow_secret:NAME}` is a guess based on platform conventions; confirm.
- **Retry backoff defaults** — HR may have configurable backoff; we use "1 retry" as a floor.
