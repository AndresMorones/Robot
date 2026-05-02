# HappyRobot Platform V2 API — project-scoped reference

Base URL: `https://platform.happyrobot.ai/api/v2`
Auth: `Authorization: Bearer <HAPPYROBOT_API_KEY>` (org-level, currently in `secrets.local.md`)

This is a project-scoped subset — not a full vendor docs mirror. Lists only endpoints we use (or plan to use) for this take-home + IaC roadmap. Full reference is at `docs.happyrobot.ai`.

## Twin (managed Postgres per HR org)

| Method | Path | Used in |
|---|---|---|
| GET | `/twin/schema` | IaC verification: does `calls_log` exist with expected schema? |
| POST | `/twin/tables` | Create a Twin table (alternative to SQL editor for IaC) |
| GET | `/twin/tables/{tableName}` | Read rows. Used in seed-loads spike + dashboard aggregations |
| DELETE | `/twin/tables/{tableName}` | Drop table (cleanup) |
| POST | `/twin/tables/{tableName}/rows` | Insert row. Body: `{"values": {<col>: <stringified>}}`. Used to seed loads CSV. Numeric values must be STRINGS. |
| DELETE | `/twin/tables/{tableName}/rows` | Delete rows by filter |
| PATCH | `/twin/tables/{tableName}/rows` | Update row |
| POST | `/twin/sql` | Execute arbitrary SQL — for ALTER, complex migrations the table-row API doesn't cover |

## Workflow Variables (IaC for tunable policy)

| Method | Path | Used in |
|---|---|---|
| GET | `/workflows/{workflow_id}/variables` | List policy vars (negotiation_floor_pct, max_negotiation_rounds, agent_name, company_name) |
| POST | `/workflows/{workflow_id}/variables` | Create new policy var when adding a knob |
| PATCH | `/workflows/{workflow_id}/variables/{var_id}` | Update value across env (development/staging/production) |
| DELETE | `/workflows/{workflow_id}/variables/{var_id}` | Remove deprecated vars |

`workflow_id` accepts UUID OR slug (`inbound-carrier-v4`).

## Workflow runs (CI smoke tests)

| Method | Path | Used in |
|---|---|---|
| POST | `/workflows/{workflow_id}/runs` | Trigger a workflow run with payload `{"payload": {}, "environment": "development"\|"staging"\|"production"}` — for CI smoke after every prompt change. NOT `/runs/trigger`. |
| GET | `/workflows/{workflow_id}/runs` | List runs. |
| POST | `/runs/{run_id}/cancel` | Cancel an active run. |

## Versions (fork + publish automation)

| Method | Path | Used in |
|---|---|---|
| POST | `/versions/{version_id}/fork` | Fork v4 → v5 from CI when prompt changes |
| POST | `/versions/{version_id}/publish` | Promote forked version to development |
| POST | `/versions/{version_id}/lock` | Mark published version immutable |
| PUT | `/versions/{version_id}/nodes/{node_id}` | Replace a node's config (e.g., paste new prompt) |
| GET | `/versions/{version_id}/nodes` | Snapshot the workflow shape for diff |
| POST | `/versions/{version_id}/nodes` | Add nodes (for prompt-as-code IaC) |

## Quality gates (post-MVP CI)

| Method | Path | Used in |
|---|---|---|
| POST | `/prompt_nodes/{id}/custom_evals` | Register prompt regression test |
| POST | `/custom_evals/{id}/run` | Run eval, gate prompt deploys on green |
| POST | `/prompt_nodes/{id}/northstars` | Register quality criteria attached to Prompt |
| POST | `/prompt_nodes/{id}/adversarial_suites` | Register jailbreak test bank |
| POST | `/adversarial_suites/{id}/run` | Run all jailbreak tests; CI gate |

## Out of scope (for context, never call)

- Phone Numbers / SIP Trunks — web-call only in MVP
- Knowledge Bases — not used
- Sessions / Messages / Chat — auto-managed during runtime
- Bridge API — outbound HR→our-API; we receive these calls, don't make them

## Quirks (verified live, 2026-04-25)

- Numeric values in POST bodies must be **strings** for `/twin/tables/.../rows`; HR coerces to typed columns server-side.
- Bearer auth on every endpoint; one org-level key per environment.
- Windows curl needs `--ssl-no-revoke` for Schannel SSL stack — not relevant for Python (httpx uses OpenSSL).
- `manage_workflow` MCP tool wraps many of these endpoints for dev-time usage; for IaC prefer raw REST (portable, language-agnostic, doesn't require MCP runtime).

## Roadmap usage (post-MVP)

| Goal | Endpoints |
|---|---|
| Promote v4 → v5 on prompt change | versions fork → versions publish |
| Sync workflow vars from `data/policy.json` | GET/PATCH workflow variables |
| CI gate prompt regressions | custom_evals run |
| CI gate jailbreak regressions | adversarial_suites run |
| Backup workflow schema for disaster recovery | versions get + nodes list |
| Migrate Twin schema (e.g., add column) | `POST /twin/sql` with ALTER TABLE |
