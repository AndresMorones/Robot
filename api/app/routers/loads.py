"""Loads endpoints — match HR webhook expectations.

HR's voice agent has two tools that webhook to:
  GET /loads/search?origin=&destination=&equipment_type=   (search_loads_by_lane)
  GET /loads/{reference_number}                            (find_available_loads)

Both authenticate via `x-api-key` header (or Bearer; see app/deps.py).
Origin/destination are combined "City, State" strings; equipment_type is a
lowercase phrase ("dry van").

We expose every endpoint at TWO paths:
  - the legacy unprefixed path (`/loads/...`) which HR webhook URLs already
    point at — preserved for backwards compatibility, do not break HR.
  - the `/v1/loads/...` alias for consistency with every other endpoint
    (dashboard, calls, carriers) which sits under `/v1/`.

Route registration order matters: the `/search` paths are declared FIRST so
they aren't shadowed by the `/{reference_number}` path-parameter routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import require_api_key
from app.services.load_store import load_store

router = APIRouter(tags=["loads"])


def _search_payload(
    origin: str | None,
    destination: str | None,
    equipment_type: str | None,
    max_results: int,
) -> dict:
    matches = load_store.search(
        origin=origin,
        destination=destination,
        equipment_type=equipment_type,
        max_results=max_results,
    )
    return {
        "matches": [m.to_response_dict() for m in matches],
        "total_in_store": len(load_store.all()),
        "filters_applied": {
            "origin": origin,
            "destination": destination,
            "equipment_type": equipment_type,
        },
    }


def _get_payload(reference_number: str) -> dict:
    load = load_store.get(reference_number)
    if load is None:
        raise HTTPException(
            status_code=404,
            detail=f"Load {reference_number} not found",
        )
    return load.to_response_dict()


@router.get(
    "/loads/search",
    dependencies=[Depends(require_api_key)],
)
@router.get(
    "/v1/loads/search",
    dependencies=[Depends(require_api_key)],
)
def search_loads(
    origin: str | None = Query(default=None, description='City + state, e.g. "Dallas, TX"'),
    destination: str | None = Query(
        default=None, description='City + state, e.g. "Atlanta, GA". Optional.'
    ),
    equipment_type: str | None = Query(
        default=None, description='e.g. "dry van", "reefer", "flatbed". Optional.'
    ),
    max_results: int = Query(default=5, ge=1, le=20),
) -> dict:
    """Search loads by lane. Used by HR's `search_loads_by_lane`."""
    return _search_payload(origin, destination, equipment_type, max_results)


@router.get(
    "/loads/{reference_number}",
    dependencies=[Depends(require_api_key)],
)
@router.get(
    "/v1/loads/{reference_number}",
    dependencies=[Depends(require_api_key)],
)
def get_load(reference_number: str) -> dict:
    """Lookup a single load by reference number. Used by HR's `find_available_loads`."""
    return _get_payload(reference_number)
