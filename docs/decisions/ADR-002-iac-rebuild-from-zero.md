# ADR-002 — IaC: rebuild the v4 workflow from zero on a clean HR org

- **Status**: Proposed (deferred to dedicated branch post-MVP)
- **Date**: 2026-04-25
- **Decided by**: Andres + Claude (after end-to-end Write Twin + Twin DDL + publish proven via REST in the same session)

## Context

We proved today that every component of v4 can be created from REST API calls — Twin DDL via `POST /twin/sql`, the Write Twin node via `POST /versions/{id}/nodes`, publish via `POST /versions/{id}/publish`. The MVP demo will ship as a manually-built workflow because reproducibility wasn't gated on demo day.

Post-MVP, we want one command — `make iac-rebuild ORG_KEY=$HAPPYROBOT_API_KEY` — to recreate the entire v4 workflow on any clean HR org. Reasons:

1. **Disaster recovery** — if Andres's HR org gets nuked, demo + ongoing dev recover in minutes instead of hours.
2. **Multi-environment parity** — promoting from dev → staging → prod orgs requires byte-exact replication, not "configure each one in the UI".
3. **Broker-doc narrative** — "this workflow is fully scripted; here's the GitHub Action that rebuilds it" is a stronger FDE story than "it took an afternoon to click through".
4. **Onboarding** — any future engineer pulls the repo, runs the bootstrap, and has a working dev workflow in 5 minutes.
5. **Customer deployments** — when a real broker buys this, deploying to their HR org is a script run, not consultancy hours.

We're not building this for MVP — we're locking the design now while the contracts are fresh, then implementing on a dedicated branch when MVP demo ships.

## Decision

Build `scripts/iac/` as a hybrid **manifest + snapshot** toolchain. YAML manifest captures human-readable intent (workflow name, variables, prompt file references); JSON snapshots capture exact Plate state for nodes that are tedious to express declaratively (real-time classifiers, complex tool configs). A Python orchestrator sequences the REST calls.

### Repository structure (after the IaC branch lands)

```
scripts/
├── iac/
│   ├── bootstrap.py              # main orchestrator — runs the 9-step sequence
│   ├── extract_snapshots.py      # one-time: dumps existing v4 nodes to JSON
│   ├── modules/
│   │   ├── twin.py               # CREATE TABLE + INSERT loads via /twin/sql
│   │   ├── workflow.py           # POST /workflows + variables
│   │   ├── nodes.py              # POST /versions/{id}/nodes (uses snapshot JSONs)
│   │   ├── publish.py            # POST /versions/{id}/publish
│   │   └── http.py               # curl-via-subprocess client (urllib gets 401d)
│   ├── manifest.yaml             # workflow name, vars, env → file-reference map
│   ├── snapshots/                # extracted Plate JSON, one per v4 node
│   │   ├── voice_agent.json
│   │   ├── prompt.json
│   │   ├── verify_carrier.json
│   │   ├── find_available_loads.json
│   │   ├── search_loads_by_lane.json
│   │   ├── negotiate_evaluate.json
│   │   ├── extract.json
│   │   ├── classify.json
│   │   ├── classify_sentiment.json
│   │   ├── case_health_score.json
│   │   ├── carrier_sales_auditor.json
│   │   └── write_twin.json
│   └── tests/
│       └── test_smoke.py         # synthetic happy-path call after bootstrap
├── add_write_twin_node.py        # already exists — keep, port logic into modules/nodes.py
└── build_logic_tree.py           # unrelated, stays
Makefile                          # `make iac-rebuild`, `make iac-extract`, `make iac-test`
```

### Manifest schema (`scripts/iac/manifest.yaml`)

```yaml
workflow:
  name: "Inbound Carrier Sales New"
  icon: "robot"
  data_retention_days: 90

variables:
  - {key: negotiation_floor_pct,    value_dev: "0.10",  value_staging: "0.10", value_prod: "0.10"}
  - {key: max_negotiation_rounds,   value_dev: "3",     value_staging: "3",    value_prod: "3"}
  - {key: agent_name,               value_dev: "Paul",  value_staging: "Paul", value_prod: "Paul"}
  - {key: company_name,             value_dev: "Acme Logistics", value_staging: "Acme Logistics", value_prod: "Acme Logistics"}
  - {key: API_BEARER_TOKEN_,        value_dev: "${env:API_BEARER_TOKEN}", hidden: true}

twin_tables:
  - schema_file: data/twin_schema_loads.sql
    seed_file: data/twin_seed_loads.sql
  - schema_file: data/twin_schema_calls_log.sql

nodes:
  # Order matters — parents before children. Each entry references a snapshot file
  # OR a constructor module + parameters.
  - {snapshot: voice_agent.json}
  - {snapshot: prompt.json, parent: voice_agent}
  - {snapshot: verify_carrier.json, parent: prompt}
  - {snapshot: find_available_loads.json, parent: prompt}
  - {snapshot: search_loads_by_lane.json, parent: prompt}
  - {snapshot: negotiate_evaluate.json, parent: prompt}
  - {snapshot: extract.json, parent: classify}     # post-call chain order
  - {snapshot: classify.json, parent: initiate_new_contact}
  - {snapshot: classify_sentiment.json, parent: carrier_sales_auditor}
  - {snapshot: case_health_score.json, parent: computations}
  - {snapshot: carrier_sales_auditor.json, parent: case_health_score}
  - {snapshot: write_twin.json, parent: classify_sentiment}

publish:
  environment: development
```

### Bootstrap sequence (orchestrator's 9 phases)

1. **Verify HR API key** — `GET /api/v2/api-keys/me`; abort if 401.
2. **Twin DDL** — for each `schema_file`, parse statements (split on `;`, strip comments), POST each to `/twin/sql`. Idempotent via `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`.
3. **Twin seed** — for each `seed_file`, batch INSERTs (multi-row `INSERT ... VALUES (...), (...)`) via `/twin/sql`. Skip if `SELECT count(*)` already > 0.
4. **Create workflow** — `POST /workflows` with name + icon + folder_id from manifest. Capture `workflow_id` + `version_id` from response.
5. **Create variables** — `POST /workflows/{id}/variables` × N. Substitute `${env:KEY}` references against the shell env.
6. **Add nodes** — for each entry in manifest's `nodes`, load snapshot JSON, rewrite `parent_node_id` from the lookup table built so far, POST via `/versions/{id}/nodes`. Snapshots are templated: `{{group_id_for("Extract")}}` placeholders get substituted with newly-created persistent_ids.
7. **Sanity check** — `GET /versions/{id}/nodes`, assert every node `is_complete: true`.
8. **Publish** — `POST /versions/{id}/publish` with `{"environment": <manifest>}`. Capture warning array; fail loudly if any node has `missing_variables`.
9. **Smoke test** — `POST /workflows/{id}/runs` with synthetic payload (empty for web-call trigger); poll run status until terminal; assert no error.

### Snapshot template format

Snapshots are nearly verbatim from `GET /versions/{id}/nodes/{id}` but with two transformations:

- **persistent_ids → semantic placeholders**: `{{node_ref:extract}}` resolves at runtime to the just-created Extract node's persistent_id. Allows snapshots to be portable across orgs.
- **Workflow var refs → semantic placeholders**: `{{var_ref:negotiation_floor_pct}}` resolves to the new var's id.

Example (excerpt from `write_twin.json`):

```json
{
  "type": "action",
  "event_id": "7021bfff-3e47-459c-b871-b0271ca04d9f",
  "name": "Write to Twin",
  "parent_node_id": "{{node_ref:classify_sentiment}}",
  "configuration": {
    "tableName": "calls_log",
    "columnValues": [
      {
        "columnName": "mc_number",
        "type": "text",
        "isPrimary": false,
        "value": [{"type": "paragraph", "children": [
          {"text": ""},
          {"type": "variable", "children": [{"text": ""}],
           "group_id": "{{node_ref:extract}}",
           "variable_id": "response.mc_number"},
          {"text": ""}
        ]}]
      }
    ]
  }
}
```

### Idempotency strategy

Each bootstrap step checks state before mutating:

| Step | Check before mutate |
|---|---|
| Twin DDL | `GET /twin/schema` — skip if table exists with matching column set |
| Twin seed | `SELECT count(*)` — skip if rows exist |
| Workflow create | `GET /workflows` filtered by name — skip + reuse if exists |
| Variable create | `GET /workflows/{id}/variables` — skip + reuse if key exists |
| Node create | `GET /versions/{id}/nodes` — skip if name + event_id matches existing |
| Publish | check `is_published=true` on latest version — skip if already published |

Re-running `make iac-rebuild` on a cleanly-deployed org is a no-op. Re-running after partial failure resumes from where it left off.

### Test fixture (`scripts/iac/tests/test_smoke.py`)

After bootstrap:

1. Generate a synthetic happy-path transcript (paste from `docs/test-scenarios.md HP-02`).
2. Trigger a run with that transcript as input.
3. Wait for run completion (poll `GET /runs/{id}` until status terminal).
4. Query `SELECT * FROM calls_log WHERE call_id = <run_id>` via `/twin/sql`.
5. Assert: `mc_number = "250819"`, `agreed_rate = 2400.0`, `call_outcome IS NOT NULL`, `case_health_score BETWEEN 0 AND 100`.

If any assertion fails, exit non-zero. CI catches regressions.

### CI integration (sketch)

```yaml
# .github/workflows/iac-deploy.yml
on:
  push:
    branches: [iac]
  workflow_dispatch:

jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install pyyaml
      - run: python scripts/iac/bootstrap.py
        env:
          HAPPYROBOT_API_KEY: ${{ secrets.HAPPYROBOT_API_KEY_DEV }}
          API_BEARER_TOKEN: ${{ secrets.API_BEARER_TOKEN_DEV }}
      - run: python -m pytest scripts/iac/tests/
```

For staging/prod, separate workflow files with respective env secrets + `manifest.yaml` overrides for `publish.environment`.

## Rationale

- **Hybrid over pure-snapshot:** snapshots alone are unreadable diffs (Plate JSON is verbose). Manifest YAML lets reviewers see "5 vars, 12 nodes, publish to dev" at a glance.
- **Hybrid over pure-DSL:** writing a constructor for every node type doubles the implementation surface. Snapshots cover the "exotic" nodes (real-time classifiers, complex Plate); DSL covers the "regular" ones.
- **YAML over TOML:** workflow manifests need nested arrays of objects; YAML is more readable than TOML for that shape.
- **Curl over urllib:** `urllib` gets 401'd by HR's auth gateway (header negotiation diff). Verified during today's Write Twin attempt. Curl works fine. Subprocess wrapper is ugly but stable.
- **Idempotent state checks per step** instead of "delete + recreate everything": delete-recreate would lose run history + audit context attached to the workflow. Idempotent reads are slightly more code; payoff is replay safety.
- **Per-environment manifest overrides** instead of one big monolithic manifest: `manifest.dev.yaml`, `manifest.staging.yaml`, `manifest.prod.yaml` keep secrets + retention + publishing target tidy without complex template logic.
- **Smoke test in CI gates the deploy:** if a manifest change breaks the workflow at runtime, CI catches it before the prod deploy. Without this, IaC would be "I shipped what I think works" — same risk as manual UI clicks.

## Implementation order (estimated effort)

| Phase | Effort | Deliverable |
|---|---|---|
| 1 — `extract_snapshots.py` against current v4 | 1-2 hr | `snapshots/*.json` × 12 captured + persistent_ids replaced with placeholders |
| 2 — `manifest.yaml` design + parser | 1 hr | manifest validates against a JSON schema |
| 3 — `bootstrap.py` orchestrator (steps 1-5) | 2-3 hr | empty workflow + Twin tables created end-to-end |
| 4 — `bootstrap.py` step 6 (add nodes) | 2-3 hr | snapshots applied with placeholder substitution; 19-node graph rebuilt |
| 5 — `bootstrap.py` step 7-8 (sanity + publish) | 1 hr | publish call + warning detection |
| 6 — `bootstrap.py` step 9 (smoke test) | 2-3 hr | synthetic test run + assertion |
| 7 — `Makefile` + README | 1 hr | usage doc + extract/rebuild/test targets |
| 8 — CI YAML | 1 hr | dev/staging/prod GitHub Actions wired |
| **Total** | **11-15 hr** | full IaC toolchain on a dedicated branch |

## Rejected alternatives

- **Use HR's MCP server** (`manage_workflow`, `manage_versions`, etc.) — fits Claude Code dev-time but isn't portable to CI / non-Claude environments. Raw REST is the language-agnostic primitive.
- **Pure declarative (Pulumi-style)** — would require building a HappyRobot Pulumi provider. Months of work. Overkill.
- **Pure imperative Python (no manifest)** — every config change requires a code change. Doesn't survive non-engineer edits.
- **HR Workflow Templates** — `from_template: voice-agent` covers the agent container but not the carrier-sales tools, post-call chain, or our domain logic. Useful as a starting point inside our bootstrap, not a replacement.
- **Skip snapshot extraction; build everything from manifest + constructors** — feasible, ~3× the constructor code. Acceptable if we wanted to fully own the abstraction, but defeats the "use HR-native primitives" story.

## References

- [iac-bundle.md](../references/happyrobot/iac-bundle.md) — current state of identifiers, file pointers, and what we've already built
- [api-reference.md](../references/happyrobot/api-reference.md) — HR Platform V2 API endpoints we use
- [scripts/add_write_twin_node.py](../../scripts/add_write_twin_node.py) — the working IaC artifact that proves the contract; will be ported into `scripts/iac/modules/nodes.py`
- HR docs: `https://docs.happyrobot.ai/api-reference/v2/workflows/create-a-workflow` — `from_template` + `version.nodes` body shapes
- Today's session: discovered `parent_node_id` (not `parent_id`), Plate Paragraph[] bookend rule, Write Twin columnValues schema, HR linear-chain semantics, `/runs` not `/runs/trigger`, `/available-vars` not `/available_variables`. All saved to `~/.claude/projects/.../memory/reference_hr_procedural_quirks.md`.

## Consequences

- **`scripts/iac/` becomes the source of truth** for workflow shape. The HR UI becomes a viewing/debugging tool, not the canonical config store. Manual UI edits in dev are fine but must be backported to manifest+snapshots before merging.
- **Branching strategy shifts**: workflow changes happen on feature branches, get reviewed via PR (manifest diff readable), then `iac` branch deploys to dev on merge. Promotion to staging/prod via `gh workflow run iac-deploy.yml -f env=staging`.
- **HR org becomes ephemeral**: any time the dev org gets messy, `make iac-rebuild` resets it. Encourages experimentation.
- **Onboarding time: 5 minutes** vs the current "follow the manual click-through guide" half-day.
- **Cost:** one-time 11-15 hr effort, then ongoing maintenance ~30 min per workflow change (re-extract snapshot of changed node, update manifest if structure changed). Cheap.
- **Failure mode:** if HR changes their API contract (e.g., renames `parent_node_id` back to `parent_id`), every IaC re-deploy breaks. Mitigation: pin the API version in manifest (`apiVersion: v2`), CI smoke test catches breakage immediately.
