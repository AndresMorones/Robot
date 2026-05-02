# ADR-013: Operational vs Analytical Store Separation (no warehouse for MVP)

- **Status:** Accepted
- **Date:** 2026-04-30
- **Supersedes:** None
- **Superseded by:** None
- **Pairs with:** ADR-005 (Twin canonical post-call store), ADR-007 (dashboard caching), ADR-009 (freshness pipeline), ADR-012 (dashboard-side latency compute), `memory/project_twin_production_lock_in.md`

## 1. Context

Today's data path:

- Operational write — HR Voice Agent post-call extraction → AI Extract → Case Health Score → Write-to-Twin chip → `calls_log` + `bookings` rows.
- Operational read — FastAPI hits `/twin/sql` (Twin Postgres behind Cloudflare WAF) for transactional lookups (`GET /v1/calls/{id}`, idempotency on `(call_id, load_id)`, etc.).
- Analytical read — same Twin tables via `api/app/services/dashboard_aggregations.py`, raw rows pulled into the FastAPI process and aggregated in Python (WAF blocks `ORDER BY+LIMIT`, multi-aggregate SELECT, IN-lists, UNION, `information_schema`). Wrapped in `cachetools.TTLCache(ttl=30s)`.
- Per-call drilldown — HR REST API (`/runs`, `/runs/{id}/nodes`, `/runs/{id}/outputs/{output_id}`) called on demand for transcript, run nodes, raw extract outputs. `run_details.py` planned with `cachetools` 60s for nodes / 300s for outputs.

There is no separate analytical warehouse, no CDC stream, no read replica. `calls_log` and `bookings` serve both write-path idempotency and dashboard aggregation off the same rows.

The user asked verbatim: *"What is FAANG production level architecture creating database of this or querying directly from API?"* That question forced an explicit decision rather than continued drift, because:

- Twin is take-home grade (memory: `project_twin_production_lock_in.md`). SPOF on `HAPPYROBOT_API_KEY`. Cross-org coupling. WAF restrictions already shaped the aggregation refactor (2026-04-28). No platform SLA.
- Dashboard reads are growing: funnel, economics, operational, quality, observability, carriers — six tabs with overlapping aggregates over the same rows.
- Per-call drilldown is moving toward the HR REST API for transcript + run details (ADR-012 Phase 2).

The architectural question this ADR locks: do we keep operational and analytical reads on the same store, or stand up a warehouse?

## 2. Decision

**Keep the operational store (Twin `calls_log` + `bookings`) as the source of truth for transactional data; layer the analytical surface (FastAPI aggregation cache + HR REST API drilldown) on top WITHOUT a separate warehouse for MVP.** Spec clause `docs/FDE-TECHNICAL-CHALLENGE.md` line 52 (Docker) + line 76 (single-cloud deploy) constrains scope to one container fleet; line 48 (custom dashboard, no platform analytics) is satisfied by the Python-side aggregator. A second datastore would not move the deliverables forward.

The FAANG canonical pattern (Option B below) is acknowledged and staged behind explicit Tier-2/Tier-3 trigger conditions (Section 5). This is a deviation from canonical, not ignorance of it.

## 3. Options Considered

### Option A — Operational Twin + dashboard cache + HR REST API drilldown (chosen for MVP)

Single Twin Postgres (HR-managed) holds `calls_log` + `bookings`. FastAPI reads raw rows behind a 30s `cachetools` TTL and aggregates in Python. HR REST API serves per-call drilldown (transcript, run nodes, output blobs) behind 60s/300s TTLs.

- Pros — zero new infrastructure; satisfies spec ($0 incremental cost); single place to write; reuses ADR-007 cache seam; ADR-009 webhook invalidates one cache, not two; drilldown freshness is whatever HR exposes (~live).
- Cons — every analytical query competes with operational writes on the same rows; WAF restrictions shape what queries are even expressible; no historical retention beyond what HR offers; cross-call analytics over `transcript` is O(n) per query body since transcripts are large JSON blobs; vendor lock-in on HR Twin schema; dashboard latency under load is bounded by HR `/twin/sql` round-trip + WAF.

### Option B — Operational Twin → CDC stream → analytical warehouse (FAANG canonical, Tier-2/Tier-3)

Twin remains the operational store. A CDC pipeline (Debezium / HR-emitted events / nightly batch dump) replicates writes into BigQuery / Snowflake / ClickHouse. Dashboard reads warehouse; HR REST API stays as fallback for fresh per-call drilldown (warehouse lag absorbs everything else).

- Pros — analytical queries don't compete with operational writes; warehouse SQL surface is unrestricted (no WAF); columnar storage handles transcript-body scans cheaply; historical retention is independent of HR; clear separation lets each store be sized independently; multi-tenant scaling story is straightforward.
- Cons — incremental ~$500-2000/mo (warehouse + Debezium + dbt or equivalent); operational complexity (replication lag monitoring, schema drift, dbt CI); two query paths means two sets of caches and two staleness windows; freshness contract becomes a real SLA the dashboard has to surface; over-engineered for take-home volume.

### Option C — Live HR REST API for everything; no Twin write (rejected)

All reads (aggregates + drilldown) hit HR REST API directly. No `Write-to-Twin` chip. No `calls_log`. Dashboard composes per-call data on the fly.

- Pros — single source (HR); no operational store to maintain; no schema drift; freshness is automatic.
- Cons — HR REST API has no SLA; per-aggregation N+1 (`/runs` list → N × `/runs/{id}/nodes` → N × `/runs/{id}/outputs`); no historical retention guarantee from HR; cannot enforce idempotency on `(call_id, load_id)` without a local store; ADR-005 already locked Twin as canonical post-call store. Rejected on architectural and contractual grounds.

## 4. Tier-Maturity Ladder

| Tier | Architecture | Cost (incremental) | Trigger |
|---|---|---|---|
| Tier 1 (today) | Operational Twin + FastAPI aggregation cache + HR REST API drilldown. No warehouse. | $0 | Take-home phase + early customer pilot. |
| Tier 2 | Self-hosted Postgres replica via logical replication (or scheduled `pg_dump`) from HR Twin. Dashboard reads replica; HR REST API still drilldown. | ~$50-100/mo (Fly Postgres or RDS small) | HR Twin SLA gap measured at >0.5% downtime/month, OR Cloudflare WAF blocking critical analytical queries we cannot rewrite, OR data retention >90 days needed by customer contract. |
| Tier 3 | Full analytical warehouse (BigQuery / Snowflake / ClickHouse) + CDC pipeline (Debezium or equivalent) + dbt models. Dashboard reads warehouse; operational Postgres for writes; HR REST API drilldown. | ~$500-2000/mo (warehouse + CDC + dbt CI) | >100k calls/month sustained, OR multi-tenancy live (org_id on every row), OR analytics queries exceed 5s p95 on operational DB, OR regulatory retention/audit requirement (e.g. SOC 2, HIPAA-adjacent). |

Tier 2 is an escape from HR vendor lock-in; Tier 3 is a separation-of-concerns step driven by load, not just lock-in.

## 5. Data Routing Matrix

| Query type | Store today (Tier 1) |
|---|---|
| Funnel aggregates (calls, bookings, conversion %) | Twin `calls_log` + `bookings` via `dashboard_aggregations.py`, 30s TTL |
| Per-call drilldown (full row + extract response) | Twin `calls_log` row by `call_id` |
| Transcript fetch | HR REST API `/runs/{id}/outputs/{transcript_output_id}`, 300s TTL (planned `run_details.py`) |
| Per-tool latency (FMCSA, query_loads round-trip) | HR REST API `/runs/{id}/nodes`, 60s TTL — or transcript-side compute (ADR-012 Phase 1/2) |
| Real-time RPM/TPM (rolling-window throughput) | Twin `calls_log` count + transcript token sums, 30s TTL |
| Historical trend charts (last 7d / 30d) | Twin `calls_log` aggregated dashboard-side, 30s TTL |
| Alert thresholds (e.g. CHS p10 drop) | Twin `calls_log` aggregated dashboard-side, 30s TTL |
| Post-call write idempotency (`UNIQUE (call_id, load_id)`) | Twin `bookings` (constraint enforced server-side in HR Postgres) |
| Carrier rollup (calls + bookings grouped by `mc_number`) | Twin `calls_log` + `bookings` via `dashboard_aggregations.py`, 30s TTL |
| Observability dashboard (telemetry tab — RPM/TPM/latency) | Twin `calls_log` (transcript + duration) + HR REST API for per-node timestamps |
| Dead-air / time-to-first-utterance | Blocked — requires per-turn timestamps not exposed in transcript or REST API today (ADR-012 §4) |
| Dashboard auth / Bearer surface | FastAPI `app/deps.py::require_bearer`; Twin access is server-side only; HR REST API key never leaves the server |

## 6. Implementation Status

Live today:

- `api/app/services/dashboard_aggregations.py` — Twin aggregation in Python, `cachetools.TTLCache(ttl=30s, maxsize=128)`.
- `api/app/services/twin_client.py` — `/twin/sql` client, single-statement guard, WAF-aware error parsing.
- `api/app/services/calls_store.py`, `api/app/services/bookings_store.py` — operational write + read paths.
- `api/app/services/event_bus.py`, `api/app/routers/events.py` — webhook-driven cache invalidation (ADR-009).
- `api/app/routers/dashboard.py` — six aggregation endpoints reading via the cached aggregator.

Planned (in-flight):

- `api/app/services/run_details.py` — HR REST API client for `/runs/{id}/nodes` (60s TTL) and `/runs/{id}/outputs/{output_id}` (300s TTL); used by per-call drilldown + ADR-012 Phase 2 latency compute.

Deferred (not built):

- Logical replication or `pg_dump` ETL out of HR Twin (Tier 2).
- CDC pipeline (Debezium, Kafka, or equivalent) (Tier 3).
- Warehouse (BigQuery / Snowflake / ClickHouse) + dbt models (Tier 3).
- Multi-region read replicas (Tier 3, paired with Fly multi-region rollout).

## 7. Consequences

### Positive

- Spec-compliant with $0 incremental cost. Single deployable surface (FastAPI + Next.js + HR Twin + HR REST API).
- One write path (`Write-to-Twin` chip), one cache invalidation seam (`invalidate_dashboard_cache()`), one schema to evolve.
- Keeps the FAANG canonical pattern (Option B) staged with explicit triggers — not closed off, just staged.
- Drilldown freshness is whatever HR exposes; we don't re-implement transcript storage.
- Cache layers (ADR-007 + ADR-009) absorb the analytical-on-operational pressure within current load envelope.

### Negative — debt items added by Option A that Tier-2 escapes

- Dashboard latency under load: at >100 concurrent reviewer sessions, every analytical query competes with operational writes on the same Twin rows; observed p95 will degrade.
- SPOF on HR Twin uptime: every dashboard tab and every post-call write fails together if Twin is down.
- Cloudflare WAF restrictions: aggregation queries that use `ORDER BY+LIMIT`, multi-aggregate SELECT, IN-lists, UNION, or `information_schema` must be expressed in Python over raw rows, which costs memory and CPU on the FastAPI process.
- Cross-call analytics over large `transcript` JSON bodies is O(n) per query — fine at 50 calls/day, ugly at 50k.
- Vendor lock-in on HR Twin schema; any HR-side schema change ripples into FastAPI parsing.
- No historical retention guarantee independent of HR; data egress on shutdown becomes the customer's risk.
- Cross-org coupling: `HAPPYROBOT_API_KEY` is a single credential controlling both write path (Twin) and read path (REST API).

## 8. Trigger to Revisit

Move to Tier 2 when any of:

- Sustained call volume exceeds ~5k/month (above current pilot envelope).
- Dashboard p95 latency exceeds 2s on any tab (current budget; tracked in observability).
- Customer-facing SLA on dashboard freshness (e.g. "dashboard is live within 60s of call end") becomes a contract obligation we'd default on if HR Twin had a multi-hour outage.
- Data retention requirement >90 days from customer contract or regulatory regime.
- Cloudflare WAF blocks an analytical query we cannot rewrite in Python within the FastAPI memory budget.

Move to Tier 3 when any of:

- Sustained call volume exceeds ~100k/month.
- Multi-tenancy launches (org_id on every row, per-tenant dashboards, isolation requirement).
- Analytics queries exceed 5s p95 on the Tier-2 operational replica.
- Regulatory retention/audit requirement (SOC 2 Type II, HIPAA-adjacent, freight broker compliance regime) demands immutable audit log + point-in-time recovery beyond Postgres-native.

## 9. Reference

- ADR-005 — Twin as canonical post-call store (the substrate this ADR layers on).
- ADR-007 — two-layer caching strategy.
- ADR-009 — webhook + SSE hybrid freshness pipeline (the cache-invalidation contract this ADR depends on).
- ADR-012 — dashboard-side latency compute (the HR REST API drilldown path this ADR codifies).
- Memory: `project_twin_production_lock_in.md` — Twin take-home-grade limits + Tier-2 escape route.
- Memory: `reference_cloudflare_waf_twin.md` — WAF restrictions that shaped `dashboard_aggregations.py` refactor (2026-04-28).
- Code: `api/app/services/dashboard_aggregations.py`, `api/app/services/twin_client.py`, `api/app/services/calls_store.py`, `api/app/services/bookings_store.py`, `api/app/services/event_bus.py`.
- Spec: `docs/FDE-TECHNICAL-CHALLENGE.md` lines 48, 52, 76.
