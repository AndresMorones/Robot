"""Active-call indicator endpoint — proxies HR Monitor API.

Webhook is end-of-call only; this endpoint provides in-flight visibility for
the dashboard's live indicator. Polls HR's `/workflows/{wf}/runs?status=running`
through a single global TTLCache (10s) so N dashboard tabs cost at most 1 HR
call per 10s.

Auth: Bearer / x-api-key (same as other /v1/* endpoints).

States in response:
  - status="ok"             — query succeeded; runs[] reflects HR's view
  - status="unconfigured"   — HR_WORKFLOW_ID not set (dev / pre-deploy state)
  - status="error"          — HR returned non-2xx or transport error; UI
                              renders amber dot + "Status unknown"

See `docs/dashboard-v2-research/04-engineering-feasibility.md` §2.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog
from cachetools import TTLCache
from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import require_api_key

log = structlog.get_logger()

# Single global cache; TTL=10s caps HR ingress at ~8.6k calls/day.
_active_cache: TTLCache = TTLCache(maxsize=1, ttl=10)
_lock = asyncio.Lock()

router = APIRouter(prefix="/v1/calls", tags=["calls-active"])


@router.get("/active", dependencies=[Depends(require_api_key)])
async def active_calls() -> dict[str, Any]:
    async with _lock:
        if "v" in _active_cache:
            return _active_cache["v"]

    if not settings.hr_workflow_id:
        return {"count": 0, "runs": [], "status": "unconfigured"}

    try:
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
        rows = data.get("data") or data.get("runs") or []
        runs = [
            {
                "run_id": r.get("id"),
                "started_at": r.get("started_at") or r.get("created_at"),
                "duration_seconds": r.get("duration_seconds"),
                "current_node": (r.get("current_node") or {}).get("name"),
                "mc_number": (r.get("inputs") or {}).get("mc_number"),
            }
            for r in rows
        ]
        out: dict[str, Any] = {"count": len(runs), "runs": runs, "status": "ok"}
    except Exception as e:  # noqa: BLE001 — transport/JSON shape unverified
        log.warning("active_calls_query_failed", error_type=type(e).__name__)
        out = {
            "count": 0,
            "runs": [],
            "status": "error",
            "error": str(e)[:100],
        }

    async with _lock:
        _active_cache["v"] = out
    return out
