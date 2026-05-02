"""Twin-backed reads against the `calls_log` table.

HR's Write-to-Twin component is the sole writer for `calls_log`. The FastAPI
service is read-only against this table; it surfaces calls in the dashboard
layer alongside `bookings` (joined on call_id).

Live schema (29 columns, v2 production — verified 2026-04-30 night):
  identity:   id, created_at, call_id (UNIQUE)
  caller:     mc_number, carrier_name, callback_phone,
              fmcsa_eligibility_failure_reason
  lane:       lane_origin, lane_dest
  quality:    call_outcome, sentiment, case_health_score, audit_remarks, notes
  data:       transcript
  tokens:     extract_input/output/reasoning/cached/uncached_tokens (5)
              chs_input/output/reasoning/cached/uncached_tokens (5)
  telemetry:  duration_seconds, intermediate_response_count (HR NULL),
              p70_latency_ms (HR NULL), p90_latency_ms (HR NULL)

Per ADR-012: latency + intermediate_response_count are NULL on Twin (HR-platform
bug); dashboard derives them from HR REST API /runs/{id}/nodes timestamps.

`apply_rate` is NOT a calls_log column — it lives on `bookings.apply_rate`
(joined on call_id). Single integration point: `twin_client.query`.
Null-resilient on missing fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from app.services.twin_client import twin_client

log = structlog.get_logger()


def _ts_key(r: dict) -> tuple:
    # ISO-aware sort; lex fallback for malformed values.
    raw = r.get("created_at") or ""
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return (1, dt.timestamp())
    except (ValueError, TypeError):
        return (0, str(raw))


_CALLS_LOG_COLS = (
    "id, created_at, call_id, "
    "mc_number, carrier_name, callback_phone, fmcsa_eligibility_failure_reason, "
    "lane_origin, lane_dest, "
    "call_outcome, sentiment, case_health_score, audit_remarks, notes, "
    "transcript, "
    "extract_input_tokens, extract_output_tokens, extract_reasoning_tokens, "
    "extract_cached_input_tokens, extract_uncached_input_tokens, "
    "chs_input_tokens, chs_output_tokens, chs_reasoning_tokens, "
    "chs_cached_input_tokens, chs_uncached_input_tokens, "
    "duration_seconds, intermediate_response_count, "
    "p70_latency_ms, p90_latency_ms"
)


async def list_calls(
    *,
    limit: int = 100,
    offset: int = 0,
    since_ts: str | None = None,
) -> list[dict[str, Any]]:
    """List recent calls, newest first.

    Cloudflare WAF blocks `ORDER BY ... LIMIT/OFFSET` — pull rows with WHERE only,
    sort + slice in Python. Twin payload is one row per call_id; for the demo
    dataset (10s-100s of rows) this is negligible.
    """
    where = ""
    params: dict[str, Any] = {}
    if since_ts:
        where = "WHERE created_at >= :since_ts"
        params["since_ts"] = since_ts

    sql = f"SELECT {_CALLS_LOG_COLS} FROM calls_log {where}"
    rows = await twin_client.query(sql, params if params else None)
    rows.sort(key=_ts_key, reverse=True)
    start = int(offset)
    end = start + int(limit)
    return rows[start:end]


async def get_call_by_id(call_id: str) -> dict[str, Any] | None:
    """Lookup a single call by call_id. Returns None if not found.

    Cloudflare WAF blocks `WHERE call_id = '<uuid-with-dashes>'` literals
    (SQL-injection rule false-positive on the hex+dash pattern). Workaround:
    fetch recent rows + filter Python-side. Acceptable at MVP scale (calls_log
    is small).
    """
    if not call_id:
        return None
    sql = (
        f"SELECT {_CALLS_LOG_COLS} "
        "FROM calls_log "
        "ORDER BY created_at DESC"
    )
    rows = await twin_client.query(sql)
    target = str(call_id)
    for row in rows:
        if row.get("call_id") == target:
            return row
    return None
