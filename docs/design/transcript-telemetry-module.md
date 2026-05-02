# transcript_telemetry.py — design spec

Target: `api/app/services/transcript_telemetry.py`. Operational telemetry for the Pit Telemetry tab. Computes RPM, TPM, and latency percentiles from `calls_log` rows, plus a Voice-Agent token estimate derived in-process from the `transcript` JSON column. Mirrors `dashboard_aggregations.py` conventions: async functions, single-statement WAF-safe SQL, raw-rows-aggregated-in-Python, 30s TTL cache for SQL-backed results, 60s TTL for transcript parses. Cost is intentionally not computed (per `project_telemetry_widgets_locked.md`).

## 1. Imports and module-level state

- `tiktoken` lazy-loaded at first use (one global encoder for `o200k_base`); `None` when unavailable, and the estimator falls back to `len(words) * 1.3`.
- Two `cachetools.TTLCache` instances behind `asyncio.Lock`s:
  - `_telemetry_cache`: maxsize 512, ttl 30s — for series/percentile/widget bundles.
  - `_transcript_cache`: maxsize 256, ttl 60s — keyed by `call_id` for token estimates.
- Reuses `twin_client.query`, `date_range_clause`, `_parse_dt`, `_to_float`, `_to_int`, `_percentile`, `_normalize_window`, `_filter_key` from `dashboard_aggregations` (import, do not duplicate).

## 2. Public API

### `async def voice_agent_token_estimates(call_id: str) -> dict`
Returns `{"agent_input": int, "agent_output": int, "tool_input": int, "tool_output": int, "total": int}`. Pulls a single row `SELECT transcript FROM calls_log WHERE call_id = :cid`; `json.loads` the string; partition turns by role; tokenize each turn's `content`. 60s TTL cache keyed by `call_id`. Empty/missing transcript returns all zeros. Token-count function is `_count_tokens(text)`: tiktoken `o200k_base.encode` length when available, else `int(len(text.split()) * 1.3)`.

### `async def rpm_series(from_, to_, bucket: str) -> list[dict]`
Returns `[{"t": "<iso bucket start>", "v": <int count>}, ...]`. SQL pulls `SELECT created_at FROM calls_log` + `date_range_clause`. Bucketing entirely client-side — see Section 4. 30s TTL.

### `async def tpm_series(from_, to_, bucket: str, components: list[str]) -> list[dict]`
Returns `[{"t": "<iso>", "v": <int sum>}, ...]`. `components` ⊆ `{"agent","extract","chs","all"}`; "all" expands to the union. Selects only the columns needed plus `created_at` and `transcript` (transcript only when "agent" requested), then sums in Python per bucket. NULL token columns coerce to 0. 30s TTL.

### `async def latency_percentiles(from_, to_, percentiles: list[int]) -> dict`
Returns `{"p50": float|None, "p70": ..., "p90": ..., "p99": ...}` with only the requested keys present.

**Source: NOT the raw `p70_latency_ms` / `p90_latency_ms` columns** — those are NULL forever per ADR-012 (known HR-platform bug). Compute dashboard-side from `transcript` + `duration_seconds`:

- SQL: `SELECT transcript, duration_seconds FROM calls_log` + `date_range_clause`. No raw latency columns selected.
- For each row: `turn_count = len(json.loads(transcript or "[]"))`; `avg_turn_ms = (duration_seconds * 1000) / max(turn_count, 1)`. Coerce non-int durations to None and skip.
- Aggregate `avg_turn_ms` across all rows in the window → apply `_percentile()` for each requested percentile.
- Returns `None` for any percentile when n < 5 (existing `_percentile` already handles this).
- 30s TTL cache.

This is the **Phase 1** count-based approach. Phase 2 (per-turn timestamps) is gated on Path B-1 timing-capture node landing in HR. Document phase distinction in code comments referencing ADR-012.

### `async def voice_agent_widget_data(from_, to_, bucket, percentiles) -> dict`
Bundle for the BIG widget: `{"rpm_series": [...], "tpm_series": [...], "latency_series": [{"t","p50","p70","p90","p99"}], "latency_percentiles": {...}, "totals": {"calls": int, "agent_tokens": int, "tool_tokens": int}}`. Calls helpers in parallel via `asyncio.gather`. `latency_series` is the per-bucket percentile re-computation over the bucket-grouped rows.

### `async def extract_widget_data(from_, to_, bucket, fields) -> dict`
Bundle for Extract widget: `{"rpm_series", "tpm_series", "field_series": {field: [{"t","v"},...]}, "totals": {field: int}}`. `fields` ⊆ `{"input","output","reasoning","cached_input","uncached_input"}` mapped to columns `extract_input_tokens, extract_output_tokens, extract_reasoning_tokens, extract_cached_input_tokens, extract_uncached_input_tokens`. SQL selects only requested columns + `created_at`.

### `async def chs_widget_data(from_, to_, bucket, fields) -> dict`
Identical shape and logic to `extract_widget_data` but on the `chs_*` columns. Implemented by sharing a private `_token_widget_bundle(prefix, ...)` helper that takes column prefix `"extract"` or `"chs"`.

## 3. Token estimation pseudocode

```python
def estimate_from_transcript(transcript_json: str | None) -> dict:
    out = {"agent_input": 0, "agent_output": 0, "tool_input": 0, "tool_output": 0}
    if not transcript_json:
        return out | {"total": 0}
    try:
        turns = json.loads(transcript_json)
    except (json.JSONDecodeError, TypeError):
        return out | {"total": 0}
    if not isinstance(turns, list):
        return out | {"total": 0}
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        role = (turn.get("role") or "").lower()
        content = turn.get("content") or ""
        if not isinstance(content, str):
            content = str(content)
        n = _count_tokens(content)
        if role == "user":
            out["agent_input"] += n
        elif role == "assistant":
            out["agent_output"] += n
        elif role == "tool":
            args, ret = _split_tool_content(content)
            out["tool_input"] += _count_tokens(args)
            out["tool_output"] += _count_tokens(ret)
    out["total"] = sum(out.values())
    return out


def _split_tool_content(s: str) -> tuple[str, str]:
    # heuristic markers in order of preference:
    for marker in ("\nresult:", "\nreturn:", "-> ", "=>"):
        if marker in s:
            i = s.index(marker)
            return s[:i], s[i + len(marker):]
    if "args:" in s and "result:" in s:
        return s.split("result:", 1)[0], s.split("result:", 1)[1]
    # no markers → halve to avoid double-counting
    mid = len(s) // 2
    return s[:mid], s[mid:]
```

## 3.5 Latency computation per ADR-012 (transcript + run details API; Twin column is escape-hatch only)

Per ADR-012:
- HR's `intermediate_response_count` / `p70_latency_ms` / `p90_latency_ms` columns are NULL forever (HR-platform bug). Don't use.
- `node_timings_json` Twin column EXISTS but is unpopulated at MVP — escape hatch only, revisited only if run details API turns out insufficient.
- **Robust path:** transcript content + HR run details API for per-node timestamps.
- **Fallback path:** transcript count-based when run details unavailable.

### Phase 1 — transcript count-based (ships now, fallback)

```python
def _avg_turn_ms(transcript_json: str | None, duration_seconds: int | None) -> float | None:
    if not transcript_json or duration_seconds is None:
        return None
    try:
        turns = json.loads(transcript_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(turns, list) or not turns:
        return None
    return (duration_seconds * 1000.0) / len(turns)


def _tool_turn_count(transcript_json: str | None) -> int:
    if not transcript_json:
        return 0
    try:
        turns = json.loads(transcript_json)
    except (json.JSONDecodeError, TypeError):
        return 0
    if not isinstance(turns, list):
        return 0
    return sum(1 for t in turns if isinstance(t, dict) and (t.get("role") or "").lower() == "tool")
```

Aggregate across calls:
- `p70_latency_ms = _percentile([_avg_turn_ms(r) for r in rows], 70)`
- `p90_latency_ms = _percentile([_avg_turn_ms(r) for r in rows], 90)`
- `intermediate_proxy = _percentile([_tool_turn_count(r) for r in rows], 50)`

Across-call percentiles, not per-call.

### Phase 2 — HR run details API (PRIMARY robust path)

Source: HR `monitor_runs` MCP tool OR Web Call run-details REST API per `call_id`. Returns per-run telemetry that **may** include per-node `started_at` / `ended_at` (verify on first probe).

Pseudocode:

```python
async def fetch_run_details(call_id: str) -> dict | None:
    """Pull per-call run details from HR. 60s TTL cache.

    Response shape (UNVERIFIED at lock time — probe on first real run):
      {
        "run_id": "<uuid>",
        "nodes": [
          {"name": "Voice Agent", "started_at": "...", "completed_at": "..."},
          {"name": "verify_carrier", "started_at": "...", "completed_at": "..."},
          {"name": "query_loads", "started_at": "...", "completed_at": "..."},
          {"name": "Extract Call Details", "started_at": "...", "completed_at": "..."},
          {"name": "Case Health Score", "started_at": "...", "completed_at": "..."},
          ...
        ]
      }
    Returns None if run not found, API unavailable, or no per-node timestamps.
    """
    # impl: httpx call to HR API with HAPPYROBOT_API_KEY; cache by call_id
    ...


def latency_phases_from_run(run_details: dict | None) -> dict | None:
    """Compute 3-phase latency decomposition + per-tool latencies.

    Returns dict with keys:
      voice_call_ms, verify_carrier_ms, query_loads_ms, negotiate_rate_ms,
      book_load_ms, extract_ms, chs_ms,
      before_tool_ms, during_tool_total_ms, after_tool_ms
    Returns None if run_details missing/malformed.
    """
    if not run_details or "nodes" not in run_details:
        return None

    by_name: dict[str, tuple[datetime, datetime]] = {}
    for n in run_details.get("nodes") or []:
        name = (n.get("name") or "").strip()
        s = _parse_dt(n.get("started_at"))
        e = _parse_dt(n.get("completed_at"))
        if name and s and e:
            by_name[name] = (s, e)

    def _delta_ms(name: str) -> int | None:
        if name not in by_name:
            return None
        s, e = by_name[name]
        return int((e - s).total_seconds() * 1000)

    out = {
        "voice_call_ms": _delta_ms("Voice Agent"),
        "verify_carrier_ms": _delta_ms("verify_carrier"),
        "query_loads_ms": _delta_ms("query_loads"),
        "negotiate_rate_ms": _delta_ms("negotiate_rate"),
        "book_load_ms": _delta_ms("book_load"),
        "extract_ms": _delta_ms("Extract Call Details"),
        "chs_ms": _delta_ms("Case Health Score"),
    }

    # 3-phase decomposition anchored against Voice Agent wall-clock
    if "Voice Agent" in by_name:
        voice_start, voice_end = by_name["Voice Agent"]
        tool_intervals = sorted(
            [by_name[n] for n in ("verify_carrier", "query_loads", "negotiate_rate", "book_load")
             if n in by_name],
            key=lambda iv: iv[0],
        )
        if tool_intervals:
            out["before_tool_ms"] = max(0, int((tool_intervals[0][0] - voice_start).total_seconds() * 1000))
            out["during_tool_total_ms"] = sum(
                int((e - s).total_seconds() * 1000) for s, e in tool_intervals
            )
            out["after_tool_ms"] = max(0, int((voice_end - tool_intervals[-1][1]).total_seconds() * 1000))
        else:
            out["before_tool_ms"] = None
            out["during_tool_total_ms"] = None
            out["after_tool_ms"] = None
    else:
        out["before_tool_ms"] = None
        out["during_tool_total_ms"] = None
        out["after_tool_ms"] = None

    return out
```

Aggregate across calls in the window:
- `p70_voice_call_ms = _percentile([d["voice_call_ms"] for d in phase_dicts], 70)`
- Per-tool percentiles for FMCSA, query_loads, etc.
- 3-phase rollup (before / during / after) for cost analysis.

### Composition + fallback

Per-call resolution flow:
1. Try Phase 2 (HR run details API) for `call_id`. 60s TTL cache.
2. If run details fetch fails OR per-node timestamps absent → Phase 1 fallback (transcript + duration count-based).
3. Combine: aggregate Phase 2 rows separately from Phase 1 rows when computing window percentiles, OR mix them with a "approximate" flag in the response so the widget can disclose.

### Escape hatch (DEFERRED)

If the run details API turns out to lack per-node timestamps after probing:
- Implement C-T2.9 in HR (Run Python timing-capture node) — adds ~15 min user-time
- Bind its output to `calls_log.node_timings_json` (already-present empty column)
- Add a third source path in `latency_from_run()` that reads from Twin column
- Same widget API; transparent swap

Don't build this until probe confirms run details API insufficient.

### Tooltip disclosure

```python
def _avg_turn_ms(transcript_json: str | None, duration_seconds: int | None) -> float | None:
    if not transcript_json or duration_seconds is None:
        return None
    try:
        turns = json.loads(transcript_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(turns, list) or not turns:
        return None
    return (duration_seconds * 1000.0) / len(turns)


def _tool_turn_count(transcript_json: str | None) -> int:
    if not transcript_json:
        return 0
    try:
        turns = json.loads(transcript_json)
    except (json.JSONDecodeError, TypeError):
        return 0
    if not isinstance(turns, list):
        return 0
    return sum(1 for t in turns if isinstance(t, dict) and (t.get("role") or "").lower() == "tool")
```

Aggregate across calls in the filter window:
- `p70_latency_ms = _percentile([_avg_turn_ms(r) for r in rows], 70)`
- `p90_latency_ms = _percentile([_avg_turn_ms(r) for r in rows], 90)`
- `intermediate_proxy = _percentile([_tool_turn_count(r) for r in rows], 50)` (count-based proxy: tool-heavy calls are where filler audio likely fired; published as "Intermediate fires (proxy)" in the widget)

### Phase 2 — true per-turn timestamps (gated on Path B-1)

Once HR exposes per-node `started_at` / `ended_at` OR the C-T2.9 timing-capture Run Python ships writing `node_timings_json` to calls_log:

- Per-turn latency = (next_turn.start_at - this_turn.completed_at) when both available
- Per-call p50/p70/p90/p99 from the call's own distribution
- Phase decomposition (per user direction):
  - **`before_tool_latency_ms`** = sum of (assistant_turn duration) for assistant turns BEFORE the first role=tool turn
  - **`during_tool_latency_ms`** = `tool.completed_at - tool.started_at` per tool call (one number per tool turn; aggregate via avg or sum)
  - **`after_tool_latency_ms`** = sum of (assistant_turn duration) for assistant turns AFTER the last role=tool turn

Phase 2 swaps Phase 1's `_avg_turn_ms` for actual timestamp-derived latencies; the API surface stays identical so widgets don't change.

### Tooltip disclosure (Phase 1)

Widget tooltip MUST disclose: *"Computed from transcript turn count ÷ duration; per-turn timestamps unavailable at HR-platform layer (ADR-012). Upgrade to true latency once Path B-1 ships."*

## 4. Bucketing logic (client-side, for WAF safety)

All buckets computed in Python from raw `created_at` rows. UTC throughout (`_parse_dt` already enforces UTC).

```python
def _bucket_key(dt: datetime, bucket: str) -> datetime:
    if bucket == "1m":
        return dt.replace(second=0, microsecond=0)
    if bucket == "5m":
        m = (dt.minute // 5) * 5
        return dt.replace(minute=m, second=0, microsecond=0)
    if bucket == "15m":
        m = (dt.minute // 15) * 15
        return dt.replace(minute=m, second=0, microsecond=0)
    if bucket == "1h":
        return dt.replace(minute=0, second=0, microsecond=0)
    if bucket == "1d":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"unknown bucket {bucket}")
```

A `_bucket_range(start, end, bucket)` helper produces every empty bucket in `[start, end]` so series have continuous x-axes (parallel to `_date_buckets`). RPM/TPM/latency series all walk this list and emit `{"t": iso, "v": ...}`.

For TPM, the "agent" component requires per-row token estimation. Each row carries `created_at + transcript`; the estimator runs once per row in the SQL fetch loop and the `(agent_input + agent_output + tool_input + tool_output)` total adds to that row's bucket. Per-row results are not cached (only the per-`call_id` path through `voice_agent_token_estimates` hits the 60s cache); the 30s series cache absorbs repeat dashboard refreshes.

## 5. SQL templates (all WAF-safe)

- `SELECT created_at FROM calls_log <date_range>` — RPM.
- `SELECT created_at, transcript FROM calls_log <date_range>` — TPM agent component.
- `SELECT created_at, extract_input_tokens, ... FROM calls_log <date_range>` — TPM extract/chs (only requested columns).
- `SELECT p70_latency_ms, p90_latency_ms, created_at FROM calls_log <date_range>` — latency.
- `SELECT transcript FROM calls_log WHERE call_id = '<escaped>'` — single-call estimator (escape via `twin_client._sql_literal`, do not f-string).

No `IN`, no `ORDER BY ... LIMIT`, no multi-aggregate, single-statement only.

## 6. Cache key convention

Mirror `_filter_key` plus the additional knobs:
- `rpm_series:{filter_key}|bucket={bucket}`
- `tpm_series:{filter_key}|bucket={bucket}|comp={','.join(sorted(components))}`
- `latency_percentiles:{filter_key}|pcts={','.join(sorted(map(str,percentiles)))}`
- `voice_widget:{filter_key}|bucket={bucket}|pcts={...}`
- `extract_widget:{filter_key}|bucket={bucket}|fields={...}`
- `chs_widget:{filter_key}|bucket={bucket}|fields={...}`

`_cached_call` is reused by importing from `dashboard_aggregations`. `invalidate_telemetry_cache()` and `telemetry_cache_stats()` exposed for parity, wired to the same `/v1/events/call-ended` Tier-2 hook.

## 7. Edge cases

- Empty transcript / non-list JSON / JSONDecodeError → return zeros, no exception.
- Token columns NULL → coerce via `_to_int(...) or 0` in sums.
- `n < 5` for any latency percentile → `None` for p90/p99; p50/p70 still computed (existing `_percentile` already handles `len==1`).
- Empty bucket → `{"t": iso, "v": 0}` (latency: `None`, not 0, so the chart skips the point).
- Tiktoken import failure → log once at module load, fall back to word*1.3 silently per call.
- Unknown bucket / component / field strings → raise `ValueError`; the API layer maps to 400.
- Timezone-naive `created_at` from Twin → `_parse_dt` already coerces to UTC.

## 8. Test surface

Unit tests at `api/tests/services/test_transcript_telemetry.py`:
- estimator with assistant-only / user-only / tool-only / mixed transcripts
- estimator with malformed JSON, missing column, empty list
- bucketing parity for each bucket value at a known timestamp
- percentile None when `n < 5`
- cache hit on second call (assert Twin called once)
- WAF-safety regression: the SQL strings rendered for each public function contain no `ORDER BY`, no `LIMIT`, no `IN (`, no two `(` after `SELECT` other than function-call openings.

## 9. Critical Files for Implementation

- `api/app/services/transcript_telemetry.py` — new module
- `api/app/services/dashboard_aggregations.py` — pattern source (cache, percentile, date_range_clause, WAF posture)
- `api/app/services/twin_client.py` — async query interface and `_sql_literal` escape
- `api/tests/services/test_transcript_telemetry.py` — companion tests
