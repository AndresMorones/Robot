"""Transcript-derived telemetry aggregator.

Replaces the HR `/runs` REST API path. Iterates `calls_log` rows in a window,
parses each `transcript` JSON via `transcript_parser.parse_transcript`, and
pools per-tool durations + token counts for `/v1/dashboard/telemetry`.

Single public coroutine: `aggregate_telemetry_from_transcripts(...)`.
Returns the legacy shape MINUS the Extract / Case Health node widgets (those
required HR run-node introspection — gone with `run_details` +
`transcript_telemetry`). Token estimation prefers `tiktoken` (`o200k_base`),
falling back to `len // 4` when import fails.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from app.services.calls_store import list_calls
from app.services.dashboard_aggregations import _cached_call, _within_window
from app.services.token_counting import count_role_tokens
from app.services.transcript_parser import _iso_to_unix_ms, parse_transcript

log = structlog.get_logger()


# ---------------------------------------------------------------- helpers
def _parse_dt(value: Any) -> datetime | None:
    """ISO-with-Z + Postgres `2026-04-30 14:23:11+00` tolerant."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _latency_percentiles(latencies_ms: list[float]) -> dict[str, float | None]:
    if not latencies_ms:
        return {"p50": None, "p70": None, "p90": None, "p99": None}
    s = sorted(float(v) for v in latencies_ms)
    if len(s) == 1:
        return {"p50": s[0], "p70": s[0], "p90": s[0], "p99": s[0]}

    def pct(p: float) -> float:
        k = (len(s) - 1) * (p / 100.0)
        lo = int(k)
        hi = min(lo + 1, len(s) - 1)
        return s[lo] + (s[hi] - s[lo]) * (k - lo)

    return {"p50": pct(50), "p70": pct(70), "p90": pct(90), "p99": pct(99)}


def _coerce_transcript(raw: Any) -> list[dict] | None:
    """Twin returns transcript as JSON string; legacy paths may already be
    list. Anything malformed → None so the caller skips the row."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            decoded = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        return decoded if isinstance(decoded, list) else None
    return None


def _tool_call_durations_ms(events: list[dict]) -> list[tuple[str | None, float]]:
    """Per-tool durations, ms.

    The transcript shape gives us only two timestamps: assistant turns carry
    UUIDv7 wall-clocks; user turns carry start/end offsets anchored to the
    first assistant. Tool turns have NEITHER. So tool latency is estimated as
    the gap from an `assistant_tool_call`'s wall-clock to the NEXT assistant
    turn's wall-clock — i.e. the agent's roundtrip after issuing the tool
    until it spoke again with the result. That includes tool execution + the
    LLM's follow-up generation time, which is the correct operator-facing
    "tool latency" signal for this stack.
    """
    # Pre-collect assistant wall_clocks indexed by event position, so we can
    # find the "next assistant after position i" cheaply.
    assistant_ts_by_idx: dict[int, int] = {}
    for i, e in enumerate(events):
        kind = e.get("kind")
        if kind in ("assistant_message", "assistant_tool_call"):
            wc = e.get("wall_clock")
            if wc:
                ms = _iso_to_unix_ms(wc)
                if ms is not None:
                    assistant_ts_by_idx[i] = ms

    sorted_assistant_idxs = sorted(assistant_ts_by_idx)

    def _next_assistant_after(i: int) -> int | None:
        for j in sorted_assistant_idxs:
            if j > i:
                return assistant_ts_by_idx[j]
        return None

    durations: list[tuple[str | None, float]] = []
    for i, e in enumerate(events):
        if e.get("kind") != "assistant_tool_call":
            continue
        a_ts = assistant_ts_by_idx.get(i)
        if a_ts is None:
            continue
        next_ts = _next_assistant_after(i)
        if next_ts is None:
            continue
        # Each tool_call in this assistant turn shares the same a_ts → next_ts
        # gap; record one (tool_name, duration) tuple per tool_call so the
        # percentile sample size reflects total tool invocations.
        gap = float(max(0, next_ts - a_ts))
        tool_calls = e.get("tool_calls") or [None]
        for tc in tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else None
            durations.append((name, gap))
    return durations


def _bucket_floor(dt: datetime, bucket_minutes: int) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    minute = (dt.minute // bucket_minutes) * bucket_minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def _fill_continuous(
    buckets: dict[datetime, int], bucket_minutes: int, key: str
) -> list[dict[str, Any]]:
    """Continuous-axis series from `buckets`. Empty intermediates → 0. Values
    are normalized to per-minute rates (divide by bucket_minutes)."""
    if not buckets:
        return []
    start, end = min(buckets), max(buckets)
    step = timedelta(minutes=bucket_minutes)
    out: list[dict[str, Any]] = []
    cur = start
    while cur <= end:
        rate = float(buckets.get(cur, 0)) / float(bucket_minutes)
        out.append({"t": cur.isoformat(), key: rate})
        cur = cur + step
    return out


def _normalize_window(
    from_: datetime | None, to_: datetime | None, default_days: int = 30
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end = to_ or now
    start = from_ or (end - timedelta(days=default_days))
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start, end


# ---------------------------------------------------------------- public
async def _aggregate_uncached(
    from_: datetime | None,
    to_: datetime | None,
    max_runs: int,
    bucket_minutes: int,
) -> dict[str, Any]:
    if bucket_minutes <= 0:
        raise ValueError("bucket_minutes must be > 0")

    window_from, window_to = _normalize_window(from_, to_)

    # WAF blocks created_at filters — pull broadly + filter Python-side.
    raw_rows = await list_calls(limit=500)
    in_window = [r for r in raw_rows if _within_window(r, window_from, window_to)][:max_runs]

    pooled_durations: list[float] = []
    rpm_buckets: dict[datetime, int] = defaultdict(int)
    tpm_buckets: dict[datetime, int] = defaultdict(int)
    # Per-bucket latency samples, global pool. Used by the chart's "All tools"
    # default view + headline aggregate.
    latency_buckets: dict[datetime, list[float]] = defaultdict(list)
    # Per-tool pool + per-(tool, bucket) breakdown. Used by the dashboard tool
    # filter + the active-alerts widget so threshold breaches can name the
    # offending tool. UNKNOWN_TOOL captures gaps where the parser couldn't
    # resolve a tool_name (defensive).
    pool_by_tool: dict[str, list[float]] = defaultdict(list)
    bucket_by_tool: dict[str, dict[datetime, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    runs_count = 0

    for row in in_window:
        transcript = _coerce_transcript(row.get("transcript"))
        if transcript is None:
            continue
        try:
            parsed = parse_transcript(transcript)
        except Exception as e:  # noqa: BLE001
            log.warning(
                "transcript_aggregations.parse_failed",
                call_id=row.get("call_id"),
                error=str(e),
            )
            continue

        events = parsed.get("events") or []
        runs_count += 1
        call_durations = _tool_call_durations_ms(events)
        pooled_durations.extend(d for _, d in call_durations)

        # Bucket by call start: parser's UUIDv7-derived `call_started_at` is
        # the canonical clock; fall back to row's `created_at`.
        bucket_dt = _parse_dt(parsed.get("call_started_at")) or _parse_dt(
            row.get("created_at")
        )
        if bucket_dt is None:
            continue
        b = _bucket_floor(bucket_dt, bucket_minutes)
        # RPM = carrier turns / minute (each user_message is a request to the
        # agent). TPM = total tokens (all 4 role-families summed) per minute,
        # using the same `count_role_tokens` helper that the call-detail page
        # consumes — so per-call values reconcile against the aggregate.
        user_turns = sum(1 for e in events if e.get("kind") == "user_message")
        role_tokens = count_role_tokens(events)
        rpm_buckets[b] += user_turns
        tpm_buckets[b] += sum(role_tokens.values())
        for tool_name, gap in call_durations:
            latency_buckets[b].append(gap)
            # Heal a known HR drift artifact: some forks emit `book_load_` with
            # a trailing underscore. Strip trailing `_` so historical rows roll
            # up under the canonical name (`book_load`) alongside future-fixed
            # rows. Affects only names that already end in `_` — no false
            # collisions in the current tool inventory.
            tn = (tool_name or "unknown").strip().rstrip("_") or "unknown"
            pool_by_tool[tn].append(gap)
            bucket_by_tool[tn][b].append(gap)

    pcts = _latency_percentiles(pooled_durations)
    sample_count = len(pooled_durations)

    def _series_from_buckets(
        buckets: dict[datetime, list[float]]
    ) -> list[dict[str, Any]]:
        if not buckets:
            return []
        s, e = min(buckets), max(buckets)
        step = timedelta(minutes=bucket_minutes)
        out: list[dict[str, Any]] = []
        cur = s
        while cur <= e:
            samples = buckets.get(cur, [])
            point: dict[str, Any] = {"t": cur.isoformat(), "n": len(samples)}
            if samples:
                p = _latency_percentiles(samples)
                point.update(
                    {
                        "p50_ms": p["p50"],
                        "p70_ms": p["p70"],
                        "p90_ms": p["p90"],
                        "p99_ms": p["p99"],
                    }
                )
            else:
                point.update({"p50_ms": None, "p70_ms": None, "p90_ms": None, "p99_ms": None})
            out.append(point)
            cur = cur + step
        return out

    latency_series = _series_from_buckets(latency_buckets)
    latency_by_tool: dict[str, dict[str, Any]] = {}
    for tool_name, samples in pool_by_tool.items():
        tp = _latency_percentiles(samples)
        latency_by_tool[tool_name] = {
            "sample_count": len(samples),
            "p50_ms": tp["p50"],
            "p70_ms": tp["p70"],
            "p90_ms": tp["p90"],
            "p99_ms": tp["p99"],
            "series": _series_from_buckets(bucket_by_tool[tool_name]),
        }

    log.info(
        "transcript_aggregations.aggregated",
        runs_count=runs_count,
        sample_count=sample_count,
        window_from=window_from.isoformat(),
        window_to=window_to.isoformat(),
    )

    return {
        "window": {
            "from": window_from.isoformat(),
            "to": window_to.isoformat(),
            "bucket_minutes": bucket_minutes,
        },
        "totals": {"runs": runs_count, "node_samples": sample_count},
        "rpm_series": _fill_continuous(rpm_buckets, bucket_minutes, "rpm"),
        "tpm_series": _fill_continuous(tpm_buckets, bucket_minutes, "tpm"),
        "latency": {
            "phase": "phase2",
            "source": "transcript",
            "sample_count": sample_count,
            "p50_ms": pcts["p50"],
            "p70_ms": pcts["p70"],
            "p90_ms": pcts["p90"],
            "p99_ms": pcts["p99"],
        },
        "latency_series": latency_series,
        "latency_by_tool": latency_by_tool,
    }


async def aggregate_telemetry_from_transcripts(
    from_: datetime | None = None,
    to_: datetime | None = None,
    max_runs: int = 200,
    bucket_minutes: int = 1,
) -> dict[str, Any]:
    """Aggregate per-call transcript-derived telemetry across `[from_, to_]`.

    `node_samples` = pooled per-tool durations across every call (denominator
    behind latency percentiles). `runs` = calls whose transcript parsed
    successfully. Malformed transcripts are skipped + logged at WARNING;
    aggregation continues across the rest.

    Returns the dashboard's telemetry shape — see module docstring for details.
    """
    from_iso = from_.isoformat() if from_ else "none"
    until_iso = to_.isoformat() if to_ else "none"
    key = f"telemetry_v2:{from_iso}|{until_iso}|{bucket_minutes}|{max_runs}"
    return await _cached_call(
        key, _aggregate_uncached, from_, to_, max_runs, bucket_minutes
    )


__all__ = ["aggregate_telemetry_from_transcripts"]
