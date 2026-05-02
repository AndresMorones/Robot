# v15 Architecture — Two-Table Booking Pattern (locked 2026-04-27 evening)

Canonical design for the post-pivot architecture. Replaces v14's multi-load Loop pattern. This is the locked spec the workflow rebuild and dashboard build target.

Pairs with: `docs/decisions/ADR-005-two-table-booking-pattern.md`, memory files `project_v14_loop_architecture.md` (superseded), `feedback_two_table_pattern_industry_standard.md`, `reference_hr_extract_strict_schema_rules.md`.

## 1. Overview

v15 splits the per-call data capture into two flat Twin tables:

- **`bookings`** (NEW) — one row per booking, written **mid-call** by the HR `book_load` tool firing → HR Write-to-Twin chip.
- **`calls_log`** (existing, simplified) — one row per call, written **post-call** by AI Extract → HR Write-to-Twin chip.
- **`loads`** (existing) — read-only catalog seeded from `data/twin_seed_loads.sql`.

Tables join on `call_id` at dashboard query time. The dashboard backend (FastAPI) does all JOINs and aggregations; HR writes flat rows to the two destination tables and never sees the join.

The voice path stays HR-native: HR Voice Agent → HR tools → HR Write-to-Twin. Our FastAPI is read-only on the mid-call write path. FastAPI is the read surface for dashboards plus the carrier-facing loads endpoints.

## 2. Architecture diagram

```
                                  CARRIER CALL (HappyRobot web-call)
                                            │
                                            ▼
                              ┌───────────────────────────────┐
                              │      HR Voice Agent (v15)     │
                              │  master prompt + tool calls   │
                              └───────────────────────────────┘
                                            │
              ┌──────────────┬──────────────┼──────────────┬──────────────┐
              ▼              ▼              ▼              ▼              ▼
        verify_carrier   find_loads   search_by_lane   negotiate    book_load
        (FMCSA webhook)  (Twin Read)  (Twin Read)      (Run Python)  (mid-call)
                                                                           │
                                                                           ▼
                                                              ┌────────────────────┐
                                                              │  HR Write-to-Twin  │
                                                              │   target=bookings  │
                                                              │   1 row per call   │
                                                              │   (one per book)   │
                                                              └────────────────────┘
                                            │
                                  CALL ENDS │ (carrier hangs up / transfer)
                                            ▼
                                ┌───────────────────────────┐
                                │     AI Extract node       │
                                │   call-level scalars only │
                                └───────────────────────────┘
                                            │
                                            ▼
                                ┌───────────────────────────┐
                                │  Case Health Score node   │
                                │   chs / outcome /         │
                                │   sentiment / remarks     │
                                └───────────────────────────┘
                                            │
                                            ▼
                                ┌───────────────────────────┐
                                │  HR Write-to-Twin         │
                                │   target=calls_log        │
                                │   1 row per call          │
                                └───────────────────────────┘

                                      Twin (HR-managed Postgres)
                                ┌─────────────┬──────────────┬─────────────┐
                                │   loads     │   calls_log  │  bookings   │
                                │   (seed)    │   (1/call)   │  (N/call)   │
                                └─────────────┴──────────────┴─────────────┘
                                            │
                                            ▼
                                ┌───────────────────────────┐
                                │       FastAPI (Fly)       │
                                │   GET /v1/dashboard/*     │
                                │   GET /v1/loads/*         │
                                │   reads Twin via SQL/REST │
                                └───────────────────────────┘
                                            │
                                            ▼
                                       Dashboard UI
```

Mid-call writes are short and synchronous (`book_load` → Write-to-Twin → return). Post-call writes happen after the carrier has disconnected, so latency is invisible to the carrier.

## 3. Three tables in Twin

### 3.1 `loads` (seeded, read-only at runtime)

Existing schema (per `data/twin_schema_loads.sql` and ADR-003 §1). Source-of-truth for load reference data: `load_id` (PK), `origin_city`, `origin_state`, `destination_city`, `destination_state`, `pickup_datetime`, `delivery_datetime`, `equipment_type`, `loadboard_rate`, `notes`, `weight`, `commodity_type`, `num_of_pieces`, `miles`, `dimensions` (and the Bridge-aligned columns from ADR-003 when Tier-2 lands).

Rows are seeded once. The voice agent reads via Twin Read child nodes (`Fetch Loads`, `Search Loads by Lane`). No mid-call writes.

### 3.2 `calls_log` (1 row per call, post-call write)

Simplified call-grain fact table. Columns the AI Extract + Case Health Score nodes produce, plus identifiers HR injects from the call envelope:

```
call_id                          TEXT  PRIMARY KEY    -- HR call identifier
created_at                       TIMESTAMPTZ          -- call start
ended_at                         TIMESTAMPTZ          -- call end (HR-provided)
duration_seconds                 INT
mc_number                        TEXT
carrier_name                     TEXT                  -- FMCSA legalName
fmcsa_eligibility_failure_reason TEXT                  -- enum, NULL if passed
case_health_score                INT
sentiment                        TEXT                  -- 5-tag enum
sentiment_start                  TEXT                  -- 5-tag enum
sentiment_trajectory             TEXT
call_outcome                     TEXT                  -- 4-tag enum
audit_remarks                    TEXT
transcript                       TEXT                  -- full transcript JSON
agent_version                    TEXT                  -- e.g. "v15"
callback_phone                   TEXT
```

DROPPED from v14: `loads_discussed` JSONB array, per-load fields like `pitched_loadboard_rate`, `apply_rate`, `original_rate`, `equipment_type`, `load_id` (these all move to bookings rows). Booking-grain fields are NEVER duplicated on calls_log — that was the v14 multi-load anti-pattern.

### 3.3 `bookings` (N rows per call, mid-call write)

Booking-grain fact table. One INSERT per `book_load` tool fire. Each booking is atomic and fully self-describing.

```
booking_id        BIGSERIAL PRIMARY KEY
call_id           TEXT NOT NULL                -- FK to calls_log.call_id
load_id           TEXT NOT NULL                -- FK to loads.load_id
mc_number         TEXT NOT NULL
booked_at         TIMESTAMPTZ DEFAULT NOW()
original_rate     NUMERIC                       -- the listed/asking rate at pitch time
apply_rate        NUMERIC                       -- the final mutually-agreed rate
num_negotiation_rounds INT
final_offer_position   TEXT                     -- broker_at_floor / met_in_middle / etc.
UNIQUE (call_id, load_id)                      -- idempotency guard
```

Indexes:
```
CREATE INDEX idx_bookings_call ON bookings (call_id);
CREATE INDEX idx_bookings_load ON bookings (load_id);
CREATE INDEX idx_bookings_mc   ON bookings (mc_number);
CREATE INDEX idx_bookings_booked_at ON bookings (booked_at);
```

The `UNIQUE (call_id, load_id)` constraint is the idempotency guard: if `book_load` is invoked twice for the same load on the same call (network retry, agent re-confirmation), the second INSERT fails cleanly instead of double-counting revenue. The agent's prompt says "confirm before booking" but the constraint is the safety net.

### 3.4 ER diagram (call_id JOIN)

```
        loads                 calls_log               bookings
   ┌────────────┐         ┌─────────────┐         ┌──────────────┐
   │ load_id PK │◄────┐   │ call_id PK  │◄───┐    │ booking_id PK│
   │ origin_*   │     │   │ created_at  │    │    │ call_id   FK ├──┘
   │ dest_*     │     │   │ mc_number   │    └────┤ load_id   FK ├─►
   │ rate, eq   │     │   │ outcome     │         │ apply_rate   │
   │ ...        │     │   │ chs         │         │ original_rate│
   └────────────┘     │   │ transcript  │         │ rounds       │
                      │   │ ...         │         │ ...          │
                      │   └─────────────┘         └──────────────┘
                      │                                  │
                      └──────────────────────────────────┘
                          (load_id FK to loads — for lane / rate enrichment)
```

Dashboard SQL pattern: `SELECT ... FROM bookings b LEFT JOIN calls_log c USING (call_id) LEFT JOIN loads l USING (load_id) WHERE c.created_at >= …` — three flat tables, all joins on indexed PK/FK columns.

## 4. Voice agent flow (mid-call)

For each load the carrier agrees to book during the call:

1. Carrier and agent reach final-rate agreement on a specific `load_id`.
2. Agent invokes `book_load` tool with: `load_id`, `mc_number`, `apply_rate`, `original_rate` (snapshot of the load's listed rate at pitch time), `num_negotiation_rounds`, `final_offer_position`.
3. `book_load` is wired as an HR Action node → HR Write-to-Twin (target table `bookings`). One INSERT.
4. Tool returns success/failure to the agent. On failure (idempotency violation, transient Twin error), the agent's prompt instructs it to reassure the carrier ("system delay — confirming on my end") rather than retry blindly.
5. Agent verbal-fillers during the ~500ms-1s tool latency ("great, locking that in"). This is the canonical mitigation for the latency tradeoff.

Agent can fire `book_load` multiple times in one call (multi-load wins). Each fire is independent. No Loop node, no array, no Custom Code shim, no Paths node.

If the carrier hangs up mid-call, every booking captured before the hangup is already persisted. Compare to v14: a mid-call hangup before the post-call Loop ran would have lost ALL bookings.

## 5. Post-call flow

After call ends:

1. HR fires the post-call chain: AI Extract → Case Health Score → Write-to-Twin (`calls_log`).
2. AI Extract emits **scalar** call-level fields only — no `loads_discussed` array. Field surface: `mc_number`, `carrier_name`, `fmcsa_eligibility_failure_reason`, `sentiment_start`, `sentiment_trajectory`, `callback_phone`, `agent_version`, `transcript`.
3. Case Health Score emits `case_health_score`, `call_outcome`, `sentiment`, `audit_remarks` (single LLM call, per the v14 classifier design — that part survives the pivot).
4. Write-to-Twin INSERTs one row keyed by `call_id`.

Booking-grain fields are **never** part of the post-call extract. The agent's tool fires are the source of truth.

## 6. FastAPI endpoint surface

### Drop list (no longer in v15)

- `POST /v1/calls/log` — superseded by HR Write-to-Twin direct path. The FastAPI shim was a v14-era artifact for staging the loads_discussed array; now obsolete.

### Keep list

- `GET /v1/loads/{reference_number}` — single-load lookup (carrier-facing surface; per-spec).
- `GET /v1/loads/search` — lane / equipment / date filtered search (per-spec).
- `GET /v1/dashboard/funnel` — call-grain funnel metrics from `calls_log`.
- `GET /v1/dashboard/economics` — booking-grain revenue / discount / rate-lift JOINing `bookings ⋈ calls_log ⋈ loads`.
- `GET /v1/dashboard/operational` — volume, hour-heatmap, duration histogram from `calls_log`.
- `GET /v1/dashboard/quality` — CHS distribution, sentiment mix, decline reasons from `calls_log`.
- `GET /v1/policy/defaults` (optional, broker-doc Tier-2) — exposes 4 HR workflow vars.
- `GET /v1/carrier-profile/{mc}` (optional) — repeat-caller history JOINing `bookings ⋈ calls_log` filtered by `mc_number`.

All endpoints are Bearer-authed (or `?token=`) per CLAUDE.md auth conventions.

## 7. Dashboard query patterns — Tier 1 metrics

The five Tier 1 metrics that drive the executive KPI strip. SQL shape shown is the canonical form — actual implementation goes through the FastAPI dashboard service layer, not raw SQL exposed to clients.

### M-001 — Calls Today

Call-grain. Single-table query.

```sql
SELECT COUNT(*) AS calls_today
FROM   calls_log
WHERE  created_at >= date_trunc('day', NOW() AT TIME ZONE 'America/Chicago');
```

### M-080 — Bookings Today (booking-grain volume)

Booking-grain. Single-table query.

```sql
SELECT COUNT(*) AS bookings_today
FROM   bookings
WHERE  booked_at >= date_trunc('day', NOW() AT TIME ZONE 'America/Chicago');
```

### M-081 — Bookings per Booked Call (multi-load celebration)

Joins both fact tables. Per `dashboard-design-philosophy.md` Principle 2, multi-load wins surface as `bookings ÷ booked_calls > 1.0`.

```sql
SELECT COUNT(*)::FLOAT
       / NULLIF(COUNT(DISTINCT b.call_id), 0)            AS bookings_per_booked_call
FROM   bookings b
JOIN   calls_log c USING (call_id)
WHERE  c.created_at >= :window_start;
```

### M-082 — No-Booking Calls

Call-grain, anti-join against bookings. Counts calls where ZERO bookings landed (not the same as `call_outcome='no_match'` — a call could have outcome='load_booked' yet still have failed every `book_load` tool fire and be hangup-rescued; this metric audits true booking failure).

```sql
SELECT COUNT(*) AS no_booking_calls
FROM   calls_log c
LEFT JOIN bookings b ON b.call_id = c.call_id
WHERE  c.created_at >= :window_start
  AND  b.booking_id IS NULL;
```

### M-010 — Revenue Booked

Booking-grain SUM. Joins bookings to calls_log only for the time-window filter.

```sql
SELECT COALESCE(SUM(b.apply_rate), 0) AS revenue_booked
FROM   bookings b
JOIN   calls_log c USING (call_id)
WHERE  c.created_at >= :window_start;
```

Notes:
- All five queries are null-resilient (`NULLIF`, `COALESCE`).
- All five use indexed columns (`created_at` on calls_log, `booked_at` on bookings).
- The dashboard backend caches per-window aggregates briefly (≤30s) to absorb tile + sparkline + trend-chart triple-fetches.
- Per Principle 2, headline ratios use bookings as numerator, not calls.

## 8. Tradeoffs (honestly stated)

| Tradeoff | Severity | Mitigation |
|---|---|---|
| **Mid-call latency** of `book_load` tool fire (~500ms-1s — Twin INSERT round-trip via HR Write-to-Twin) | Medium — carrier-perceptible if not masked | Verbal filler in agent prompt ("great, locking that in") covers the gap. Validated as the standard pattern in HR voice flows. |
| **Drops declined-load context** from analytics — non-booked loads pitched-and-rejected mid-call don't get persisted as structured rows. | Low — pragmatic | Transcript captures it. Tier-2 could add a scalar `declined_loads_count` field to AI Extract (single integer extracted from transcript) without resurrecting the array. |
| **Idempotency required** — network retry of `book_load` could double-write | Low — handled at schema layer | `UNIQUE (call_id, load_id)` constraint on bookings rejects duplicates cleanly. Agent prompt instructs gentle re-assurance on tool-failure response. |
| **Two writes per call** (one mid-call, one post-call) instead of one consolidated write | Low | Two flat INSERTs are simpler than v14's Custom Code → Paths → Loop → N×Write-to-Twin chain. Net complexity drops. |
| **Cross-table queries everywhere** in dashboard | Low | All joins are PK/FK on indexed columns. Postgres-on-Twin handles this trivially. |

The biggest win is hidden in the not-listed: the `loads_discussed` JSONB column is gone, the Loop is gone, the Custom Code shim is gone, the Paths node is gone. Cloudflare WAF risks on JSONB unnest (per ADR-004 context) are gone. The agent never extracts `load_id` from a transcript — it passes it directly via tool param.

## 9. Migration order

Sequenced for minimum risk on the way to v15:

1. **Twin DDL** — `CREATE TABLE bookings (...)` with the UNIQUE constraint and 4 indexes. Done via `POST /api/v2/twin/sql`. Idempotent (`CREATE TABLE IF NOT EXISTS`).
2. **calls_log column drops** — drop `loads_discussed`, `pitched_loadboard_rate`, `apply_rate`, `original_rate`, `equipment_type`, `load_id` from calls_log. Use `ALTER TABLE ... DROP COLUMN IF EXISTS`. (Existing v13/v14 row content is acceptable archaeological data; no migration of historical rows needed at MVP scale.)
3. **HR workflow rebuild** (UI-only — never API; per `reference_hr_post_batch_corruption.md`):
   - Remove Custom Code shim, Paths node, Loop node from the post-call chain.
   - Simplify AI Extract to scalar fields only.
   - Add `book_load` Action node under the Prompt node, wired to a new HR Write-to-Twin chip targeting `bookings`.
   - Update master prompt to invoke `book_load` at agreed-rate moment, with verbal-filler instruction.
4. **FastAPI dashboard refactor** — update `api/app/services/dashboard_aggregations.py` SQL to JOIN bookings ⋈ calls_log. Drop `POST /v1/calls/log` route from `api/app/routers/loads.py` (the route currently named `calls.py` post-WS2a). Add `bookings` table reads.
5. **Smoke test** — single carrier call with single booking; assert one bookings row + one calls_log row, both linked by `call_id`. Then a multi-load call (2+ bookings); assert N bookings rows + 1 calls_log row.
6. **Test re-run** — Phase 6 7-call suite verifies: multi-load wins land as N bookings, FMCSA decline lands as 0 bookings + 1 calls_log row with `fmcsa_eligibility_failure_reason` populated, abandons land as 0 bookings + 1 calls_log row with `call_outcome='call_abandoned'`.

Tier-2 path forward (Postgres migration) is unchanged from `project_post_mvp_scalability_availability.md` — Twin → managed Postgres is a lift-and-shift since the schema is already standard 3NF.

## 10. References

- `docs/decisions/ADR-005-two-table-booking-pattern.md` — the decision record + rationale.
- `docs/v14-classifier-design-2026-04-27.md` (SUPERSEDED) — what we just walked away from.
- `docs/decisions/ADR-003-adopt-bridge-api-contract.md` — Tier-2 schema enrichment of `loads` table; v15 is compatible.
- `docs/decisions/ADR-004-twin-search-architecture.md` — Twin search architecture; carriers/loads search path is unchanged in v15.
- `docs/dashboard-design-philosophy.md` — Principle 2 (multi-load is positive), Principle 3 (null-resilience), Principle 9 (donut grain composition).
- `docs/dashboard-metric-catalog.md` — full metric catalog; v15-aware Tier 1 metrics (M-001, M-080, M-081, M-082, M-010).
- Memory: `project_v14_loop_architecture.md` (superseded), `feedback_two_table_pattern_industry_standard.md`, `reference_hr_extract_strict_schema_rules.md`, `feedback_ask_clarifying_questions.md`.
