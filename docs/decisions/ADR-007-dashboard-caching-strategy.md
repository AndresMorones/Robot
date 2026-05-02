# ADR-007: Dashboard Caching Strategy — Two-Layer In-Process TTL

- **Status:** Accepted
- **Date:** 2026-04-28
- **Supersedes:** None
- **Superseded by:** None

## 1. Context

The initial dashboard architecture made every page render fire 5-15 Twin SQL queries through FastAPI on each browser refresh. The user flagged this as wasteful: most refresh events return identical data, and HR Twin sits behind Cloudflare WAF + REST rate limits, so query volume is a real ceiling rather than a theoretical concern.

A goliath investigation surfaced three layered optimization options. They are independent but compose cleanly:

1. A Next.js cache fix at the App Router layer.
2. A FastAPI-layer TTL cache wrapping the aggregation functions.
3. A webhook-driven cache invalidation path (HR `call.ended` → FastAPI receiver → invalidate + `revalidatePath`) for near-real-time push.

The recent scope shift from "MVP-minimum" to "production-ready" (see ADR-006) makes optimization matter — the dashboard is now a demo surface, not just an internal admin view. Custom SQL via `twin_client.run_sql()` is fully supported, so the bottleneck is query frequency, not query flexibility.

## 2. Decision

**Adopt a two-layer in-process cache: Next.js ISR (`revalidate=30`) + FastAPI `cachetools.TTLCache(ttl=30s, maxsize=128)`.**

- Next.js App Router pages drop their `force-dynamic` overrides and use `revalidate=30`. Rendered HTML is cached at the Next.js edge for 30 seconds; cache hits do zero work below the Next.js layer.
- FastAPI aggregation functions are wrapped with a `cachetools.TTLCache` keyed on call arguments. Sub-millisecond hits absorb the Next.js cache misses that still reach the API.
- An `invalidate_dashboard_cache()` helper is exported for future event-driven invalidation. It is not called anywhere yet — it is the seam for the Tier-2 webhook path.

**Tier-2 path documented but explicitly deferred:** HR `call.ended` webhook → FastAPI `/v1/events/call-ended` → `invalidate_dashboard_cache()` + Next.js `revalidatePath('/dashboard')` for ~1-3s push latency. The user said "no need to focus on webhook to trigger update for now"; it stays on the roadmap.

## 3. Consequences

### Positive

- ~95-99% reduction in Twin query load on the dashboard hot path under steady-state traffic.
- Sub-millisecond FastAPI cache hits when the Next.js cache misses (e.g. across cache key boundaries).
- Zero infrastructure cost: in-process only, no Redis, no third-party cache.
- Staleness ceiling is 30 seconds — acceptable per spec (no real-time requirement stated).
- The `invalidate_dashboard_cache()` hook is in place, so the Tier-2 webhook integration is additive, not a refactor.

### Negative

- In-process state breaks under multi-machine Fly deploys: each machine has its own cache, so two browsers hitting different machines may see different data inside the 30s window.
- 30s staleness window: a call that lands immediately after a refresh will not appear until the next window or a manual refresh.
- Cache adds a debug surface — any data oddity now has "is the cache stale?" as a candidate root cause.

### Neutral

- Complexity is low: the cache infrastructure is roughly 30 LOC, and the rename-and-wrap pattern keeps every existing caller untouched.
- The escape hatch to multi-machine (Redis pub/sub or equivalent) is well-known and not blocked by this decision.

## 4. Alternatives considered

**A. Faster polling (`revalidate=5s`).** Pros: closer to real-time. Cons: 6× more dashboard render work and 6× more Twin query load; doesn't actually solve the wasteful-refresh problem, just moves it. Rejected.

**B. Webhook + SSE push (Option B from the goliath investigation).** Pros: ~1-3s latency, true real-time, demo wow factor. Cons: ~4-5 hours of Claude-time plus ~10 min of user-time HR webhook config; in-process pubsub also breaks under multi-machine, so it inherits the same scaling caveat. Rejected for this cycle on direct user instruction; logged as Tier-2.

**C. Materialized views in Twin Postgres.** Pros: server-side pre-aggregation; the view is always self-consistent. Cons: HR Twin's support for materialized views is unverified; manual refresh schedules add cognitive load; on-demand invalidation is harder than with an in-process cache. Rejected.

**D. Replicated local Postgres / SQLite for dashboard reads.** Pros: zero query lag on the read path; full SQL flexibility. Cons: replication infrastructure, schema sync overhead, large complexity add for marginal gain over a TTL cache. Rejected.

**E. Redis-backed cache.** Pros: production-grade, multi-machine ready out of the box. Cons: adds a Redis service (~$5-10/mo Fly Redis or external); not justified at single-machine MVP scale. Held as the Tier-2 escape hatch when scaling beyond one machine.

## 5. Rollout plan

1. Drop `force-dynamic` from the four Next.js dashboard pages — DONE.
2. Add `cachetools>=5.5` to API deps — DONE.
3. Wrap the nine aggregation functions with the TTL cache — DONE (parallel agent).
4. Add at least three caching tests (hit, miss-then-hit, TTL expiry) — DONE (parallel agent).
5. User runs `uv sync` + `uv run pytest -x` to verify locally.
6. User redeploys the API to Fly.
7. Monitor Twin query rate post-deploy — drop should be visible immediately.

## 6. Open questions / risks

- **Cache stampede on cold start.** All nine cache slots empty → first request can trigger nine parallel Twin queries. Mitigated by an `asyncio.Lock` in `_cached_call` so only one query per cache key is in flight at a time.
- **Multi-machine drift.** `fly.toml` currently runs `min_machines=1`. Scaling to two or more without swapping the in-process cache for Redis introduces visible cross-machine staleness. Documented in the broker doc as a Tier-2 prerequisite.
- **Staleness during demo.** If a call lands during a Loom recording and the dashboard is mid-30s window, the call won't appear without a manual refresh. Mitigation: hit refresh in the narration, or run with `revalidate=5` during recording and revert post-demo.

## 7. References

- FDE spec: `docs/FDE-TECHNICAL-CHALLENGE.md`
- Goliath investigation findings (in conversation; archived to memory)
- Memory: `project_dashboard_caching_strategy.md`
- Memory: `project_dashboard_nextjs_committed.md`
- Memory: `project_phase_b_complete_audit_2026_04_28.md`
- Memory: `project_post_mvp_scalability_availability.md` (Redis path)
- ADR-006: Next.js dashboard commit (precursor)
