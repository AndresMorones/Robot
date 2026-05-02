"""Aggregation functions for the dashboard layer.

Two flavors live here:

1. **Tier 1 SQL-backed metrics** (M-001, M-080, M-081, M-082, M-010) — async
   functions that hit Twin via `twin_client.query`. These join `calls_log` and
   `bookings` server-side and are the canonical source for the four dashboard
   endpoints (funnel / economics / operational / quality).

2. **Legacy pure-Python aggregations** — operate on lists of row dicts pulled
   into memory. Still used by the HTML dashboard view (`dashboard_view.py`)
   for trend charts, heatmaps, alerts, etc. Stdlib-only, defensive on missing
   keys / None values / string-formatted numbers so a single bad row never
   crashes the dashboard.

## Cloudflare WAF constraint (third-party, in front of HR Twin)

HR Twin's `/twin/sql` endpoint sits behind a Cloudflare WAF that enforces a
generic OWASP-aligned SQL-injection ruleset. It blocks any SQL string whose
shape resembles an extraction / probe attempt — even when our org-level Bearer
key authenticates. Triggers we've hit:

  - `information_schema.*` queries (database introspection)
  - `ORDER BY <col> LIMIT <n>` patterns (pagination-based blind extraction)
  - Multi-aggregate SELECTs (`SELECT AVG(a), SUM(b), COUNT(*) FROM t`)
  - `IN (...)` lists with literals
  - `UNION ALL` / `UNION SELECT`

WAF rejection surfaces as a 403 HTML body, NOT a JSON error. Symptom: dashboard
shows `Twin SQL error (403): <!DOCTYPE html>...`.

Defensive posture in every helper below:
  1. Single-statement queries only
  2. NO multi-aggregate SELECT — pull raw rows + aggregate in Python
     (economics, operational, chs_distribution, revenue, bookings_per_call)
  3. NO `ORDER BY ... LIMIT` — sort + slice in Python
     (audit_sample, list_calls, list_carriers)
  4. NO `IN (...)` — use `LEFT JOIN ... IS NULL` or `NOT EXISTS` for set-difference
  5. GROUP BY simple aggregates ARE allowed — outcome / sentiment distributions

This shifts a tiny amount of compute from SQL to Python (negligible for the
demo dataset's dozens of rows) in exchange for never falling outside the WAF's
safe zone. Full discussion in `docs/services-integration.md` §6.5.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Awaitable, Callable, Iterable

from cachetools import TTLCache

from app.services.twin_client import twin_client


# ---------------------------------------------------------------- cache layer
#
# Single-process, async-safe TTL cache for the SQL-backed dashboard
# aggregation functions. Each dashboard endpoint render fans out to ~5
# aggregation calls; without caching every browser refresh re-issues every
# query against Twin. With a 30s TTL we drop steady-state Twin load by ~95%
# while keeping freshness acceptable for an operational dashboard.
#
# Multi-machine deployment (Tier-2): swap this for Redis. The
# `invalidate_dashboard_cache()` helper exists so an event-driven
# invalidation path (e.g. POST /v1/events/call-ended) can flush stale
# entries the moment new data lands.

_DASHBOARD_CACHE_TTL_SECONDS = 30
# Bumped 128 → 512 for v2 filter cache keys (each unique
# (function, from_, to_) tuple is its own slot). Per
# 08-filter-state-architecture.md §5: 7 active dimensions × ~5 typical values
# each is the worst-case keyspace, but realistic hit-pattern keeps occupancy
# well under the new cap. ~5KB/entry → ~2.5MB heap, trivial on Fly's 256MB tier.
_DASHBOARD_CACHE_MAXSIZE = 512

_dashboard_cache: TTLCache = TTLCache(
    maxsize=_DASHBOARD_CACHE_MAXSIZE, ttl=_DASHBOARD_CACHE_TTL_SECONDS
)
_cache_lock = asyncio.Lock()


# ---------------------------------------------------------------- date filter
#
# `date_range_clause` builds the `WHERE created_at BETWEEN ...` fragment that
# every filter-aware aggregation appends to its base SQL. Both endpoints are
# rendered via Python ISO-8601 strings — the WAF-safe shape we already use
# elsewhere (no params + literal-only). Single-statement, no IN, no UNION,
# no ORDER BY ... LIMIT. The literal datetimes we inject are already validated
# by FastAPI's `datetime` Query type, so they cannot carry SQL fragments.
#
# `prefix` lets callers compose the clause into existing queries:
#   - "WHERE "  — start a brand-new WHERE
#   - "AND "    — append after an existing WHERE
#   - ""        — caller injects the connector themselves


def _waf_safe_dt(dt: datetime) -> str:
    """Format a datetime as a SQL literal Cloudflare WAF accepts.

    The WAF in front of Twin trips on the `+00:00` offset substring inside
    quoted SQL literals. Drop the offset and use a space separator;
    PostgreSQL parses both forms identically against `timestamptz` columns.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def date_range_clause(
    from_: datetime | None,
    to_: datetime | None,
    *,
    column: str = "created_at",
    prefix: str = "AND ",
) -> str:
    """ALWAYS empty string. Cloudflare WAF in front of HR Twin blocks ANY
    `created_at` comparison (`>=`, `<=`, `=`, EXTRACT, etc.) when the value
    is a literal — even numeric epochs. Probed live 2026-04-30: only
    `IS NULL` / `IS NOT NULL` checks pass through.

    Date filtering MUST happen Python-side on the pulled rows (see
    `_filter_rows_by_date`). This function is kept as a no-op so existing
    callers compile, but it injects nothing.

    Args are deliberately ignored. Tests covering the previous SQL output
    were removed when this WAF block was discovered.
    """
    _ = (from_, to_, column, prefix)
    return ""


def _filter_key(from_: datetime | None, to_: datetime | None) -> str:
    """Stable cache-key suffix for filter combinations."""
    a = from_.isoformat() if from_ else None
    b = to_.isoformat() if to_ else None
    return f"from={a or 'none'}|to={b or 'none'}"


async def _cached_call(
    key: str,
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """30s TTL cache for async aggregation results.

    Cache key = function name + serialized args (None args produce key 'fn_name:').
    Single-machine in-process cache. Multi-machine deployment requires Redis
    (Tier-2).
    """
    async with _cache_lock:
        if key in _dashboard_cache:
            return _dashboard_cache[key]
    result = await fn(*args, **kwargs)
    async with _cache_lock:
        _dashboard_cache[key] = result
    return result


def invalidate_dashboard_cache() -> None:
    """Clear all cached aggregations. Call from event-driven invalidation
    paths (e.g., POST /v1/events/call-ended) when those land in Tier-2."""
    _dashboard_cache.clear()


def dashboard_cache_stats() -> dict[str, int]:
    """Inspect cache occupancy. Useful for startup/diagnostic logs."""
    return {
        "currsize": len(_dashboard_cache),
        "maxsize": _dashboard_cache.maxsize,
        "ttl_seconds": int(_dashboard_cache.ttl),
    }


_OUTCOME_ENUMS = ("load_booked", "no_match", "carrier_not_qualified", "call_abandoned")
_AUDIT_KEYWORDS = (
    "fmcsa",
    "inactive",
    "tool",
    "fail",
    "confus",
    "hallucin",
    "declined",
    "unclear",
    "abandoned",
)
_ALERT_AUDIT_REGEX = re.compile(r"tool|fail|confus|hallucin|inactive|fmcsa", re.IGNORECASE)


def _first(*values: Any) -> Any:
    for v in values:
        if v not in (None, ""):
            return v
    return None


def _outcome(r: dict[str, Any]) -> str | None:
    return _first(r.get("call_outcome"), r.get("outcome"), r.get("classification"))


def _sentiment(r: dict[str, Any]) -> str | None:
    return _first(
        r.get("sentiment"),
        r.get("sentiment_classification"),
        r.get("sentiment_end"),
        r.get("real_time_sentiment_classifier"),
    )


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_int(v: Any) -> int | None:
    f = _to_float(v)
    if f is None:
        return None
    try:
        return int(f)
    except (ValueError, TypeError):
        return None


def _apply_rate(r: dict[str, Any]) -> float | None:
    # Legacy row-mode helper (HTML dashboard view). Post-v15 the rate column
    # lives in `bookings` (`apply_rate`), not in calls_log row dicts; histogram
    # calls fed via `list_calls()` will yield empty data unless the caller pre-
    # joins bookings into the row dicts.
    return _to_float(r.get("apply_rate"))


def _case_health(r: dict[str, Any]) -> int | None:
    return _to_int(r.get("case_health_score"))


def _latency(r: dict[str, Any]) -> float | None:
    return _to_float(r.get("p90_latency_ms"))


def _duration(r: dict[str, Any]) -> int | None:
    v = _first(r.get("duration_seconds"), r.get("duration"))
    return _to_int(v)


def _parse_dt(v: Any) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _created_at(r: dict[str, Any]) -> datetime | None:
    return _parse_dt(r.get("created_at"))


def _within_window(
    r: dict[str, Any],
    from_: datetime | None,
    to_: datetime | None,
) -> bool:
    """In-memory replacement for `WHERE created_at BETWEEN ...`.

    The Cloudflare WAF in front of HR Twin blocks every comparison on
    `created_at` (probed live 2026-04-30), so we MUST pull rows without a
    server-side date filter and apply the window here.
    """
    if from_ is None and to_ is None:
        return True
    ca = _created_at(r)
    if ca is None:
        return False
    if from_ is not None and ca < from_:
        return False
    if to_ is not None and ca > to_:
        return False
    return True


def _sorted_by_created(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: _created_at(r) or datetime.min.replace(tzinfo=timezone.utc),
    )


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def apply_filters(
    rows: list[dict[str, Any]],
    from_: str | None = None,
    to_: str | None = None,
    outcome: str | None = None,
    sentiment: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    dt_from = _parse_dt(from_) if from_ else None
    dt_to = _parse_dt(to_) if to_ else None
    q_norm = q.strip().lower() if q else None

    out: list[dict[str, Any]] = []
    for r in rows:
        if dt_from or dt_to:
            ca = _created_at(r)
            if ca is None:
                continue
            if dt_from and ca < dt_from:
                continue
            if dt_to and ca > dt_to:
                continue
        if outcome and _outcome(r) != outcome:
            continue
        if sentiment and _sentiment(r) != sentiment:
            continue
        if q_norm:
            mc = str(r.get("mc_number") or "").lower()
            name = str(r.get("carrier_name") or "").lower()
            if q_norm not in mc and q_norm not in name:
                continue
        out.append(r)
    return out


def outcome_trend(rows: list[dict[str, Any]], days: int = 30) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    labels = [(today - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    label_idx = {lbl: i for i, lbl in enumerate(labels)}
    series: dict[str, list[int]] = {k: [0] * days for k in _OUTCOME_ENUMS}

    for r in rows:
        ca = _created_at(r)
        if ca is None:
            continue
        key = ca.date().isoformat()
        idx = label_idx.get(key)
        if idx is None:
            continue
        oc = _outcome(r)
        if oc in series:
            series[oc][idx] += 1

    return {"labels": labels, "series": series}


def chs_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    counts = [0] * 5
    for r in rows:
        v = _case_health(r)
        if v is None:
            continue
        if v < 0:
            v = 0
        if v > 100:
            v = 100
        idx = min(v // 20, 4)
        counts[idx] += 1
    return {"buckets": buckets, "counts": counts}


def apply_rate_histogram(rows: list[dict[str, Any]], bins: int = 10) -> dict[str, Any]:
    """Histogram of bookings.apply_rate values for booked calls.

    Function name uses the source-of-truth column (`apply_rate`); the dashboard
    UI labels this "Agreed rate" for broker readability. Both terms refer to the
    same value — the rate the carrier accepted at booking time.
    """
    vals = [
        v
        for v in (_apply_rate(r) for r in rows if _outcome(r) == "load_booked")
        if v is not None
    ]
    if not vals or bins < 1:
        return {"bin_edges": [], "counts": []}
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return {"bin_edges": [lo, lo + 1.0], "counts": [len(vals)]}
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins + 1)]
    counts = [0] * bins
    for v in vals:
        idx = int((v - lo) / width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1
    return {"bin_edges": edges, "counts": counts}


def fmcsa_decline_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter = Counter()
    declined = 0
    for r in rows:
        reason = r.get("fmcsa_eligibility_failure_reason")
        if reason:
            counter[str(reason).strip().upper()] += 1
            declined += 1
    total = len(rows)
    rate = round(declined / total * 100, 2) if total else 0.0
    items = counter.most_common()
    return {
        "reasons": [k for k, _ in items],
        "counts": [v for _, v in items],
        "decline_rate_pct": rate,
    }


def call_volume_heatmap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    matrix: list[list[int]] = [[0] * 24 for _ in range(7)]
    for r in rows:
        ca = _created_at(r)
        if ca is None:
            continue
        matrix[ca.weekday()][ca.hour] += 1
    return {"matrix": matrix, "days": days, "hours": list(range(24))}


def carrier_rollup(rows: list[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        mc = str(r.get("mc_number") or "").strip()
        if not mc:
            continue
        groups[mc].append(r)

    rollup: list[dict[str, Any]] = []
    for mc, grp in groups.items():
        booked = sum(1 for r in grp if _outcome(r) == "load_booked")
        chs_vals = [v for v in (_case_health(r) for r in grp) if v is not None]
        last_ca = max(
            (_created_at(r) for r in grp if _created_at(r) is not None),
            default=None,
        )
        name = next(
            (r.get("carrier_name") for r in grp if r.get("carrier_name")), None
        )
        rollup.append(
            {
                "mc_number": mc or None,
                "carrier_name": name,
                "call_count": len(grp),
                "booked_count": booked,
                "booking_rate_pct": round(booked / len(grp) * 100, 2) if grp else 0.0,
                "avg_chs": round(mean(chs_vals), 2) if chs_vals else None,
                "last_call_at": last_ca,
            }
        )
    rollup.sort(key=lambda x: (-x["call_count"], -x["booked_count"]))
    return rollup[:top_n]


def agent_version_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        v = r.get("agent_version") or "unknown"
        groups[str(v)].append(r)

    out: list[dict[str, Any]] = []
    for ver, grp in groups.items():
        booked = sum(1 for r in grp if _outcome(r) == "load_booked")
        chs_vals = [v for v in (_case_health(r) for r in grp) if v is not None]
        out.append(
            {
                "version": ver,
                "call_count": len(grp),
                "booking_rate_pct": round(booked / len(grp) * 100, 2) if grp else 0.0,
                "avg_chs": round(mean(chs_vals), 2) if chs_vals else None,
            }
        )
    out.sort(key=lambda x: -x["call_count"])
    return out


def audit_remarks_clusters(
    rows: list[dict[str, Any]], top_n: int = 5
) -> list[dict[str, Any]]:
    counter: Counter = Counter()
    for r in rows:
        text = r.get("audit_remarks")
        if not text:
            continue
        low = str(text).lower()
        for kw in _AUDIT_KEYWORDS:
            if kw in low:
                counter[kw] += 1
    return [{"tag": k, "count": v} for k, v in counter.most_common(top_n)]


def _avg(vals: Iterable[float]) -> float | None:
    lst = list(vals)
    return mean(lst) if lst else None


def _booking_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    booked = sum(1 for r in rows if _outcome(r) == "load_booked")
    return booked / len(rows) * 100.0


def system_alerts(
    rows: list[dict[str, Any]],
    recent_window: int = 20,
    baseline_window: int = 200,
) -> list[dict[str, Any]]:
    sorted_rows = _sorted_by_created(rows)
    recent = sorted_rows[-recent_window:]
    trailing = sorted_rows[-(recent_window + baseline_window) : -recent_window]

    if len(recent) < 5:
        names_meta = [
            ("booking_rate_cliff", "page"),
            ("quality_drift", "warn"),
            ("fmcsa_failure_spike", "page"),
            ("duration_outlier_rate", "info"),
            ("audit_keyword_cluster", "warn"),
        ]
        return [
            {
                "name": n,
                "severity": s,
                "value": None,
                "threshold": None,
                "fired": False,
                "detail": "insufficient data",
            }
            for n, s in names_meta
        ]

    alerts: list[dict[str, Any]] = []

    br_recent = _booking_rate(recent)
    br_trailing = _booking_rate(trailing)
    fired_br = False
    detail_br = "ok"
    if br_recent is not None and br_trailing is not None and br_trailing > 0:
        drop = (br_trailing - br_recent) / br_trailing
        fired_br = drop > 0.40
        if fired_br:
            detail_br = f"recent={br_recent:.1f}% trailing={br_trailing:.1f}%"
    alerts.append(
        {
            "name": "booking_rate_cliff",
            "severity": "page",
            "value": round(br_recent, 2) if br_recent is not None else None,
            "threshold": 40.0,
            "fired": fired_br,
            "detail": detail_br,
        }
    )

    chs_recent = [v for v in (_case_health(r) for r in recent) if v is not None]
    chs_trailing = [v for v in (_case_health(r) for r in trailing) if v is not None]
    avg_chs_recent = _avg(chs_recent)
    avg_chs_trailing = _avg(chs_trailing)
    fired_qd = False
    detail_qd = "ok"
    if avg_chs_recent is not None and avg_chs_trailing is not None:
        drop = avg_chs_trailing - avg_chs_recent
        fired_qd = drop >= 15
        if fired_qd:
            detail_qd = f"recent={avg_chs_recent:.1f} trailing={avg_chs_trailing:.1f}"
    alerts.append(
        {
            "name": "quality_drift",
            "severity": "warn",
            "value": round(avg_chs_recent, 2) if avg_chs_recent is not None else None,
            "threshold": 15.0,
            "fired": fired_qd,
            "detail": detail_qd,
        }
    )

    fmcsa_fail = sum(
        1 for r in recent if r.get("fmcsa_eligibility_failure_reason")
    )
    pct_fmcsa = fmcsa_fail / len(recent) * 100
    alerts.append(
        {
            "name": "fmcsa_failure_spike",
            "severity": "page",
            "value": round(pct_fmcsa, 2),
            "threshold": 60.0,
            "fired": pct_fmcsa > 60,
            "detail": f"{fmcsa_fail}/{len(recent)} declines",
        }
    )

    out_dur = 0
    for r in recent:
        d = _duration(r)
        if d is None:
            continue
        if d < 15 or d > 480:
            out_dur += 1
    pct_dur = out_dur / len(recent) * 100
    alerts.append(
        {
            "name": "duration_outlier_rate",
            "severity": "info",
            "value": round(pct_dur, 2),
            "threshold": 20.0,
            "fired": pct_dur > 20,
            "detail": f"{out_dur}/{len(recent)} outside 15-480s",
        }
    )

    kw_hits = sum(
        1 for r in recent if r.get("audit_remarks") and _ALERT_AUDIT_REGEX.search(str(r.get("audit_remarks")))
    )
    alerts.append(
        {
            "name": "audit_keyword_cluster",
            "severity": "warn",
            "value": float(kw_hits),
            "threshold": 3.0,
            "fired": kw_hits >= 3,
            "detail": f"{kw_hits} hits in last {len(recent)}",
        }
    )

    return alerts


# ---------------------------------------------------------------- Tier 1 metrics
#
# Each function returns (value, count_basis) so the dashboard can render
# goals/comparisons. `count_basis` is the denominator population the value is
# computed against, or None when the metric is itself a count.

MetricResult = tuple[float | int | None, int | None]


def _safe_div(num: float | None, den: float | None) -> float | None:
    """Division that returns None on zero/missing denominator."""
    if num is None or den is None:
        return None
    try:
        d = float(den)
    except (TypeError, ValueError):
        return None
    if d == 0:
        return None
    return float(num) / d


def _safe_count(rows: list[dict[str, Any]] | None) -> int:
    """Null-resilient row counting."""
    if not rows:
        return 0
    return sum(1 for r in rows if r is not None)


def _scalar(rows: list[dict[str, Any]], key: str) -> Any:
    """Pull a single value from the first row of a SELECT-aggregate query."""
    if not rows:
        return None
    return rows[0].get(key)


async def _total_calls_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> MetricResult:
    """M-001 — total rows in calls_log."""
    sql = "SELECT created_at FROM calls_log"
    where = date_range_clause(from_, to_, prefix="WHERE ")
    rows = await twin_client.query(sql + where)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    return len(rows), None


async def total_calls(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> MetricResult:
    key = f"total_calls:{_filter_key(from_, to_)}"
    return await _cached_call(key, _total_calls_uncached, from_=from_, to_=to_)


async def _total_bookings_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> MetricResult:
    """M-080 — total rows in bookings."""
    sql = "SELECT created_at FROM bookings"
    where = date_range_clause(from_, to_, prefix="WHERE ")
    rows = await twin_client.query(sql + where)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    return len(rows), None


async def total_bookings(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> MetricResult:
    key = f"total_bookings:{_filter_key(from_, to_)}"
    return await _cached_call(key, _total_bookings_uncached, from_=from_, to_=to_)


async def _calls_without_booking_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> MetricResult:
    """M-081 — calls_log rows with no matching bookings row.

    Cloudflare WAF flags `LEFT JOIN ... IS NULL` patterns (it looks like the
    "find rows missing in a junction table" extraction shape). Refactored to
    pull both call_id sets independently and diff in Python — fully WAF-safe.
    """
    call_sql = "SELECT call_id, created_at FROM calls_log" + date_range_clause(
        from_, to_, prefix="WHERE "
    )
    # Bookings filter is on the call's window, not the booking's, so we filter
    # the call set first and intersect against the bookings call_id index.
    booking_sql = "SELECT call_id FROM bookings"

    call_rows = await twin_client.query(call_sql)
    booking_rows = await twin_client.query(booking_sql)

    call_rows = [r for r in call_rows if _within_window(r, from_, to_)]
    booked_ids = {r.get("call_id") for r in booking_rows if r.get("call_id")}
    total = len(call_rows)
    no_booking = sum(
        1 for r in call_rows if r.get("call_id") and r.get("call_id") not in booked_ids
    )
    return no_booking, total


async def calls_without_booking(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> MetricResult:
    key = f"calls_without_booking:{_filter_key(from_, to_)}"
    return await _cached_call(
        key, _calls_without_booking_uncached, from_=from_, to_=to_
    )


async def bookings_per_booked_call() -> MetricResult:
    """M-082 — average # of bookings per call that booked at least one load.

    Cloudflare WAF blocks `COUNT(*) + COUNT(DISTINCT)` in one SELECT — pull
    call_id rows once, count + distinct in Python.
    """
    rows = await twin_client.query("SELECT call_id FROM bookings")
    if not rows:
        return None, 0
    bookings_int = len(rows)
    distinct_calls = {r.get("call_id") for r in rows if r.get("call_id")}
    basis_int = len(distinct_calls)
    avg = _safe_div(bookings_int, basis_int)
    return (round(avg, 2) if avg is not None else None), basis_int


async def revenue_booked() -> MetricResult:
    """M-010 — total apply_rate over all bookings.

    Cloudflare WAF blocks `SUM + COUNT` in same SELECT — pull rows + sum/len
    in Python.
    """
    rows = await twin_client.query("SELECT apply_rate FROM bookings")
    if not rows:
        return 0.0, 0
    vals: list[float] = []
    for r in rows:
        v = r.get("apply_rate")
        if v is None:
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    return round(sum(vals), 2), len(rows)


async def calls_without_booking_not_exists() -> MetricResult:
    """Same as `calls_without_booking` but using NOT EXISTS — Cloudflare WAF
    fallback when the LEFT JOIN form is rejected (per deliverable note).
    """
    sql = (
        "SELECT COUNT(*) AS n "
        "FROM calls_log c "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM bookings b WHERE b.call_id = c.call_id"
        ")"
    )
    rows = await twin_client.query(sql)
    n = _scalar(rows, "n") or 0

    total_rows = await twin_client.query("SELECT COUNT(*) AS n FROM calls_log")
    basis = _scalar(total_rows, "n") or 0
    try:
        return int(n), int(basis)
    except (TypeError, ValueError):
        return 0, 0


async def _outcome_distribution_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, int]:
    """Funnel support — rows by call_outcome enum.

    Defensive: pull raw outcomes + count in Python (parallel pattern with
    sentiment_distribution).
    """
    sql = "SELECT call_outcome, created_at FROM calls_log" + date_range_clause(
        from_, to_, prefix="WHERE "
    )
    rows = await twin_client.query(sql)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    out: dict[str, int] = {}
    for r in rows:
        key = r.get("call_outcome") or "unknown"
        out[str(key)] = out.get(str(key), 0) + 1
    return out


async def outcome_distribution(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, int]:
    key = f"outcome_distribution:{_filter_key(from_, to_)}"
    return await _cached_call(
        key, _outcome_distribution_uncached, from_=from_, to_=to_
    )


async def avg_apply_rate() -> float | None:
    """Economics support — mean booking rate across all bookings."""
    sql = "SELECT AVG(apply_rate) AS avg_rate FROM bookings"
    rows = await twin_client.query(sql)
    avg = _scalar(rows, "avg_rate")
    if avg is None:
        return None
    try:
        return round(float(avg), 2)
    except (TypeError, ValueError):
        return None


async def _economics_rate_summary_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, Any]:
    """Economics core — joins bookings to loads and returns the rate KPI bundle.

    Cloudflare WAF blocks multi-aggregate SELECTs (multiple AVG/SUM/COUNT in a
    single SELECT trigger 403s on JOIN queries). Refactored to fetch raw join
    rows once and compute the four aggregates in Python. Twin payload stays
    small (1 row per booking; demo dataset is dozens of rows).

    Filter targets `bookings.created_at` (alias `b.created_at`) — the booking
    timestamp is what we want for revenue periodicity.

    Returns: {avg_loadboard_rate, avg_agreed_rate, bookings_count, total_revenue}
    Each value is None when no rows exist.
    """
    sql = (
        "SELECT b.apply_rate AS apply_rate, l.loadboard_rate AS loadboard_rate, "
        "b.created_at AS created_at "
        "FROM bookings b JOIN loads l ON l.load_id = b.load_id"
    )
    sql += date_range_clause(from_, to_, column="b.created_at", prefix="WHERE ")
    rows = await twin_client.query(sql)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    if not rows:
        return {
            "avg_loadboard_rate": None,
            "avg_agreed_rate": None,
            "bookings_count": 0,
            "total_revenue": 0.0,
        }

    def _f(v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    apply_vals = [v for v in (_f(r.get("apply_rate")) for r in rows) if v is not None]
    loadboard_vals = [
        v for v in (_f(r.get("loadboard_rate")) for r in rows) if v is not None
    ]

    return {
        "avg_loadboard_rate": (
            round(sum(loadboard_vals) / len(loadboard_vals), 2)
            if loadboard_vals
            else None
        ),
        "avg_agreed_rate": (
            round(sum(apply_vals) / len(apply_vals), 2) if apply_vals else None
        ),
        "bookings_count": len(rows),
        "total_revenue": round(sum(apply_vals), 2) if apply_vals else 0.0,
    }


async def economics_rate_summary(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, Any]:
    key = f"economics_rate_summary:{_filter_key(from_, to_)}"
    return await _cached_call(
        key, _economics_rate_summary_uncached, from_=from_, to_=to_
    )


async def _sentiment_distribution_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, int]:
    """Quality support — rows by sentiment enum.

    Cloudflare WAF has flagged `WHERE x IS NOT NULL GROUP BY x` patterns. Pull
    raw sentiments and count in Python. Tiny payload (one short string per call).
    """
    sql = "SELECT sentiment, created_at FROM calls_log" + date_range_clause(
        from_, to_, prefix="WHERE "
    )
    rows = await twin_client.query(sql)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    out: dict[str, int] = {}
    for r in rows:
        key = r.get("sentiment")
        if not key:
            continue
        out[str(key)] = out.get(str(key), 0) + 1
    return out


async def sentiment_distribution(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, int]:
    key = f"sentiment_distribution:{_filter_key(from_, to_)}"
    return await _cached_call(
        key, _sentiment_distribution_uncached, from_=from_, to_=to_
    )


async def _avg_case_health_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> float | None:
    """Quality support — mean CHS across calls_log."""
    sql = (
        "SELECT case_health_score, created_at "
        "FROM calls_log "
        "WHERE case_health_score IS NOT NULL"
    )
    sql += date_range_clause(from_, to_, prefix="AND ")
    rows = await twin_client.query(sql)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    vals = [v for v in (_to_float(r.get("case_health_score")) for r in rows) if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


async def avg_case_health(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> float | None:
    key = f"avg_case_health:{_filter_key(from_, to_)}"
    return await _cached_call(key, _avg_case_health_uncached, from_=from_, to_=to_)


async def avg_duration_seconds() -> float | None:
    """Operational support — mean call duration."""
    sql = (
        "SELECT AVG(duration_seconds) AS avg_dur "
        "FROM calls_log "
        "WHERE duration_seconds IS NOT NULL"
    )
    rows = await twin_client.query(sql)
    avg = _scalar(rows, "avg_dur")
    if avg is None:
        return None
    try:
        return round(float(avg), 2)
    except (TypeError, ValueError):
        return None


async def fmcsa_decline_count() -> int:
    """Operational support — calls where FMCSA failed (non-null reason)."""
    sql = (
        "SELECT COUNT(*) AS n "
        "FROM calls_log "
        "WHERE fmcsa_eligibility_failure_reason IS NOT NULL"
    )
    rows = await twin_client.query(sql)
    n = _scalar(rows, "n") or 0
    try:
        return int(n)
    except (TypeError, ValueError):
        return 0


async def _operational_summary_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, float | None]:
    """Operational KPIs over calls_log: avg duration, fmcsa decline %, abandon %.

    Cloudflare WAF blocks multi-aggregate SELECTs (AVG + multiple SUM(CASE) +
    COUNT(*) in one SELECT triggers 403). Refactored to pull raw rows once and
    compute aggregates in Python. Demo dataset is small (dozens of rows).

    abandon_rate = calls with `call_outcome = 'call_abandoned'` / total. Stable
    enum from v15 Classify Outcome (see test-scenarios.md).
    """
    sql = (
        "SELECT duration_seconds, fmcsa_eligibility_failure_reason, call_outcome, created_at "
        "FROM calls_log"
    )
    sql += date_range_clause(from_, to_, prefix="WHERE ")
    rows = await twin_client.query(sql)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    total = len(rows)
    if total == 0:
        return {
            "avg_duration_seconds": None,
            "fmcsa_decline_pct": None,
            "abandon_rate_pct": None,
        }

    durations = [
        v for v in (_to_float(r.get("duration_seconds")) for r in rows) if v is not None
    ]
    fmcsa_fail = sum(
        1 for r in rows if r.get("fmcsa_eligibility_failure_reason") not in (None, "")
    )
    abandoned = sum(1 for r in rows if r.get("call_outcome") == "call_abandoned")

    return {
        "avg_duration_seconds": (
            round(sum(durations) / len(durations), 2) if durations else None
        ),
        "fmcsa_decline_pct": round(fmcsa_fail / total * 100, 2),
        "abandon_rate_pct": round(abandoned / total * 100, 2),
    }


async def operational_summary(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, float | None]:
    key = f"operational_summary:{_filter_key(from_, to_)}"
    return await _cached_call(
        key, _operational_summary_uncached, from_=from_, to_=to_
    )


async def _chs_distribution_sql_uncached(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, int]:
    """Quality support — case_health_score histogram, 5 buckets of width 20.

    Cloudflare WAF blocks 5×SUM(CASE WHEN) in a single SELECT (multi-aggregate
    pattern). Refactored to pull raw scores and bucket in Python.
    """
    sql = (
        "SELECT case_health_score, created_at FROM calls_log WHERE case_health_score IS NOT NULL"
    )
    sql += date_range_clause(from_, to_, prefix="AND ")
    rows = await twin_client.query(sql)
    rows = [r for r in rows if _within_window(r, from_, to_)]
    labels = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    counts = [0] * 5
    for r in rows:
        v = r.get("case_health_score")
        if v is None:
            continue
        try:
            score = int(float(v))
        except (TypeError, ValueError):
            continue
        score = max(0, min(score, 100))
        idx = min(score // 20, 4)
        counts[idx] += 1
    return dict(zip(labels, counts))


async def chs_distribution_sql(
    from_: datetime | None = None,
    to_: datetime | None = None,
) -> dict[str, int]:
    key = f"chs_distribution_sql:{_filter_key(from_, to_)}"
    return await _cached_call(
        key, _chs_distribution_sql_uncached, from_=from_, to_=to_
    )


# ---------------------------------------------------------------------------
# Spark-card surfaces (v2 dashboard)
# ---------------------------------------------------------------------------
#
# Each KPI card needs two extra signals on top of the headline scalar:
#   1. `delta_pct_vs_prior` — % change vs the same-length prior window. Drives
#      the Tremor BadgeDelta chip (auto-arrowed colored pct).
#   2. `sparkline` — daily-bucketed series for the Tremor SparkAreaChart slot.
#
# All helpers respect the WAF posture documented at the top of this module:
# single-statement SELECTs, no multi-aggregate, no ORDER BY/LIMIT, no IN(...).
# We pull rows + bucket in Python.


def _safe_pct_change(current: float | None, prior: float | None) -> float | None:
    """Symmetric pct-change helper. Returns None when prior is missing/zero so
    the dashboard can render an em-dash instead of a misleading ∞."""
    if current is None or prior is None:
        return None
    try:
        c = float(current)
        p = float(prior)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    return round((c - p) / p * 100, 2)


def _normalize_window(
    from_: datetime | None, to_: datetime | None, default_days: int = 30
) -> tuple[datetime, datetime]:
    """Normalize (from_, to_) into a closed UTC datetime range.

    Defaults to the trailing `default_days` window when either bound is missing.
    Used by the spark/prior helpers — they need a bounded window to compute the
    prior-period and the daily buckets deterministically.
    """
    now = datetime.now(timezone.utc)
    end = to_ or now
    start = from_ or (end - timedelta(days=default_days))
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start, end


def _date_buckets(start: datetime, end: datetime) -> list[str]:
    """Sorted list of ISO date strings for every day in [start, end]."""
    days: list[str] = []
    cur = start.date()
    last = end.date()
    while cur <= last:
        days.append(cur.isoformat())
        cur = cur + timedelta(days=1)
    return days


def _empty_sparkline(start: datetime, end: datetime) -> list[dict[str, Any]]:
    return [{"d": d, "v": 0} for d in _date_buckets(start, end)]


def _bucket_dt(value: Any) -> str | None:
    dt = _parse_dt(value)
    if dt is None:
        return None
    return dt.date().isoformat()


# ----- calls_log: count per day + prior-period delta -----

async def _calls_window_count(start: datetime, end: datetime) -> int:
    """Count calls_log rows whose created_at falls in [start, end].

    Pulls created_at column + filters in Python — keeps the SQL shape
    WAF-friendly (single SELECT, no BETWEEN with ISO literals which Cloudflare
    occasionally flags as a probe pattern).
    """
    rows = await twin_client.query("SELECT created_at FROM calls_log")
    n = 0
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None:
            continue
        if start <= dt <= end:
            n += 1
    return n


async def calls_prior_period(
    from_: datetime | None, to_: datetime | None
) -> int:
    """Total calls in the same-length window immediately preceding [from_, to_]."""
    start, end = _normalize_window(from_, to_)
    span = end - start
    return await _calls_window_count(start - span, end - span)


async def calls_sparkline(
    from_: datetime | None, to_: datetime | None
) -> list[dict[str, Any]]:
    """Daily call count, bucketed by created_at::date over the window."""
    start, end = _normalize_window(from_, to_)
    rows = await twin_client.query("SELECT created_at FROM calls_log")
    counts: dict[str, int] = {d: 0 for d in _date_buckets(start, end)}
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < start or dt > end:
            continue
        key = dt.date().isoformat()
        if key in counts:
            counts[key] += 1
    return [{"d": d, "v": counts[d]} for d in counts]


# ----- bookings + revenue: prior-period + sparkline -----

async def _bookings_join_rows() -> list[dict[str, Any]]:
    """Single source for bookings × calls_log time series.

    Pulls one row per booking with `apply_rate` + the parent call's
    `created_at`. We use calls_log.created_at (not bookings.created_at) so
    the spark windows align with the call/funnel timeline. Per WAF rules:
    single SELECT, no aggregation.
    """
    return await twin_client.query(
        "SELECT b.apply_rate AS apply_rate, c.created_at AS created_at "
        "FROM bookings b JOIN calls_log c ON c.call_id = b.call_id"
    )


def _sum_apply_in_window(
    rows: list[dict[str, Any]], start: datetime, end: datetime
) -> float:
    total = 0.0
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < start or dt > end:
            continue
        v = _to_float(r.get("apply_rate"))
        if v is None:
            continue
        total += v
    return round(total, 2)


async def revenue_prior_period(
    from_: datetime | None, to_: datetime | None
) -> float:
    start, end = _normalize_window(from_, to_)
    span = end - start
    rows = await _bookings_join_rows()
    return _sum_apply_in_window(rows, start - span, end - span)


async def revenue_sparkline(
    from_: datetime | None, to_: datetime | None
) -> list[dict[str, Any]]:
    """Daily revenue (SUM(apply_rate)) bucketed by parent call's created_at."""
    start, end = _normalize_window(from_, to_)
    rows = await _bookings_join_rows()
    buckets: dict[str, float] = {d: 0.0 for d in _date_buckets(start, end)}
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < start or dt > end:
            continue
        v = _to_float(r.get("apply_rate"))
        if v is None:
            continue
        key = dt.date().isoformat()
        if key in buckets:
            buckets[key] += v
    return [{"d": d, "v": round(buckets[d], 2)} for d in buckets]


# ----- operational (avg duration) prior-period + sparkline -----

async def duration_prior_period(
    from_: datetime | None, to_: datetime | None
) -> float | None:
    start, end = _normalize_window(from_, to_)
    span = end - start
    rows = await twin_client.query(
        "SELECT created_at, duration_seconds FROM calls_log"
    )
    vals: list[float] = []
    p_start, p_end = start - span, end - span
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < p_start or dt > p_end:
            continue
        v = _to_float(r.get("duration_seconds"))
        if v is None:
            continue
        vals.append(v)
    return round(sum(vals) / len(vals), 2) if vals else None


async def duration_sparkline(
    from_: datetime | None, to_: datetime | None
) -> list[dict[str, Any]]:
    """Daily mean call duration."""
    start, end = _normalize_window(from_, to_)
    rows = await twin_client.query(
        "SELECT created_at, duration_seconds FROM calls_log"
    )
    sums: dict[str, float] = {d: 0.0 for d in _date_buckets(start, end)}
    counts: dict[str, int] = {d: 0 for d in _date_buckets(start, end)}
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < start or dt > end:
            continue
        v = _to_float(r.get("duration_seconds"))
        if v is None:
            continue
        key = dt.date().isoformat()
        if key in sums:
            sums[key] += v
            counts[key] += 1
    return [
        {"d": d, "v": round(sums[d] / counts[d], 2) if counts[d] else 0.0}
        for d in sums
    ]


# ----- quality (avg CHS) prior-period + sparkline -----

async def chs_prior_period(
    from_: datetime | None, to_: datetime | None
) -> float | None:
    start, end = _normalize_window(from_, to_)
    span = end - start
    rows = await twin_client.query(
        "SELECT created_at, case_health_score FROM calls_log"
    )
    vals: list[float] = []
    p_start, p_end = start - span, end - span
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < p_start or dt > p_end:
            continue
        v = _to_float(r.get("case_health_score"))
        if v is None:
            continue
        vals.append(v)
    return round(sum(vals) / len(vals), 2) if vals else None


async def chs_sparkline(
    from_: datetime | None, to_: datetime | None
) -> list[dict[str, Any]]:
    """Daily mean CHS over the window."""
    start, end = _normalize_window(from_, to_)
    rows = await twin_client.query(
        "SELECT created_at, case_health_score FROM calls_log"
    )
    sums: dict[str, float] = {d: 0.0 for d in _date_buckets(start, end)}
    counts: dict[str, int] = {d: 0 for d in _date_buckets(start, end)}
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < start or dt > end:
            continue
        v = _to_float(r.get("case_health_score"))
        if v is None:
            continue
        key = dt.date().isoformat()
        if key in sums:
            sums[key] += v
            counts[key] += 1
    return [
        {"d": d, "v": round(sums[d] / counts[d], 2) if counts[d] else 0.0}
        for d in sums
    ]


# ----- effective rate delta time-series (hero chart) -----

async def effective_delta_series(
    from_: datetime | None, to_: datetime | None
) -> list[dict[str, Any]]:
    """Daily mean of (apply_rate - loadboard_rate) for booked loads.

    Joins bookings + loads + calls_log so each row carries
    {created_at, apply_rate, loadboard_rate}; bucketed by date and meaned in
    Python (per WAF rules). Returns one entry per day in [from_, to_]:
        {"d": "YYYY-MM-DD", "v": float | null, "n": int}

    `v=None` for days with no bookings — the chart suppresses null points
    rather than collapsing them to zero (which would misread as "we broke
    even" instead of "no data").
    """
    start, end = _normalize_window(from_, to_)
    rows = await twin_client.query(
        "SELECT b.apply_rate AS apply_rate, "
        "l.loadboard_rate AS loadboard_rate, "
        "c.created_at AS created_at "
        "FROM bookings b "
        "JOIN loads l ON l.load_id = b.load_id "
        "JOIN calls_log c ON c.call_id = b.call_id"
    )
    sums: dict[str, float] = {d: 0.0 for d in _date_buckets(start, end)}
    counts: dict[str, int] = {d: 0 for d in _date_buckets(start, end)}
    for r in rows:
        dt = _parse_dt(r.get("created_at"))
        if dt is None or dt < start or dt > end:
            continue
        agreed = _to_float(r.get("apply_rate"))
        listed = _to_float(r.get("loadboard_rate"))
        if agreed is None or listed is None:
            continue
        # Sign convention: agreed - loadboard.
        # Negative = below list (broker captured margin).
        # Positive = above list (concession).
        delta = agreed - listed
        key = dt.date().isoformat()
        if key in sums:
            sums[key] += delta
            counts[key] += 1
    out: list[dict[str, Any]] = []
    for d in sums:
        n = counts[d]
        out.append(
            {
                "d": d,
                "v": round(sums[d] / n, 2) if n else None,
                "n": n,
            }
        )
    return out
