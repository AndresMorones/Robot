# Inbound Carrier v4 — IaC bundle

Single source of truth for everything needed to reproduce the v4 deployment from a clean HR org. Files in this list, plus the API reference and platform credentials, are sufficient to rebuild from scratch.

Last verified live: 2026-04-25.

## Identifiers (org-scoped — change per environment)

| Asset | ID | Notes |
|---|---|---|
| Workflow | `019db77a-0548-741c-9ac8-d713bea1a51f` | "Inbound Carrier Sales New" |
| Workflow slug | `xsfvbpjpsoy4` | URL-safe |
| Latest version (v4) | `019dc0f8-cd64-755b-9b4d-52961ffe15e0` | Forked from Version 3 |
| Version slug (v4) | `eu3pn7eqb7kk` | |
| Twin integration | `82409919-9100-4b06-8a52-dfb6eb79fbcb` | events: Read from Twin, Write to Twin |
| Read from Twin event | `ebd81a7b-ace2-4225-9410-b657ce8ea412` | used in `find_available_loads`, `search_loads_by_lane` children |
| Write to Twin event | `7021bfff-3e47-459c-b871-b0271ca04d9f` | used in calls_log Write Twin node |
| Webhook integration | `01926a93-064a-7a00-81b2-8ab78d5907e0` | events: GET, POST, PUT, PATCH, Polling, Predefined request |
| Predefined Webhook event | `b329e750-2e0e-4618-ba65-e04bb6a93c5f` | use ~90% of the time when payload schema is known |

## v4 node IDs (for inspection / programmatic edit)

| Node name | Node ID | Purpose |
|---|---|---|
| Incoming Customer Details | `019dc0f8-cd78-7de9-b40d-4fdfe625352a` | Web call trigger |
| Analyze Incoming Conversation | `019dc0f8-cd77-714c-a06e-545cdaa8c144` | Voice Agent container |
| Prompt | `019dc0f8-cd81-7758-8e9a-ea0e80723642` | Agent system prompt + tools |
| verify_carrier (tool) | `019dc0f8-cd86-723e-8bb8-0d1322107c7b` | FMCSA lookup |
| GET MC Number (verify_carrier child) | `019dc0f8-cd6f-7d6d-87f4-50a0b247030e` | Webhook → FMCSA demo endpoint |
| find_available_loads (tool) | `019dc0f8-cd89-762f-96a6-468cb0479610` | Single load by `reference_number` |
| Get load (find_available_loads child) | `019dc598-424d-7ac7-88c4-8fb53288c376` | Read from Twin |
| search_loads_by_lane (tool) | `019dc0f8-cd85-786b-bf23-d8e91308cd14` | Lane search |
| Fetch Loads (search_loads_by_lane child) | `019dc58d-4c4e-73c1-b136-293bd448006e` | Read from Twin |
| negotiate_evaluate (tool) | `019dc159-ee63-7d0e-aeeb-3c8799f2d2cf` | Python sidecar |
| Calculate Carrier Cost (negotiate child) | `019dc167-68b5-71f9-b6b0-f2c364827cdf` | Run Python |
| Initiate New Contact | `019dc69f-e1c5-7183-a6ad-af52e4af8003` | Post-voice handoff |
| Extract | `019dc0f8-cd75-705b-8864-81c602386b3e` | AI Extract — 14 live response fields (canonical target: 16) |
| Computations | `019dc0f8-cd7d-74b2-9f2b-b246978d3633` | (post-call computation) |
| Case Health Score | `019dc0f8-cd7b-7012-9e9e-67c258763160` | 5 response fields incl health_score_reasoning |
| Carrier Sales Auditor | `019dc0f8-cd7f-79d6-ad5a-a71a7e61111a` | 2 outputs: final_offer_position, posted_price_increase |
| Classify | `019dc0f8-cd79-74f5-b65e-076016934c63` | post-call call_outcome classifier |
| Classify Sentiment | `019dc0f8-cd7b-70af-bf3f-c6feff910179` | post-call sentiment classifier |
| Write to Twin | `019dc6e1-b5a4-7c2d-a992-8562aeab34cc` | Created via API 2026-04-25 by [scripts/add_write_twin_node.py](../../scripts/add_write_twin_node.py); 20 columns bound, leaf child of Classify Sentiment, is_complete: true |

## Workflow variables (4 active + 1 secret)

Stored in HR's workflow variables panel; values per environment via `PATCH /workflows/{id}/variables/{var_id}`:

| Key | Type | Default (dev) | Notes |
|---|---|---|---|
| `negotiation_floor_pct` | float | 0.10 | tunable policy — 10% off loadboard |
| `max_negotiation_rounds` | int | 3 | hard ceiling |
| `agent_name` | string | "Paul" | persona surface |
| `company_name` | string | "Acme Logistics" | persona surface |
| `API_BEARER_TOKEN_` | string (secret) | (see secrets.local.md) | currently used by deprecated POST Call Data webhook; will become unused after Write Twin replaces it |

## Repo files (canonical IaC artifacts)

| File | Purpose |
|---|---|
| [data/twin_schema_calls_log.sql](../../data/twin_schema_calls_log.sql) | calls_log table DDL — 23 cols + 3 indexes |
| [data/twin_schema_loads.sql](../../data/twin_schema_loads.sql) | loads table DDL — 15 cols + 2 indexes |
| [data/twin_seed_loads.sql](../../data/twin_seed_loads.sql) | 25-row loads seed |
| [data/loads.csv](../../data/loads.csv) | CSV mirror of seed (portability story for broker-doc) |
| [prompts/voice-agent-system-prompt.md](../../prompts/voice-agent-system-prompt.md) | Agent system prompt — pasted into v4 Prompt node |
| [prompts/ai-extract-schema.md](../../prompts/ai-extract-schema.md) | Canonical Extract JSON Schema (16 fields target; 14 live MVP) |
| [prompts/classify-outcome-realtime.md](../../prompts/classify-outcome-realtime.md) | Real-time Call Outcome classifier |
| [prompts/classify-sentiment-realtime.md](../../prompts/classify-sentiment-realtime.md) | Real-time Sentiment classifier |
| [docs/references/happyrobot/api-reference.md](api-reference.md) | HR Platform V2 API endpoints we use |

## Reproducing on a clean HR org

Order of operations to rebuild from scratch:

1. **Get an API key** — HR Profile → Developer Settings → generate; export as `HAPPYROBOT_API_KEY` env var.
2. **Create Twin tables** — run each statement from `twin_schema_loads.sql` and `twin_schema_calls_log.sql` via `POST /twin/sql` (one statement per call).
3. **Seed loads** — run each `INSERT` line from `twin_seed_loads.sql` via `POST /twin/sql` (or batch via `INSERT ... VALUES (...), (...), ...` in single statement).
4. **Create workflow** — `POST /workflows` with name "Inbound Carrier Sales New".
5. **Create workflow variables** — `POST /workflows/{id}/variables` × 5 (the table above; secret one carries the bearer token).
6. **Add nodes** — `POST /versions/{id}/nodes` for each node in the v4 graph. Use:
   - Voice Agent container with the system prompt from `prompts/voice-agent-system-prompt.md`
   - 4 tool children (verify_carrier, find_available_loads, search_loads_by_lane, negotiate_evaluate) with their respective webhook/Run-Python/Read-from-Twin children
   - Post-call: AI Extract (paste schema from `prompts/ai-extract-schema.md`), Classify (post-call), Classify Sentiment, Case Health Score, Carrier Sales Auditor, then Write Twin → `calls_log`
7. **Publish** — `POST /versions/{id}/publish` with `{"environment": "development"}`.
8. **Smoke test** — `POST /workflows/{id}/runs` with `{"environment": "development", "payload": {}}`.

## Open IaC gaps (resolve as we hit them)

- ~~Write Twin `columnValues` shape~~ → **RESOLVED 2026-04-25.** Each item: `{columnName: str, type: <twin column type>, isPrimary: bool, value: Plate Paragraph[]}`. POST body must be `{"nodes": [<node>]}` with `parent_node_id` (NOT `parent_id`). Working IaC at [scripts/add_write_twin_node.py](../../scripts/add_write_twin_node.py).
- Bulk row insert — no `/twin/tables/{name}/rows/bulk` endpoint; use multi-row `INSERT ... VALUES (...), (...)` through `/twin/sql` for >10 rows.
- Workflow-level webhooks — `/workflows/{id}/webhooks` 404; appears to not be a separate REST resource.

## Future branch work — full IaC implementation (post-MVP requirement)

**Status:** deferred to a dedicated branch. Today (2026-04-25) we proved end-to-end that v4 can be reproduced from API calls.

**Full design + implementation plan:** [ADR-002](../../decisions/ADR-002-iac-rebuild-from-zero.md) — covers repo structure, manifest schema, bootstrap sequence, snapshot template format, idempotency strategy, smoke test fixture, CI integration, estimated effort (11-15 hr total), and rejected alternatives.

**TL;DR:** `scripts/iac/` will hold a hybrid manifest+snapshot toolchain. `manifest.yaml` declares the workflow + variables + node order; `snapshots/*.json` capture exact Plate state for each of v4's 19 nodes (extracted via a one-time `extract_snapshots.py`); `bootstrap.py` orchestrates the 9-step sequence (Twin DDL → seed → create workflow → create variables → add nodes → sanity → publish → smoke test). Idempotent — re-runs are no-ops. Single command: `make iac-rebuild ORG_KEY=$HAPPYROBOT_API_KEY`.

**Why defer:** the MVP demo doesn't need IaC to ship. Productionizing requires ~12 hrs of mechanical snapshot-extraction + orchestrator work with marginal demo value. The proven `scripts/add_write_twin_node.py` is enough evidence for the broker-doc IaC narrative ("here's the contract we discovered, here's a working script, here's the design for the full rebuild").

## Migration triggers (broker-doc Tier-2)

- **>1K calls/day per broker:** add more indexes on calls_log (e.g., `(mc_number, created_at DESC)` for carrier history queries)
- **>10K calls/day:** dual-write Write Twin + a Kafka producer for analytics
- **>100K calls/day:** archive cold data >90d to S3, Twin holds rolling window only
