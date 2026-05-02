# Dashboard v2 — Engineering Feasibility & Active-Call Research

## 1. SQL feasibility matrix

Constraint set: **single-statement, no `ORDER BY ... LIMIT`, no multi-aggregate SELECT, no `IN (…)`, no `information_schema`, no `UNION`**. Simple `GROUP BY <col>, COUNT(*)` allowed.

**Schema reality (live as of 2026-04-28):**
- `calls_log` — 12 cols. **No `agent_version`, `negotiation_rounds_used`, `p90_latency_ms`** — code referencing those is dead-pathed.
- `bookings` — `id, created_at, call_id, load_id, apply_rate, agreed_at`. **DRIFT FOUND:** `routers/carriers.py:82` queries `WHERE mc_number = :mc_number` — column not in documented schema. **P0 audit item.**
- `loads` — 15 cols.

### Pattern matrix

| # | Pattern | Example metric | WAF-safe SQL | Python fallback | Vol @ 1k/day | Vol @ 10k/day |
|---|---|---|---|---|---|---|
| P1 | Time-bucketed counts | calls/day for 7d | `SELECT date_trunc('day', created_at) AS d, COUNT(*) FROM calls_log WHERE … GROUP BY d` | Pull rows, sort + zero-fill | 7-365 rows | 7-365 rows |
| P2 | Time-bucketed averages | avg booking rate per ISO-week | Pull rows, group + count + divide in Python | — | 4-52 rows | 4-52 rows |
| P3 | Histograms | effective rate delta | `SELECT b.apply_rate, l.loadboard_rate FROM bookings b JOIN loads l ON …` then bucket in Python | — | ~50/day | ~500/day |
| P4 | Top-N rankings | top 10 carriers | `SELECT mc_number, COUNT(*) FROM calls_log WHERE mc_number IS NOT NULL GROUP BY mc_number` then sort + slice | — | ≤200 MCs | ≤2k MCs |
| P5 | Multi-table JOINs | lane analysis | Pull joined rows once; build rollup in Python | — | ~50 rows | ~500 rows |
| P6 | Set-difference | calls without bookings | Two queries; diff in Python | `NOT EXISTS` works as alternative | 2× ~1k rows | 2× ~10k rows |
| P7 | Distinct counts | unique MCs this week | `SELECT mc_number FROM calls_log WHERE …` then `len(set(rows))` | — | ≤200 rows | ≤2k rows |
| P8 | Transcript free-text | "calls mentioning 'reefer'" | `SELECT call_id, transcript FROM calls_log WHERE transcript ILIKE :needle AND created_at >= :from_ts` | Single-needle ILIKE; multi-needle = client-side post-filter | up to 1k rows | 10k rows >5MB risk |

### Volume + cache stampede

- **Demo (current):** 10s of rows. <5ms aggregation.
- **At 1k calls/day:** 30k rows in 30 days. Tractable.
- **At 10k calls/day:** Week-window JOIN ≈ 70k rows ≈ 5-15MB JSON. **Trigger to migrate off Twin.**
- **Cache stampede:** `_cache_lock` is single global, not per-key. Acceptable for MVP.

## 2. HR Monitor API research — active call detection

User asked: how do we show in-progress calls when webhook is end-of-call only?

### What HR exposes

- **`GET /api/v2/workflows/{workflow_id}/runs`** — supports `status` enum: `scheduled | running | completed | canceled | failed`. **`status=running` is first-class.**
- **`GET /api/v2/runs/{run_id}`** — detail.
- **`GET /api/v2/runs/{run_id}/sessions`** — sessions.
- **`GET /api/v2/runs/{run_id}/nodes`** — node outputs in flight.
- **Auth:** Bearer org-key.

**No HR-side workflow change required.**

### Recommended architecture

```
Browser → Next.js /api/calls/active (server route, Bearer)
       → FastAPI GET /v1/calls/active (Bearer-auth, TTL 10s)
       → HR GET /workflows/{wf_id}/runs?status=running
```

Polling not SSE: HR has no `run.started` event; centralizing at FastAPI = N tabs cost 1 HR call per 10s.

### Implementation sketch (`api/app/routers/calls_active.py`)

```python
from fastapi import APIRouter, Depends
from cachetools import TTLCache
import asyncio, httpx
from app.config import settings
from app.deps import require_api_key

_active_cache: TTLCache = TTLCache(maxsize=1, ttl=10)
_lock = asyncio.Lock()
router = APIRouter(prefix="/v1/calls", tags=["calls"])

@router.get("/active", dependencies=[Depends(require_api_key)])
async def active_calls() -> dict:
    async with _lock:
        if "v" in _active_cache:
            return _active_cache["v"]
    async with httpx.AsyncClient(
        base_url=settings.hr_base_url,
        headers={"Authorization": f"Bearer {settings.happyrobot_api_key}"},
        timeout=5.0,
    ) as c:
        resp = await c.get(
            f"/workflows/{settings.hr_workflow_id}/runs",
            params={"status": "running", "page_size": 50},
        )
        resp.raise_for_status()
        data = resp.json()
    runs = [
        {
            "run_id": r["id"],
            "started_at": r.get("started_at") or r.get("created_at"),
            "duration_seconds": r.get("duration_seconds"),
            "current_node": (r.get("current_node") or {}).get("name"),
            "mc_number": (r.get("inputs") or {}).get("mc_number"),
        }
        for r in data.get("data", data.get("runs", []))
    ]
    out = {"count": len(runs), "runs": runs}
    async with _lock:
        _active_cache["v"] = out
    return out
```

**Cache TTL: 10s.** Caps ingress at ~8.6k HR calls/day.
**Config addition:** `hr_workflow_id` (Fly secret `HR_WORKFLOW_ID`).

### Risks + fallback

- Field drift; rate limit unverified; `current_node` may require 2nd round-trip.
- **Tier-2 fallback:** HR Webhook on `workflow.run.start` → new `POST /v1/events/run-started`. ~3hr Claude-time.

**Recommendation: BUILD via Monitor API in MVP.** ~80 LOC, no HR-side change.

## 3. Filter + search backend architecture

| Dimension | Server-side feasible? | WAF-safe clause | Layer |
|---|---|---|---|
| Date range | Yes | `created_at >= :from_ts AND created_at <= :to_ts` | Server-side always |
| Outcome | Yes | `call_outcome = :outcome` | Server-side |
| Sentiment | Yes | `sentiment = :sentiment` | Server-side |
| MC number | Yes | `mc_number = :mc` | Server-side exact |
| Lane | Yes (joins) | `l.origin_state = :origin AND l.destination_state = :dest` | Server-side on lane tabs |
| Equipment type | Yes | `l.equipment_type = :equip` | Server-side on lane tabs |
| Free-text carrier | Partial | `mc_number ILIKE :q || '%'` | Client-side on fetched batch |
| Free-text transcript | Yes (single needle) | `transcript ILIKE '%' || :q || '%'` | Server-side with date narrowing |

### Strategy: hybrid, lean server-side

Default to server-side for date + categorical. Use client-side for free-text fuzz on fetched columns.

### Pydantic Query() params

```python
from typing import Annotated, Literal
from fastapi import Query

OutcomeEnum = Literal["load_booked", "no_match", "carrier_not_qualified", "call_abandoned"]
SentimentEnum = Literal["positive", "neutral", "negative"]

@router.get("/funnel")
async def funnel(
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to_: Annotated[datetime | None, Query(alias="to")] = None,
    outcome: Annotated[OutcomeEnum | None, Query()] = None,
    sentiment: Annotated[SentimentEnum | None, Query()] = None,
    mc: Annotated[str | None, Query(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")] = None,
):
    ...
```

### Cache implications

7 dimensions × 10 values = up to 5040 combos per period. Mitigations:
1. Keep `maxsize=128` — LRU eviction.
2. Bucket date ranges to ISO-week / day boundaries.
3. Accept lower hit rate for ad-hoc filters.
4. Monitor via `dashboard_cache_stats()`.

## 4. Schema gaps

| Likely metric | Gap | Recommendation |
|---|---|---|
| First-call vs repeat-call MC | No "is_first" flag | Compute Python-side at read time |
| Call started timestamp | Only insert-time `created_at` | Derive from duration_seconds; **defer** schema add |
| Negotiation rounds used | Dropped from v15 | **Defer** unless high-value |
| Time-to-first-load-pitched | Not captured | Compute from transcript regex. Tier-2 |
| Carrier name | Not on calls_log | Show MC; add via AI-Extract only if needed |
| Region rollup | Derive from origin_state | Compute Python-side |

## 5. Caching architecture for v2

| Namespace | Items | TTL | Invalidation |
|---|---|---|---|
| `dashboard.*` | funnel/economics/operational/quality/lane | 30s | `call.ended` webhook |
| `time_window.*` | week:N, day:N pre-aggs | 60s | `call.ended` if event in window |
| `active_calls` | live runs | 10s | TTL only |
| `search.*` | transcript ILIKE | 60s | TTL only |
| `carriers.*` | per-MC rollups | 30s | `call.ended` with same `mc_number` |

### Selective invalidation (Tier-1.5)

```python
def invalidate_dashboard_cache(*, mc: str | None = None) -> None:
    if mc is None:
        _dashboard_cache.clear()
        return
    keys_to_drop = [k for k in _dashboard_cache if f":{mc}:" in k]
    for k in keys_to_drop:
        _dashboard_cache.pop(k, None)
```

Requires HR webhook to thread `mc_number`. **Tier-2.**

### Don't cache search

Free-text search: keyspace explodes, freshness expectation high.

## 6. Build / Defer / Reject

### BUILD (15 — MVP)

| # | Item | Effort |
|---|---|---|
| B1 | Header date filter (1d/1w/12w/1m/6m/1y) | S |
| B2 | Active calls panel via Monitor API | M |
| B3 | Effective rate delta time series | S |
| B4 | Calls/day sparkline | S |
| B5 | Outcome funnel by week | S |
| B6 | Top-10 carriers leaderboard | S |
| B7 | Last 5 calls rolling | S |
| B8 | Sentiment over time period | M |
| B9 | CHS distribution histogram | S |
| B10 | FMCSA decline reason breakdown | S |
| B11 | Drilldown: row → call detail page | M |
| B12 | Search: MC prefix + transcript single-needle | M |
| B13 | Acme rebrand + active tab + remove docstring copy | S |
| B14 | vs-yesterday + vs-target badges | M |
| B15 | Filter-aware caching | S |

### DEFER (10 — Tier-2)

D1: Webhook-driven selective cache invalidation by MC. D2: Lane drilldown 3rd page. D3: Per-node tracing on call detail page. D4: Multi-needle transcript search. D5: Real-time SSE for active-calls. D6: `call_started_at` AI Extract column. D7: Repeat-vs-first-call MC segmentation. D8: Region rollup with map viz. D9: Conversion-funnel Sankey. D10: Custom date range w/ shortcuts.

### REJECT (5)

R1: Live transcript streaming (HR doesn't expose). R2: Per-call latency p50/p90/p99 (no field). R3: Agent A/B variant comparison (`agent_version` doesn't exist). R4: CSV export (spec doesn't mention). R5: Persona-switcher UI toggle (multi-persona is IA, not runtime).

## 7. Integration risks

**Active-call API:** Schema drift; rate limit unverified; `current_node` may require 2nd round-trip.

**Filter combo cache invalidation:** Webhook clears all entries — wasteful at 10k+/day. Ship MC-selective invalidation Tier-1.5.

**Multi-page drilldown vs ISR:** Chains beyond depth 2 may exceed `revalidate=30s`. Drilldown pages set `dynamic='force-dynamic'`.

**WAF surprise:** `FILTER (WHERE …)`, multi-arm `CASE`, novel `JOIN+GROUP BY` are unverified. Live-test before merging.

## 8. Final report

**Total items evaluated:** 30 (15 BUILD + 10 DEFER + 5 REJECT)

**Top 3 risks:**
1. **Cloudflare WAF surprises on new query shapes** — every novel SQL must be live-verified.
2. **`bookings.mc_number` drift** — `routers/carriers.py:82` queries undocumented column. **P0 audit.**
3. **HR Monitor API field availability** — `current_node`, `started_at`, `inputs.mc_number` speculative.

**Estimated Claude-time for MVP build set:**

| Effort | Items | Hrs each | Total |
|---|---|---|---|
| S | 10 items | 1.5 | 15 |
| M | 5 items | 4 | 20 |
| **Total** | | | **~35 Claude-hrs** |

**Recommended sequencing:**
1. B15 (filter-aware caching)
2. B1 (header date filter)
3. B13 (rebrand + remove copy) — parallelizable
4. B3 + B4 + B5 + B8 + B14 — KPI + time series
5. B6 + B7 + B9 + B10 — leaderboards + distributions
6. B2 (active calls) — needs HR live-probe
7. B11 + B12 (drilldown + search)
