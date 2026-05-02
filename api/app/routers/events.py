"""Push-pipeline endpoints for dashboard freshness (Option C).

Three endpoints under `/v1/events/...`:

  POST /v1/events/call-ended    — HR webhook receiver (Bearer-auth, idempotent)
  POST /v1/events/session       — mints a one-time session token for SSE
  GET  /v1/events/stream        — Server-Sent Events stream (session-auth via query)

Architecture (see ADR-009 + memory `project_dashboard_freshness_options.md`):

  HR call.ended → POST /v1/events/call-ended (Bearer)
    → idempotency check on call_id (5-min window)
    → invalidate_dashboard_cache()  (clears in-process TTLCache)
    → event_bus.publish({"type": "call.ended", ...})
    → SSE subscribers receive event
    → browsers call router.refresh() → re-fetch Server Component data
    → FastAPI cache cleared → re-queries Twin → returns latest data

The 5-minute ISR fallback in the dashboard catches any event that drops in
flight (network blip, Fly machine restart, slow consumer queue full).

Auth split:
  - POST endpoints use Bearer (called by HR or Next.js server-side)
  - GET /stream uses a one-time `session` query param because EventSource has
    no API to set custom headers; long-lived Bearer tokens must never appear
    in URLs (Fly access logs, browser history, referer). Session tokens are
    opaque + short-lived (60s TTL) + single-use, so log exposure is bounded.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.deps import require_api_key
from app.services import event_bus
from app.services.dashboard_aggregations import invalidate_dashboard_cache

log = structlog.get_logger()

router = APIRouter(tags=["events"])


# ---------------------------------------------------------- idempotency cache
#
# HR retries failed webhooks (defaults: 2 retries, 10s base, 2x backoff, 100s
# max) — without dedupe we'd invalidate the cache + fan out the event multiple
# times for the same call_id. 5-minute window comfortably exceeds HR's max
# retry envelope. Dict keys: call_id; values: insertion timestamp.

_IDEMPOTENCY_TTL_SECONDS = 300
_IDEMPOTENCY_MAX_ENTRIES = 1000

_seen_call_ids: dict[str, float] = {}


def _purge_expired_call_ids(now: float) -> None:
    """Drop expired entries; cap at MAX so a flood doesn't grow without bound."""
    cutoff = now - _IDEMPOTENCY_TTL_SECONDS
    expired = [k for k, ts in _seen_call_ids.items() if ts < cutoff]
    for k in expired:
        _seen_call_ids.pop(k, None)
    # Hard cap: if still over (sustained burst inside TTL window), drop oldest.
    if len(_seen_call_ids) > _IDEMPOTENCY_MAX_ENTRIES:
        excess = len(_seen_call_ids) - _IDEMPOTENCY_MAX_ENTRIES
        oldest = sorted(_seen_call_ids.items(), key=lambda kv: kv[1])[:excess]
        for k, _ in oldest:
            _seen_call_ids.pop(k, None)


# ---------------------------------------------------------- session tokens
#
# One-shot opaque tokens for SSE auth. EventSource cannot set custom headers,
# so the long-lived Bearer must never reach the URL. Flow:
#   1. Browser POSTs Next.js /api/events/session
#   2. Next.js POSTs /v1/events/session (Bearer)
#   3. FastAPI returns { session_token, expires_in: 60 }
#   4. Browser opens EventSource('/api/events/stream?session=<token>')
#   5. /v1/events/stream consumes the token (one-shot) and opens the stream

_SESSION_TTL_SECONDS = 60

_session_tokens: dict[str, float] = {}


def _purge_expired_sessions(now: float) -> None:
    expired = [k for k, exp in _session_tokens.items() if exp <= now]
    for k in expired:
        _session_tokens.pop(k, None)


# ---------------------------------------------------------- POST call-ended

class CallEndedEvent(BaseModel):
    call_id: str
    run_id: str
    time: str  # ISO-8601 from HR @ System.time.now_utc


@router.post(
    "/v1/events/call-ended",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
async def call_ended(event: CallEndedEvent) -> None:
    """HR webhook receiver — invalidates dashboard cache + fans event out via SSE.

    Idempotent on `call_id` over a 5-min window. HR retries (up to 100s envelope)
    of the same event are coalesced — invalidate + publish run exactly once.

    Wrapped in try/except so a publish failure doesn't 500 back to HR (HR retries
    are noisy; the event has been received and the worst case is one missed
    SSE fan-out, which the 5-min ISR fallback will cover).
    """
    now = time.time()
    _purge_expired_call_ids(now)

    if event.call_id in _seen_call_ids:
        log.info(
            "events.call_ended.duplicate_suppressed",
            call_id=event.call_id,
            run_id=event.run_id,
        )
        return None

    _seen_call_ids[event.call_id] = now

    try:
        invalidate_dashboard_cache()
        await event_bus.publish(
            {"type": "call.ended", "call_id": event.call_id, "time": event.time}
        )
        log.info(
            "events.call_ended.fanned_out",
            call_id=event.call_id,
            run_id=event.run_id,
            subscribers=event_bus.subscriber_count(),
        )
    except Exception as exc:  # noqa: BLE001 — see docstring
        log.warning(
            "events.call_ended.publish_failed",
            call_id=event.call_id,
            error=str(exc),
        )
    return None


# ---------------------------------------------------------- POST session

@router.post(
    "/v1/events/session",
    dependencies=[Depends(require_api_key)],
)
async def create_session() -> dict[str, Any]:
    """Mint a one-shot opaque session token for SSE subscription (60s TTL)."""
    now = time.time()
    _purge_expired_sessions(now)

    token = secrets.token_urlsafe(32)
    _session_tokens[token] = now + _SESSION_TTL_SECONDS
    return {"session_token": token, "expires_in": _SESSION_TTL_SECONDS}


# ---------------------------------------------------------- GET stream

_KEEPALIVE_SECONDS = 30


def _consume_session(session: str) -> bool:
    """Atomically validate + remove a session token. Returns True if valid."""
    now = time.time()
    _purge_expired_sessions(now)
    expires_at = _session_tokens.pop(session, None)
    if expires_at is None:
        return False
    return expires_at > now


async def _sse_event_stream(request: Request, q: asyncio.Queue):
    """Async generator yielding SSE-formatted bytes for a single subscriber.

    Sends `: keepalive` comment every 30s on idle so proxies don't time the
    connection out. Exits cleanly on client disconnect.
    """
    try:
        # Initial comment — flushes headers + verifies the connection is open.
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            payload = json.dumps(event)
            yield f"event: call-ended\ndata: {payload}\n\n"
    except asyncio.CancelledError:
        # Client disconnect / server shutdown
        raise
    finally:
        event_bus.unsubscribe(q)


@router.get("/v1/events/stream")
async def stream(
    request: Request,
    session: str = Query(..., min_length=8),
):
    """Server-Sent Events stream of dashboard refresh signals.

    Auth: one-shot session token in `?session=` (NOT Bearer — EventSource can't
    set custom headers). Invalid/expired/reused → 401.
    """
    if not _consume_session(session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )

    q = event_bus.subscribe()
    return StreamingResponse(
        _sse_event_stream(request, q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------- test-only helpers

def _reset_state_for_tests() -> None:
    """Clear idempotency + session state. Imported by tests via conftest."""
    _seen_call_ids.clear()
    _session_tokens.clear()
