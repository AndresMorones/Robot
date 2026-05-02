"""Twin-backed reads against the `bookings` table.

Schema (per data/twin_schema_v15_bookings.sql):
  id          BIGSERIAL PRIMARY KEY
  created_at  TIMESTAMPTZ DEFAULT NOW()
  call_id     TEXT NOT NULL
  mc_number   TEXT NOT NULL
  load_id     TEXT NOT NULL
  apply_rate  DOUBLE PRECISION NOT NULL
  UNIQUE (call_id, load_id)

All writes happen HR-side via the Write-to-Twin component. This module is read-only.
Single integration point: `twin_client.query`. Null-resilient on missing fields so a
schema drift (column rename / column add) doesn't crash the dashboard.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.services.dashboard_aggregations import _parse_dt, _to_float as _coerce_float
from app.services.twin_client import twin_client

log = structlog.get_logger()


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    """Coerce types we care about; pass other columns through unchanged."""
    return {
        "id": row.get("id"),
        "created_at": row.get("created_at"),
        "call_id": row.get("call_id"),
        "mc_number": row.get("mc_number"),
        "load_id": row.get("load_id"),
        "apply_rate": _coerce_float(row.get("apply_rate")),
    }


async def list_bookings(
    *,
    limit: int = 100,
    offset: int = 0,
    since_ts: str | None = None,
) -> list[dict[str, Any]]:
    """List recent bookings, newest first.

    `since_ts` is an ISO-8601 timestamp; rows older than this are excluded.
    """
    where = ""
    params: dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
    if since_ts:
        where = "WHERE created_at >= :since_ts"
        params["since_ts"] = since_ts

    sql = (
        "SELECT id, created_at, call_id, mc_number, load_id, apply_rate "
        f"FROM bookings {where} "
        "ORDER BY created_at DESC "
        "LIMIT :limit OFFSET :offset"
    )
    rows = await twin_client.query(sql, params)
    return [_normalize(r) for r in rows]


async def bookings_by_mc(mc_number: str, *, limit: int = 100) -> list[dict[str, Any]]:
    """All bookings for a single MC number, newest first."""
    if not mc_number:
        return []
    sql = (
        "SELECT id, created_at, call_id, mc_number, load_id, apply_rate "
        "FROM bookings "
        "WHERE mc_number = :mc_number "
        "ORDER BY created_at DESC "
        "LIMIT :limit"
    )
    rows = await twin_client.query(
        sql,
        {"mc_number": str(mc_number), "limit": int(limit)},
    )
    return [_normalize(r) for r in rows]


async def recent_bookings_window(
    *,
    since_ts: str,
    until_ts: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Bookings whose `created_at` falls in [since_ts, until_ts], newest first.

    WAF blocks every `created_at` comparison (Cloudflare rule, see
    `dashboard_aggregations.date_range_clause` docstring). Workaround: pull
    all rows, filter + sort in Python. Bookings table is small at MVP scale.

    Both `since_ts` and `until_ts` are ISO-8601 strings. Twin returns
    `created_at` in Postgres `timestamptz` repr (e.g. ``2026-04-30 14:23:11+00``)
    while the dashboard sends ``2026-04-30T00:00:00.000Z`` — naive string
    compare fails because ``" "`` (chr 32) sorts before ``"T"`` (chr 84). We
    parse both sides into aware datetimes and compare the values directly,
    which is the same approach `dashboard_aggregations._within_window` takes.
    """
    if not since_ts:
        return []
    sql = (
        "SELECT id, created_at, call_id, mc_number, load_id, apply_rate "
        "FROM bookings"
    )
    rows = await twin_client.query(sql)
    lower = _parse_dt(since_ts)
    upper = _parse_dt(until_ts) if until_ts else None

    def _row_dt(r: dict[str, Any]):
        return _parse_dt(r.get("created_at"))

    filtered: list[dict[str, Any]] = []
    for r in rows:
        ca = _row_dt(r)
        if ca is None:
            continue
        if lower is not None and ca < lower:
            continue
        if upper is not None and ca > upper:
            continue
        filtered.append(r)

    filtered.sort(
        key=lambda r: _row_dt(r) or _parse_dt("1970-01-01T00:00:00Z"),
        reverse=True,
    )
    sliced = filtered[: int(limit)] if limit > 0 else filtered
    return [_normalize(r) for r in sliced]


async def all_booked_load_ids() -> set[str]:
    """Distinct load_id values across every booking row.

    WAF-safe: single SELECT, no DISTINCT (the WAF tolerates DISTINCT but we
    de-dupe in Python anyway since we already have to pull the rows). Returns
    a set so callers can cheaply membership-test.
    """
    rows = await twin_client.query("SELECT load_id FROM bookings")
    return {str(r.get("load_id")) for r in rows if r.get("load_id")}


async def bookings_for_call(call_id: str) -> list[dict[str, Any]]:
    """All bookings for a single call_id (a call can book multiple loads).

    WAF workaround: `WHERE call_id = '<uuid>'` triggers a Cloudflare SQL-injection
    rule on the hex+dash pattern. Fetch all rows + filter Python-side.
    Acceptable at MVP scale (bookings table is small).
    """
    if not call_id:
        return []
    sql = (
        "SELECT id, created_at, call_id, mc_number, load_id, apply_rate "
        "FROM bookings "
        "ORDER BY created_at ASC"
    )
    rows = await twin_client.query(sql)
    target = str(call_id)
    return [_normalize(r) for r in rows if r.get("call_id") == target]
