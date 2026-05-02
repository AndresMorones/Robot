# ADR-012: Dashboard-side latency compute (HR p70/p90/intermediate_response_count NULL is expected)

- **Status:** Accepted
- **Date:** 2026-04-30
- **Supersedes:** None
- **Superseded by:** None
- **Pairs with:** ADR-007 (caching), ADR-009 (freshness pipeline), [docs/design/transcript-telemetry-module.md](../design/transcript-telemetry-module.md)

## 1. Context

The Twin `calls_log` v2 schema reserves three operational-telemetry columns:

```
intermediate_response_count INTEGER
p70_latency_ms              INTEGER
p90_latency_ms              INTEGER
```

These were intended to be populated post-call by HR's Voice Agent platform via @ picker bindings on the Log Event Write-to-Twin chip. Architectural review F8 (2026-04-28) flagged that the original bindings wrote BOOLEAN `*_intermediate_fired` flags into INT columns; Phase C C4 fixed the Twin schema (drop bool cols, add int4 cols).

After the fix, a live test call on 2026-04-30 (id=45) produced these columns as NULL even though `case_health_score`, `sentiment`, and `call_id` populated correctly. The user designated the NULL as **a known HR-platform bug we won't chase** ("This as null is expected ignore"). The columns will continue to be NULL on every call indefinitely.

## 2. Decision

**Compute robust latency dashboard-side from `transcript` + HR run details API** (when available). Treat the HR `intermediate_response_count` / `p70_latency_ms` / `p90_latency_ms` columns as cosmetic placeholders kept defensively. Treat `node_timings_json` (added 2026-04-30) as an escape-hatch infrastructure column kept empty at MVP — populated later only if the HR Run Python timing-capture path becomes necessary.

**Updated 2026-04-30 night** per user direction: *"Do phase 2 out of the gate. Full final dashboard is on the way."* → followed by *"No but just save it if we do robust version. With transcript or run details no need to use the one on Twin."* Final interpretation:

| Path | Status | Why |
|---|---|---|
| Transcript-derived (count-based) | Live now (Phase 1) | Zero new infrastructure; runs against existing `transcript` + `duration_seconds` columns |
| HR run details API (`monitor_runs` MCP / Web Call API) | **Primary "robust" path** | Returns per-node timestamps without HR UI work; explored when MCP perms allow |
| Twin `node_timings_json` column populated by HR Run Python | **Escape-hatch only** (column exists, unpopulated) | Avoids the HR UI Run Python build effort + binding pass; revisit only if run details API turns out insufficient |

The user explicitly chose "transcript or run details API" over "Twin Run Python column" for the robust path. C-T2.9 (Run Python timing-capture node) is **DEFERRED** in the Phase C v2 plan; not skipped permanently. The `node_timings_json` Twin column is ALREADY ADDED (harmless empty col) so the escape hatch is in place if future investigation requires it.

The compute lives in `api/app/services/transcript_telemetry.py` per its design doc, behind the existing 30s TTL cache.

### Phase 1 — count-based from transcript (ships now)
Without per-turn timestamps in `transcript`, the only deterministic input is total duration ÷ turn count.

For each call:
- `turn_count = len(json.loads(transcript))`
- `avg_turn_ms = (duration_seconds × 1000) / max(turn_count, 1)`
- `tool_turn_count = sum(1 for t in turns if t.role == "tool")`

For each filter window:
- `p70_latency_ms = percentile(avg_turn_ms across calls, 70)`
- `p90_latency_ms = percentile(avg_turn_ms across calls, 90)`
- `intermediate_proxy = percentile(tool_turn_count, 50)` (proxy: tool-heavy calls are where filler audio likely fired)

Gives **across-call** percentiles, not per-call. Directionally correct but approximate.

### Phase 2 — HR run details API (PRIMARY robust path)

HR's `monitor_runs` MCP / Web Call run-details API may expose per-node `started_at` / `ended_at` per run. If reachable from FastAPI:
- Pull run details on demand (or batched, behind 30s TTL cache)
- Extract per-tool latency: FMCSA round-trip, query_loads round-trip, etc.
- Per-call p50/p70/p90/p99 from real distribution
- 3-phase decomposition per user direction:
  - **Before-tool latency** = Voice Agent start → first tool start (agent thinking before invoking tools)
  - **During-tool latency** = `tool.end - tool.start` (external service round-trip)
  - **After-tool latency** = last tool end → Voice Agent end (agent wrap-up)

Open question (unresolved at lock time): does the HR `monitor_runs` endpoint actually return per-node start/end timestamps for completed runs, and does our API key tier have access? Requires a probe with a real run_id once Phase C v20 publishes + a test call lands. ADR will be updated post-probe with the actual API shape OR a note that the data isn't available, in which case we fall back to the escape hatch.

### Escape hatch — Twin `node_timings_json` (DEFERRED unless run details API insufficient)

If HR run details API doesn't expose timing data we need:
- Build the C-T2.9 Run Python timing-capture node in HR UI
- Bind its output to the existing (empty) `calls_log.node_timings_json` column
- Phase 2 then reads from Twin instead of run details API
- Same dashboard surface; only the data source swaps

Not done at MVP. Column already exists so the escape hatch is in place.

## 3. Why dashboard-side instead of fixing HR

| Option | Pros | Cons |
|---|---|---|
| **A — Fix HR @ picker bindings** | Single source of truth (Twin) | F8 was already "fixed" once; HR vars still NULL; root cause sits inside HR platform; iteration cost is 100% user-time in HR UI. |
| **B — Dashboard-side compute (chosen)** | Zero HR dependency; full control of percentile algorithm; can iterate without HR UI roundtrips; same TTL cache absorbs the cost. | Slightly worse signal pre Phase-2 (across-call vs per-call); requires transcript to be present (which it will be once that chip is bound). |
| **C — HR Run Python timing capture (Path B-1)** | Real per-node timestamps | Requires new HR node + new Twin column + 1 more chip binding; gated on HR exposing `started_at` / `ended_at` per node — currently uncertain whether HR exposes those vars. |

Option B is the dependency-cheap path that also gives us better algorithmic control; we layer C on later as Phase 2.

## 4. Consequences

### What stays
- The three Twin columns (`intermediate_response_count`, `p70_latency_ms`, `p90_latency_ms`) remain in the schema. We're not dropping them — if HR fixes the bindings later, the data flows in for free.
- Log Event chip bindings for these columns can be added or skipped per user discretion. Both states are equivalent (NULL either way).

### What changes
- `transcript_telemetry.py` gains a `latency_from_transcript()` family of functions per the design doc update below.
- The dashboard's Telemetry tab latency widget reads from those functions, NOT from raw `calls_log.p70_latency_ms`/`p90_latency_ms`.
- Dashboard call-detail view does NOT show "p70 fired / p90 fired" or "X ms" sourced from raw columns; it shows the computed value with a tooltip note "computed from transcript (dashboard-side); HR-side telemetry unavailable".

### What's blocked
- Real per-tool latency (FMCSA round-trip, query_loads round-trip) — blocked on Phase 2 (Path B-1 or HR exposing started_at).
- Time-to-first-carrier-utterance — blocked on per-turn timestamps.
- Dead-air gap distribution — blocked on per-turn timestamps.

## 5. Implementation pointers

- [api/app/services/transcript_telemetry.py](../../api/app/services/transcript_telemetry.py) — add `latency_from_transcript()` and `latency_percentiles_dashboard_side()` per Section 3.5 of [docs/design/transcript-telemetry-module.md](../design/transcript-telemetry-module.md).
- [dashboard/src/components/call-detail/call-telemetry.tsx](../../dashboard/src/components/call-detail/call-telemetry.tsx) — already updated 2026-04-30 to render ms values; rebind the source from raw column to the computed-from-transcript value via API.
- [dashboard/src/lib/api-client.ts](../../dashboard/src/lib/api-client.ts) — add `getCallLatency(call_id)` if call-grain detail wanted, else expose via existing telemetry bundle endpoint.
- Tooltip wording — follow the "computed from transcript" disclosure pattern so users know the signal is approximate until Phase 2.

## 6. Trigger to revisit

Revisit this ADR when:
- HR exposes per-node `started_at` / `ended_at` variables → migrate to Phase 2.
- The Log Event chip's `p70_latency_ms` / `p90_latency_ms` start populating live (signals HR fixed the platform-side issue) → cross-check our computed values against HR's; promote HR's source as authoritative if accurate.
- Path B-1 timing-capture Run Python node ships (C-T2.9 in v2 plan) → migrate to Phase 2 even if HR's own vars stay broken.
