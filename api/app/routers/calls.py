"""Calls endpoints — read-only views into Twin's `calls_log` + `bookings` tables.

Architecture pivot: HR's Write-to-Twin component owns all call-log writes (both
the post-call `calls_log` row and any mid-call `bookings` rows). FastAPI is
read-only here — POST returns 410 Gone for legacy callers.

GET endpoints feed the dashboard's calls list + drill-down view:
  GET /v1/calls?limit=N          — recent calls (no transcript)
  GET /v1/calls/{call_id}        — single call + bookings + load lane info
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import require_api_key
from app.services.bookings_store import bookings_for_call
from app.services.calls_store import get_call_by_id
from app.services.dashboard_aggregations import _within_window
from app.services.twin_client import twin_client

router = APIRouter(tags=["calls"])


# ---------------------------------------------------------- deprecated POST
#
# Kept mounted so any HR workflow still pointing at the old endpoint gets a
# clear 410 Gone with a recovery hint instead of a silent 404.

@router.post("/calls", status_code=status.HTTP_410_GONE)
@router.post("/v1/calls/log", status_code=status.HTTP_410_GONE)
def post_call_deprecated() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "POST /v1/calls/log deprecated; "
            "use HR Write-to-Twin to populate calls_log + bookings."
        ),
    )


# ---------------------------------------------------------- list endpoint
#
# Excludes `transcript` (potentially large) — fetch via the by-id endpoint.

_LIST_COLS = (
    "id, created_at, call_id, mc_number, call_outcome, "
    "sentiment, case_health_score, audit_remarks, "
    "fmcsa_eligibility_failure_reason, callback_phone, duration_seconds"
)


@router.get("/v1/calls", dependencies=[Depends(require_api_key)])
async def list_calls_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to_: Annotated[datetime | None, Query(alias="to")] = None,
) -> dict[str, Any]:
    """Recent calls, newest first. Transcript omitted — see GET /v1/calls/{call_id}.

    Optional `from`/`to` (ISO-8601) narrow the result to calls whose
    `created_at` falls in the window. The Cloudflare WAF in front of HR Twin
    blocks all `created_at` comparisons in SQL, so when bounds are supplied we
    pull a wider candidate set and filter Python-side via `_within_window`
    (the canonical pattern used by `dashboard_aggregations`). When no bounds
    are passed the original LIMIT-only fast path is preserved verbatim so the
    pre-filter behavior + tests stay identical.
    """
    if from_ is None and to_ is None:
        sql = (
            f"SELECT {_LIST_COLS} "
            "FROM calls_log "
            "ORDER BY created_at DESC "
            "LIMIT :limit"
        )
        rows = await twin_client.query(sql, {"limit": int(limit)})
        return {"calls": rows, "count": len(rows)}

    # Filtered path: pull a wider window (LIMIT * 5, capped at 500) so that
    # filtering doesn't starve the result when the most recent N calls fell
    # outside the requested window. WAF-safe single-statement SELECT.
    pull_cap = max(int(limit) * 5, 100)
    if pull_cap > 500:
        pull_cap = 500
    sql = (
        f"SELECT {_LIST_COLS} "
        "FROM calls_log "
        "ORDER BY created_at DESC "
        "LIMIT :limit"
    )
    rows = await twin_client.query(sql, {"limit": pull_cap})
    filtered = [r for r in rows if _within_window(r, from_, to_)][: int(limit)]
    return {"calls": filtered, "count": len(filtered)}


# ---------------------------------------------------------- by-id endpoint

@router.get("/v1/calls/{call_id}", dependencies=[Depends(require_api_key)])
async def get_call_endpoint(
    call_id: str,
    include_transcript: bool = Query(
        default=False,
        description=(
            "Set to true to include the full transcript in the response. "
            "Default false — defense-in-depth so a leaked Bearer token cannot "
            "casually exfiltrate every transcript via the standard endpoint."
        ),
    ),
) -> dict[str, Any]:
    """Single call + its bookings + per-booking load lane info.

    The full transcript is opt-in (`?include_transcript=true`). Default is the
    metadata-only view — Bearer auth alone never returns transcript bytes.
    """
    call = await get_call_by_id(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    if not include_transcript and isinstance(call, dict) and "transcript" in call:
        # Drop the transcript field entirely — caller must explicitly opt in.
        call = {k: v for k, v in call.items() if k != "transcript"}

    bookings = await bookings_for_call(call_id)

    # Enrich each booking with load lane info. One query per load_id keeps SQL
    # single-statement (Twin / Cloudflare WAF constraint) — bookings per call
    # are small (1-3 typical) so N+1 is acceptable here.
    enriched: list[dict[str, Any]] = []
    for b in bookings:
        load_info: dict[str, Any] | None = None
        load_id = b.get("load_id")
        if load_id:
            # No LIMIT — WAF blocks SELECT...LIMIT. load_id is unique so
            # WHERE returns at most one row. Full lane projection so the
            # dashboard drill-down can render every spec field without a
            # second round-trip.
            load_rows = await twin_client.query(
                "SELECT load_id, origin_city, origin_state, destination_city, "
                "destination_state, equipment_type, loadboard_rate, miles, "
                "weight, commodity_type, num_of_pieces, dimensions, "
                "pickup_datetime, delivery_datetime, notes "
                "FROM loads WHERE load_id = :load_id",
                {"load_id": str(load_id)},
            )
            load_info = load_rows[0] if load_rows else None
        enriched.append({**b, "load": load_info})

    return {"call": call, "bookings": enriched}
