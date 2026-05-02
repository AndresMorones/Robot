# ADR-005 — Two-table booking pattern: `bookings` (mid-call) + `calls_log` (post-call)

- **Status**: Accepted
- **Date**: 2026-04-27 (evening)
- **Decided by**: Andres + Claude (after a day of iterating on the v14 Loop architecture and surfacing structural problems with extracting `load_id` from transcripts)
- **Supersedes**: the v14 multi-load Loop pattern documented in `docs/v14-classifier-design-2026-04-27.md`
- **Superseded by**: none

## Context

v14 (locked the morning of 2026-04-27) had the post-call AI Extract emit a `loads_discussed` JSON array — one element per load the carrier engaged with — and routed it through a Custom Code shim → Paths node → Loop node → N×Write-to-Twin chain. Goal: one row per LOAD discussed, in a single `calls_log` table.

By the end of the day, three structural issues had surfaced:

1. **`load_id` is hard to extract from transcripts.** Carriers and agents refer to loads as "the Dallas-Atlanta one", "the reefer", "the first load", or by partial reference numbers. The AI Extract had to reconstruct canonical `load_id` strings post-hoc by reasoning over the transcript and the loads catalog. The error rate on this single field was unacceptable for a primary key on a fact row.
2. **Multi-load complexity** required a Loop node, a Custom Code shim to convert AI Extract's JSON Schema array output into the format Paths expected, and a Paths node to fan-out — three nodes whose only job was to support one multi-load case. RestrictedPython sandbox limits (per `reference_hr_python_sandbox_restrictions.md`) constrained the Custom Code shim's safe shape. The whole sub-graph was fragile.
3. **Mid-call hangup loses everything.** All bookings are post-call: if the carrier hangs up after agreeing to 2 loads but before the post-call chain runs, every booking is lost. v14 had no atomic mid-call persistence.

A separate concern that pushed the same direction: dashboard SQL was getting JSONB-unnest-heavy. Per ADR-004 context, Cloudflare WAF intermittently 403s quoted-literal SQL bodies through `/api/v2/twin/sql`, and JSONB column queries multiply that risk surface.

We considered "fix the Loop / fix the Custom Code shim / harden the load_id extraction prompt" as incremental options. None addressed the mid-call-hangup gap, and all preserved the JSONB query surface.

## Decision

**Adopt a two-table booking pattern.** Split per-call data capture across two flat Twin tables:

- **`bookings`** — booking-grain fact table, written **mid-call** by an HR `book_load` tool fire → HR Write-to-Twin. One INSERT per book. Idempotency guarded by `UNIQUE (call_id, load_id)`.
- **`calls_log`** — call-grain fact table, written **post-call** by AI Extract → Case Health Score → HR Write-to-Twin. One INSERT per call. Carries call-level scalars only; no booking-grain fields.

`loads` stays as the seeded catalog table (read-only at runtime). The dashboard FastAPI joins `bookings ⋈ calls_log` on `call_id` and `bookings ⋈ loads` on `load_id` to produce all booking-grain economics views.

**Specifically dropped**: `loads_discussed` JSONB column on calls_log, the Custom Code shim, the Paths node, the Loop node, the `POST /v1/calls/log` FastAPI endpoint.

**Specifically kept**: HR-native voice path (no FastAPI in mid-call write path), our FastAPI for dashboard reads + carrier-facing loads endpoints, the Case Health Score classifier from the v14 design (single-LLM-call still valid).

Full design at `docs/v15-architecture-2026-04-27.md`.

## Consequences

**Positive**

- **Solves load_id extraction.** Agent passes `load_id` directly as a `book_load` tool param. Never reconstructed from transcript.
- **Multi-load complexity collapses.** N bookings = N tool calls = N rows. No Loop, no shim, no Paths.
- **Mid-call hangup safety.** Each booking is persisted as it happens. A hangup after 2-of-3 books still captures 2 bookings.
- **Atomic writes.** Each booking is its own INSERT. No partial-failure modes from a Loop iteration mid-flight.
- **Standard data warehouse pattern.** Booking-grain fact + call-grain fact tables with a shared FK is the canonical shape any analytics engineer recognizes immediately. Strong broker-doc story.
- **Cleaner dashboard SQL.** No JSONB unnesting; reduced Cloudflare WAF risk surface (per ADR-004); all joins on indexed PK/FK columns.
- **Drops `POST /v1/calls/log` endpoint** — one less API surface to authenticate, test, and document.

**Negative**

- **Mid-call latency** added on every booking — `book_load` tool fire round-trips to HR Twin Write (~500ms-1s in our measurements). Carriers can perceive this if the agent goes silent.
- **Drops declined-load context.** Loads pitched and rejected mid-call no longer land as structured rows. Transcript still captures it.
- **Two writes per call** instead of one consolidated post-call write. Operational complexity is two flat INSERTs instead of one Loop chain — a net simplification, but worth naming.

**Mitigations**

- **Latency**: master prompt instructs the agent to verbal-filler during tool fires ("great, locking that in"). Verified as the standard pattern in HR voice flows; covers the ~1s gap convincingly.
- **Declined-load context**: Tier-2 `declined_loads_count` scalar Extract field gives basic visibility without resurrecting the array. Detailed analysis stays in transcripts.
- **Idempotency**: `UNIQUE (call_id, load_id)` constraint at the schema layer rejects duplicate INSERTs from network retry. Agent prompt instructs gentle reassurance on tool-failure response rather than blind retry.

## Tradeoffs

| Concern | v14 Loop | v15 two-table | Verdict |
|---|---|---|---|
| **load_id source-of-truth** | Reconstructed by post-call LLM Extract from transcript | Passed as tool param at booking moment | v15 wins decisively |
| **Multi-load complexity** | Custom Code + Paths + Loop + N×Write | N tool fires, each is one INSERT | v15 wins |
| **Mid-call hangup** | All bookings lost | Bookings already persisted | v15 wins |
| **Mid-call latency** | Zero (everything happens post-call) | ~500ms-1s per `book_load` | v14 wins (mitigation: verbal filler) |
| **Declined-load analytics** | Captured in `loads_discussed` | Transcript only (Tier-2: scalar count) | v14 wins (low practical value) |
| **Dashboard SQL** | JSONB unnest patterns, Cloudflare WAF risk | Standard PK/FK joins | v15 wins |
| **Schema simplicity** | One table with JSONB column | Two flat tables, joined on call_id | Wash — both are reasonable; v15 follows industry standard |
| **Operational atomicity** | Loop iteration partial-failure modes | Per-booking INSERT atomicity | v15 wins |

The latency tradeoff is real but well-mitigated. The declined-load tradeoff is small in practice — the transcript captures it, and the calls_log retains call-level outcome buckets (`call_outcome ∈ {load_booked, no_match, carrier_not_qualified, call_abandoned}`).

## Open questions / accepted risks

- **HR Write-to-Twin tool latency variance.** If the p95 of the round-trip exceeds ~1.5s the verbal-filler mitigation degrades. Not currently observed; instrument with smoke tests in Phase 6.
- **Idempotency on legitimately-cancelled bookings.** If an agent books a load and the carrier reverses the decision in the same call, the schema doesn't model rollback. Acceptable at MVP; Tier-2 could add a `cancelled_at` column on bookings without breaking the pattern.
- **Cross-table query latency.** Twin Postgres handles 3-table joins on indexed PK/FK columns trivially at MVP scale (<10K bookings). Reassess at >100K bookings or first dashboard slowness.

## References

- [v15 architecture](../v15-architecture-2026-04-27.md) — full design doc with ER diagram, flows, SQL patterns, migration order
- [v14 classifier design](../v14-classifier-design-2026-04-27.md) — SUPERSEDED predecessor (banner in place)
- [ADR-003 — Bridge API contract](ADR-003-adopt-bridge-api-contract.md) — `loads` table schema enrichment; v15 is compatible
- [ADR-004 — Twin search architecture](ADR-004-twin-search-architecture.md) — Cloudflare WAF risk on JSONB SQL; one of the pressures behind dropping `loads_discussed`
- `docs/dashboard-metric-catalog.md` — Tier 1 metric definitions (M-001, M-080, M-081, M-082, M-010) updated to two-table JOIN form
- `docs/dashboard-design-philosophy.md` — Principle 2 (multi-load is positive), Principle 3 (null-resilience), Principle 9 (donut grain)
- Memory: `project_v14_loop_architecture.md` (superseded), `feedback_two_table_pattern_industry_standard.md` (newly created), `reference_hr_extract_strict_schema_rules.md`, `feedback_ask_clarifying_questions.md`
- HR platform: `reference_hr_post_batch_corruption.md` — workflow rebuild MUST be UI-only (no API mutation)
