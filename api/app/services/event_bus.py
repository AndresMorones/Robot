"""In-process pubsub bus for dashboard freshness events.

Used by the Option C hybrid push pipeline: HR webhook → POST
/v1/events/call-ended → publish() → SSE subscribers fan out to browsers.
See ADR-009 + memory `project_dashboard_freshness_options.md` for the full
architecture (3 layers: trigger × fetch × cache, decoupled).

Multi-machine constraint: `_subscribers` lives in this process only. Two Fly
machines = two disjoint subscriber sets, so a webhook landing on machine A
won't fan out to a browser connected to machine B. MVP runs single-machine
(`min_machines=1`); the Tier-2 escape hatch is Redis pubsub (~1 hr swap, no
caller API change). Tracked in ADR-007 §6 + ADR-009.

Per-subscriber queue is bounded (maxsize=100) so a slow client cannot OOM the
process — `put_nowait` will silently drop overflow events for that subscriber,
and the 5-minute ISR fallback will catch any missed update on the next render.
"""

from __future__ import annotations

import asyncio

import structlog

log = structlog.get_logger()

_SUBSCRIBER_QUEUE_MAXSIZE = 100

_subscribers: set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    """Register a fresh queue and return it.

    Caller is responsible for `unsubscribe(q)` on disconnect (use `try/finally`
    in the SSE generator).
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_MAXSIZE)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Remove a queue from the subscriber set.

    Idempotent — safe to call multiple times during teardown.
    """
    _subscribers.discard(q)


async def publish(event: dict) -> None:
    """Fan event out to every subscriber.

    Uses `put_nowait` so a slow consumer cannot block the publisher. If a
    subscriber's queue is full we log and drop — the 5-min ISR polling
    fallback ensures the missed event still surfaces.
    """
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("event_bus_publish_dropped", payload=event)


def subscriber_count() -> int:
    """Number of currently-subscribed queues. Useful for diagnostics."""
    return len(_subscribers)
