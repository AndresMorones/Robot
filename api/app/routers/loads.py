"""Load search endpoint (Bearer required)."""

from fastapi import APIRouter, Depends

from app.deps import require_bearer
from app.models import LoadSearchRequest, LoadSearchResponse
from app.services.load_store import load_store

router = APIRouter(tags=["loads"])


@router.post(
    "/loads/search",
    response_model=LoadSearchResponse,
    dependencies=[Depends(require_bearer)],
)
def search_loads(req: LoadSearchRequest) -> LoadSearchResponse:
    matches = load_store.search(req)
    return LoadSearchResponse(matches=matches, total_in_store=len(load_store.all()))
