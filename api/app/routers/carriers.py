"""Carrier rollup endpoints — per-MC aggregations across calls_log + bookings.

  GET /v1/carriers/{mc_number}   — single carrier rollup (404 on zero calls)
  GET /v1/carriers?limit=N       — list rollup (top N carriers by call_count)

Each rollup returns:
  mc_number, total_calls, total_bookings, conversion_rate (bookings / calls),
  avg_apply_rate, last_call_at,
  sentiment_breakdown { positive, neutral, negative },
  outcome_breakdown   { load_booked, carrier_not_qualified, call_abandoned,
                        non_load_booking_engagement }

Twin SQL constraints (per ADR-004 / dashboard_aggregations.py):
  - Single-statement queries only (Cloudflare WAF).
  - Avoid IN-lists / JSONB ops.
  - `:placeholder` quoted-literal interpolation via twin_client.query.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import require_api_key
from app.services.twin_client import twin_client

router = APIRouter(prefix="/v1/carriers", tags=["carriers"])


_OUTCOME_KEYS = (
    "load_booked",
    "carrier_not_qualified",
    "call_abandoned",
    "non_load_booking_engagement",
)
_SENTIMENT_KEYS = ("positive", "neutral", "negative")


def _to_int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _empty_outcome_breakdown() -> dict[str, int]:
    return {k: 0 for k in _OUTCOME_KEYS}


def _empty_sentiment_breakdown() -> dict[str, int]:
    return {k: 0 for k in _SENTIMENT_KEYS}


async def _carrier_stats(mc_number: str) -> dict[str, Any] | None:
    """Build a single-MC rollup. Returns None when the MC has zero calls."""
    base_rows = await twin_client.query(
        "SELECT COUNT(*) AS total_calls, MAX(created_at) AS last_call_at "
        "FROM calls_log WHERE mc_number = :mc_number",
        {"mc_number": str(mc_number)},
    )
    if not base_rows:
        return None
    total_calls = _to_int(base_rows[0].get("total_calls"))
    if total_calls == 0:
        return None
    last_call_at = base_rows[0].get("last_call_at")

    booking_rows = await twin_client.query(
        "SELECT COUNT(*) AS total_bookings, AVG(apply_rate) AS avg_apply_rate "
        "FROM bookings WHERE mc_number = :mc_number",
        {"mc_number": str(mc_number)},
    )
    total_bookings = _to_int(booking_rows[0].get("total_bookings")) if booking_rows else 0
    avg_apply_rate = _to_float(booking_rows[0].get("avg_apply_rate")) if booking_rows else None

    outcome_rows = await twin_client.query(
        "SELECT call_outcome, COUNT(*) AS n FROM calls_log "
        "WHERE mc_number = :mc_number GROUP BY call_outcome",
        {"mc_number": str(mc_number)},
    )
    outcome_breakdown = _empty_outcome_breakdown()
    for r in outcome_rows:
        key = r.get("call_outcome")
        if key in outcome_breakdown:
            outcome_breakdown[str(key)] = _to_int(r.get("n"))

    sentiment_rows = await twin_client.query(
        "SELECT sentiment, COUNT(*) AS n FROM calls_log "
        "WHERE mc_number = :mc_number AND sentiment IS NOT NULL "
        "GROUP BY sentiment",
        {"mc_number": str(mc_number)},
    )
    sentiment_breakdown = _empty_sentiment_breakdown()
    for r in sentiment_rows:
        key = r.get("sentiment")
        if key in sentiment_breakdown:
            sentiment_breakdown[str(key)] = _to_int(r.get("n"))

    conversion_rate = round(total_bookings / total_calls, 4) if total_calls else 0.0

    return {
        "mc_number": mc_number,
        "total_calls": total_calls,
        "total_bookings": total_bookings,
        "conversion_rate": conversion_rate,
        "avg_apply_rate": (round(avg_apply_rate, 2) if avg_apply_rate is not None else None),
        "last_call_at": last_call_at,
        "sentiment_breakdown": sentiment_breakdown,
        "outcome_breakdown": outcome_breakdown,
    }


@router.get("/{mc_number}", dependencies=[Depends(require_api_key)])
async def get_carrier(mc_number: str) -> dict[str, Any]:
    stats = await _carrier_stats(mc_number)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Carrier MC {mc_number} not found")
    return stats


@router.get("", dependencies=[Depends(require_api_key)])
async def list_carriers(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """List top-N carriers by call_count, each with the same rollup shape.

    Cloudflare WAF blocks `GROUP BY ... ORDER BY ... LIMIT` — pull mc_number rows
    plain, count + sort + slice in Python. Twin payload is small (1 row per call).
    """
    rows = await twin_client.query(
        "SELECT mc_number FROM calls_log WHERE mc_number IS NOT NULL"
    )
    counts: Counter[str] = Counter(
        str(r["mc_number"]) for r in rows if r.get("mc_number")
    )
    top_mcs = [mc for mc, _ in counts.most_common(int(limit))]

    carriers: list[dict[str, Any]] = []
    for mc in top_mcs:
        stats = await _carrier_stats(mc)
        if stats is not None:
            carriers.append(stats)
    return {"carriers": carriers, "count": len(carriers)}
