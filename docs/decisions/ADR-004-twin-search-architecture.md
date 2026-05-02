# ADR-004 — Twin search architecture: `Contains` operator for MVP, FastAPI + local mirror deferred

- **Status**: Accepted
- **Date**: 2026-04-26
- **Decided by**: Andres + Claude (after live HR Twin REST probe demolished the obvious fixes)
- **Supersedes**: none
- **Superseded by**: none

## Context

A test call exposed a search defect: carrier asked for "loads from Texas", agent fired `search_loads_by_lane(origin_state="TX")`, Twin returned `{count:0, rows:[]}` despite 6 TX-origin rows. The `Fetch Loads` Twin Read child has 5 `Equals` filters on optional tool params. When the agent omits a param it resolves to `""`, which Twin evaluates as `column = ''` — matching zero rows.

"Drop the filters" is wrong: the agent must remain able to filter by ANY subset of the 5 params (origin_state, origin_city, destination_state, destination_city, equipment_type).

A live REST probe (2026-04-26) ruled out the obvious alternatives:

- **`POST /api/v2/twin/sql`**: Cloudflare WAF intermittently 403s bodies with quoted-literal SQL. HR does NOT bind `:placeholder`, `$1`, `?`, or any tested parameter syntax — user-data-driven WHERE clauses cannot be safely templated.
- **`GET /api/v2/twin/tables/{name}`**: silently ignores column-filter query params; 500-row cap; only `limit`/`offset` work.
- **Direct Postgres connection**: not exposed in HR Twin settings UI today.

Four options were enumerated:

1. **Webhook → our copied Twin DB** — HR voice agent calls our FastAPI; FastAPI queries a local mirror.
2. **`Equals` → `Contains` operator swap** — every string contains `""`, so omitted params become wildcards.
3. **Intermediate agent** — LLM or Python router between speech and Twin call.
4. **FastAPI + local mirror + dynamic SQL** — paginated Twin → local sync, parameterized binding, ranking + proximity extensibility.

## Decision

**MVP: adopt Option 2.** Change all 5 `Fetch Loads` Twin Read filter operators from `Equals` to `Contains`. 5-min UI fix, no infrastructure, no deploy. Filtering capability preserved across any subset of the 5 params.

**Post-MVP: adopt Option 4.** When triggers fire (load count >500, carrier complaints about wrong-load matches, or a feature Option 2 cannot support — proximity ranking, region expansion, full-text notes search), migrate search to a FastAPI route backed by a local Twin mirror. Sync direction is Twin → local (Twin remains source of truth). Mirror lands at `data/twin_mirror/loads.json` for MVP (read-only inspection); post-MVP the same file loads into SQLite or in-memory at FastAPI startup. Paginated read loop lives in `scripts/sync_twin_loads.py`.

Options 1 and 3 rejected: Option 1 requires our FastAPI deployed first — too much infrastructure for a 5-min fix. Option 3 adds an LLM hop or Python router for what is fundamentally a filter-operator change — wrong axis.

## Consequences

**Positive**
- 5-minute unblock; demo-ready immediately.
- No new infrastructure, no Fly deploy gating the fix.
- Filter capability preserved across any subset of the 5 params.
- Empty-string-as-wildcard verified empirically against the live HR Twin Read node.

**Negative**
- Substring false-positive risk is theoretical on the 25-row dataset (no colliding city names today; equipment_type is a 5-value enum constrained at the tool param description). Risk grows with dataset size and city diversity.
- Empty-string-`Contains`-everything is NOT documented HR semantics — verified empirically only. If HR changes operator semantics in a future release, the MVP fix breaks silently.

**Mitigation**
- Tool param descriptions enum-constrain equipment_type and state values at capture time (per `feedback_analytics_friendly_enums.md`).
- The 10 lane-search test scenarios in `project_test_scenarios_phase2.md` detect operator-semantic drift on every workflow change.
- Migration trigger documented (load count >500 OR carrier-reported wrong-match OR Option-2-blocking feature) prevents drift from becoming permanent debt.

**Migration path**
1. Deploy FastAPI to Fly.io with `GET /v1/loads/search` reading `data/twin_mirror/loads.json` (loaded into SQLite or in-memory at startup).
2. `scripts/sync_twin_loads.py` runs on cron or on-demand (paginated `GET /api/v2/twin/tables/loads` until `offset >= total`).
3. Swap `search_loads_by_lane`'s child node from Twin Read to a Webhook node hitting our FastAPI.
4. Twin remains source of truth; local mirror is read-only cache.

## Open questions / accepted risks

- **HR operator semantics drift**: mitigated by regression suite, not eliminated.
- **Substring collisions at scale**: city columns most exposed; reassess at >500 rows or first wrong-match.
- **Source-of-truth**: when `data/loads.json`, `data/twin_seed_loads.sql`, and Twin diverge, Twin wins. Local mirror is read-only cache.

## References

- [2026-04-26 handoff: Twin Search Architecture investigation](../handoffs/2026-04-26-twin-search-architecture.md) — full probe results (§4), 4-option matrix (§6), 5 clarifying questions (§7)
- [ADR-002 — IaC rebuild from zero](ADR-002-iac-rebuild-from-zero.md) — companion Tier-2 work; the migration step lands on the same `iac` branch
- [ADR-003 — Adopt HR Bridge API contract](ADR-003-adopt-bridge-api-contract.md) — Option 4's FastAPI surface aligns with the Bridge `GET /api/v1/loads` shape
- Memory: `reference_hr_twin_empty_string_filter.md` — the original constraint that kicked off this investigation
- `scripts/sync_twin_loads.py` — paginated Twin → local mirror sync loop (parallel sub-agent deliverable)
- `project_test_scenarios_phase2.md` — 10 lane-search regression scenarios that gate operator-semantic drift detection
