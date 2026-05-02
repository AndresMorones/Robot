# ADR-009: Webhook + SSE Hybrid Freshness Pipeline (Option C)

- **Status:** Accepted
- **Date:** 2026-04-28
- **Supersedes:** ADR-007 §6 (Tier-2 webhook path) — promoted from deferred to shipped
- **Superseded by:** None

## 1. Context

ADR-007 established two cache layers (Next.js ISR `revalidate=30` + FastAPI `cachetools.TTLCache(ttl=30s, maxsize=128)`) and explicitly deferred the webhook-driven invalidation path: *"the user said 'no need to focus on webhook to trigger update for now'; it stays on the roadmap."*

On 2026-04-28 the user reversed that decision: *"I think could be good to add webhook so no continuous queries and stating we have cache log this architecture addition document it deeply for final architecture diagram creation summaries and reviews ... do option c"*. Memory file `project_dashboard_freshness_options.md` captures the full 4-option spectrum; this ADR records the architectural commitment.

The dashboard freshness problem decomposes into three independent layers, each with its own decision space:

| Layer | Decision space | Prior value | New value |
|---|---|---|---|
| **Trigger** | when to refresh | 30s timer (ISR) | event (HR webhook) + 5-min timer fallback |
| **Fetch** | where data comes from | always Twin via FastAPI | unchanged |
| **Cache** | how often we hit Twin | 30s TTL + ISR | TTL invalidated by webhook + ISR same |

The webhook does **not** replace fetching. Twin remains the single source of truth. The webhook just signals *now is when to bother*. Savings come from the cache absorbing every read between events.

## 2. Decision

**Adopt Option C — webhook (HR `call.ended`) + SSE (FastAPI → Next.js) + 5-min ISR fallback.**

The four candidates considered:

- **A — pure 30s polling** (prior state): ~120 Twin queries/hour per dashboard tab, regardless of activity.
- **B — pure event-driven webhook**: ~per-call only, but a single dropped webhook means stale data until next browser refresh.
- **C — hybrid**: webhook for sub-second push, 5-min ISR for guaranteed catch-up. ← **chosen**
- **D — manual F5 only**: ~10/hour, poor UX. Rejected.

### Architecture

Three layers stay decoupled. The webhook signals *when*; the existing FastAPI/Twin path handles *what*; the cache layer absorbs duplicate reads.

```
HR call.ended
  -> POST /v1/events/call-ended  (Bearer)
     -> idempotency check on call_id (5-min window > HR's 100s max retry envelope)
     -> invalidate_dashboard_cache()      (clears 9 wrapped TTLCache entries)
     -> event_bus.publish({type, call_id, time})   (in-process pubsub)
     -> SSE subscribers fan out
        -> browsers receive `event: call-ended`
        -> router.refresh()
        -> Next.js Server Component re-renders
        -> fetch FastAPI -> cache miss -> Twin -> fresh data on screen
```

EventSource cannot send custom headers, so the SSE auth flow uses a one-shot opaque session token (60s TTL, single use). Browser POSTs `/api/events/session` (Bearer added server-side by the Next.js Route Handler), then opens `EventSource('/api/events/stream?session=<opaque>')`. The session token is consumed atomically on connect; reused tokens get 401.

### Twin-query math

Assumed: 50 calls/day, 8 hr dashboard open, 1 reviewer.

| Option | Twin queries/day | Reduction vs A |
|---|---|---|
| A — pure polling 30s | ~960 | baseline |
| B — pure webhook | ~250 | -74% |
| **C — hybrid (chosen)** | **~350** | **-64% with reliability guarantee** |
| D — manual only | ~10-30 | -97% (poor UX) |

C costs ~100 extra queries/day vs B for the polling fallback; that buys catch-up of every dropped webhook (typical drop rate ~1%). Combined with the existing ADR-007 caches, the hot-path savings vs the original force-dynamic baseline remain ~95-99%.

## 3. Consequences

### Positive

- Sub-second dashboard refresh on the happy path (HR webhook → SSE → `router.refresh()` is ~1-3s end-to-end).
- 5-min ISR catches any webhook drop — push for latency, pull for guarantee. Production-standard dual-source pattern.
- Zero new infra: in-process `asyncio.Queue` pubsub, stdlib only (`asyncio`, `secrets`, `json`, `dict`).
- Reuses the `invalidate_dashboard_cache()` seam already exported in ADR-007.
- Idempotency on `call_id` over a 5-min window absorbs HR's retry envelope (defaults: 2 retries × 10s base × 2× backoff × 100s max).

### Negative

- **In-process pubsub doesn't fan out across Fly machines.** Two machines = two disjoint subscriber sets, so a webhook landing on machine A won't reach a browser connected to machine B. MVP runs `min_machines=1`; the documented Tier-2 escape hatch is Redis pubsub (~1 hr swap, no caller API change).
- Slow consumers can fill their bounded `asyncio.Queue(maxsize=100)` and silently miss events; the 5-min ISR fallback covers that case.
- Long-lived SSE connections count against Fly's per-machine connection budget — currently negligible (one reviewer, maybe a handful of tabs), worth tracking in observability.

### Reliability pattern

- **Push** for low latency (webhook → SSE).
- **Pull** for guarantee (5-min ISR fallback catches missed events).

Without the polling fallback, dropped webhooks would never surface until the next manual refresh. Without the push, every refresh is a 5-min stale ceiling. Both layers are cheap; both pay for themselves.

## 4. HR-side configuration snapshot

Workflow → Webhooks → add `call.ended` event:

- **URL:** `https://robot-api-andres-morones.fly.dev/v1/events/call-ended`
- **Method:** POST
- **Body** (JSON, *Preserve data types* ON):
  ```json
  {
    "call_id": "<@ Voice Agent.call_id>",
    "run_id":  "<@ System.run_id>",
    "time":    "<@ System.time.now_utc>"
  }
  ```
- **Authorization:** Bearer Token (value = `API_BEARER_TOKEN` Fly secret).
- **Error Handling:** *Gracefully handle 5XX errors* ON.
- **Security:** *Enable XSS protection* ON.
- **Retries:** defaults (2 × 10s × 2× backoff, ~100s envelope).

Variable bindings must use the `@` picker — hand-typed `{{var}}` references silently render empty at runtime (memory `feedback_hr_variable_resolution.md`).

## 5. Reference

- Memory: `project_dashboard_freshness_options.md` — full 4-option spectrum + decision narrative.
- Memory: `project_dashboard_caching_strategy.md` — the prior cache-only architecture this composes onto.
- ADR-007 — two-layer caching strategy (this ADR's substrate).
- ADR-006 — Next.js dashboard commit (this ADR's UI substrate).
- Code: `api/app/services/event_bus.py`, `api/app/routers/events.py`, `dashboard/src/components/live-refresh.tsx`, `dashboard/src/app/api/events/{session,stream}/route.ts`.
- Tests: `api/tests/test_events.py` (auth + idempotency + session flow + bus fan-out).
