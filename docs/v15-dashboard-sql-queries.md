# v15 Dashboard SQL Queries — Tier 1 Metrics

Paste-ready SQL for the five Tier 1 dashboard metrics under the v15 two-table
architecture (`calls_log` + `bookings`). Pairs with:

- `docs/v15-two-table-schema.md` — table shapes and JOIN semantics.
- `docs/dashboard-metric-catalog.md` — full 29-metric catalog (these are the
  five MVP metrics).
- `docs/dashboard-design-philosophy.md` — null-resilience principles.
- `api/app/services/twin_client.py` — execution path for these queries.
- `tests/integration/v15/` — TB1–TB5 scripts that assert each metric.

The dashboard backend (FastAPI) executes these via `twin_client.query(sql,
params)`. They are **not** run from HR. The Twin REST `/twin/sql` endpoint
accepts a single statement per call and applies Cloudflare WAF rules at the
edge.

---

## Cloudflare WAF safety — patterns to avoid

The Twin SQL gateway sits behind Cloudflare. Per `ADR-004`, certain patterns
trigger 403 / 502s before reaching Postgres:

- **No `IN ('a', 'b', 'c')` literal lists.** WAF flags multi-quoted-literal
  bodies as injection candidates. Replace with explicit equality OR `LEFT JOIN
  … IS NULL` / `NOT EXISTS` patterns.
- **No `ANY (ARRAY[…])` constructs.** Same trigger as IN-lists.
- **No JSONB operators (`->`, `->>`, `@>`, `?`, `#>>`).** WAF treats these as
  high-entropy injection vectors.
- **No deeply nested subqueries with mixed quoted strings + casts.** Keep
  subqueries to a single level where possible; flatten with CTEs only if the
  WAF tolerates the size.
- **No multi-statement bodies.** One statement per `/twin/sql` call.
- **Avoid `CASE WHEN x IN (…)`.** Use conditional COUNTs with simple equality.

Workaround pattern this doc uses:

- For "membership" tests, prefer `NOT EXISTS (SELECT 1 FROM other WHERE …)` or
  `LEFT JOIN other ON … WHERE other.col IS NULL`. Both are WAF-safe and read
  cleanly.
- For per-bucket counts, use `SUM(CASE WHEN col = 'value' THEN 1 ELSE 0 END)`
  rather than `COUNT(*) FILTER (WHERE col = 'value')` (FILTER is fine, but the
  CASE form has been observed to behave consistently across regions).
- For aggregation guarantees, always `COALESCE(SUM(x), 0)` so the JSON
  response carries `0` rather than `null` when the table is empty.

If a query in this file ever needs a pattern outside the WAF-safe set, push the
aggregation up into FastAPI (per ADR-004): fetch the raw rows in a single
flat SELECT, aggregate in Python with the `_safe_*` helpers from
`api/app/services/dashboard_aggregations.py`.

---

## Filter parameters

All five metrics share the same filter window vocabulary:

| Param          | Type      | Description                                           | Example                |
|----------------|-----------|-------------------------------------------------------|------------------------|
| `:window_from` | TIMESTAMPTZ | Inclusive lower bound on `created_at`               | `2026-04-20 00:00:00+00` |
| `:window_to`   | TIMESTAMPTZ | Exclusive upper bound on `created_at`               | `2026-04-28 00:00:00+00` |

Twin lacks parameter binding, so `twin_client._interpolate` splices these
values as quoted SQL literals. Both bounds are required; the FastAPI layer
defaults missing values to "trailing 7 days" so the query is never unbounded.

When a metric needs a JOIN-time filter — e.g. M-081 reads from `calls_log` and
EXISTS-tests against `bookings` — apply the window only to the **outer** table
(`calls_log.created_at`). Bookings written mid-call may have a `created_at`
slightly before the calls_log row's `created_at`, so do not double-filter.

---

## M-001 — Total Calls

**Question**: How many calls landed in this window?

**Grain**: per call.

**Query**:

```sql
SELECT COUNT(*) AS total_calls
FROM calls_log
WHERE created_at >= :window_from
  AND created_at <  :window_to;
```

**Return shape**:

```json
[ { "total_calls": 42 } ]
```

**Null-handling**:

- `COUNT(*)` over an empty filter returns `0`, not null. No COALESCE needed.
- The FastAPI layer returns `{"value": 0}` when the table is empty;
  `safe_count` is unnecessary here.

**WAF**: clean (single equality comparison on a timestamp column, no
quoted-literal lists).

---

## M-080 — Total Bookings

**Question**: How many bookings did the agent close in this window?

**Grain**: per booking (a single call may produce multiple bookings).

**Query**:

```sql
SELECT COUNT(*) AS total_bookings
FROM bookings
WHERE created_at >= :window_from
  AND created_at <  :window_to;
```

**Return shape**:

```json
[ { "total_bookings": 17 } ]
```

**Null-handling**: same as M-001 — empty table returns `0`.

**WAF**: clean.

**Notes**:

- We filter on `bookings.created_at` (mid-call write timestamp) rather than the
  parent calls_log timestamp, because a booking writes to Twin the moment the
  agent commits — that IS the metric's natural time anchor.
- Multi-load calls contribute multiple rows here. That is the design (see
  `dashboard-design-philosophy.md` Principle 2 — multi-load is a positive
  signal, not a partial failure).

---

## M-081 — Calls without Booking

**Question**: How many calls in this window ended without a booking?

**Grain**: per call.

**Query** (NOT EXISTS form, WAF-safe):

```sql
SELECT COUNT(*) AS calls_without_booking
FROM calls_log c
WHERE c.created_at >= :window_from
  AND c.created_at <  :window_to
  AND NOT EXISTS (
    SELECT 1
    FROM bookings b
    WHERE b.call_id = c.call_id
  );
```

**Alternative form** (LEFT JOIN, also WAF-safe — pick whichever your reader
finds clearer; benchmarks were within noise on small Twin tables):

```sql
SELECT COUNT(*) AS calls_without_booking
FROM calls_log c
LEFT JOIN bookings b ON b.call_id = c.call_id
WHERE c.created_at >= :window_from
  AND c.created_at <  :window_to
  AND b.call_id IS NULL;
```

**Return shape**:

```json
[ { "calls_without_booking": 11 } ]
```

**Null-handling**:

- `COUNT(*)` returns `0` over an empty result.
- The EXISTS subquery handles `bookings` being empty cleanly — every call_id
  fails the EXISTS test, so all calls in the window count.
- Per `dashboard-design-philosophy.md` Principle 3, FastAPI surfaces this as
  `{"value": 0}` rather than null when the table is empty.

**WAF**: clean. NOT EXISTS does not trigger Cloudflare's IN-list rule. The
correlated subquery is shallow (single equality) and contains no quoted
literals.

**Anti-pattern this replaces**:

```sql
-- ❌ DO NOT USE — IN-list with subquery is WAF-flagged on some regions
SELECT COUNT(*) FROM calls_log
WHERE call_id NOT IN (SELECT call_id FROM bookings)
  AND created_at >= :window_from AND created_at < :window_to;
```

---

## M-082 — Bookings per Booked Call

**Question**: When carriers DO book, how many loads do they take per call?

**Grain**: ratio (bookings ÷ distinct booked-call IDs).

**Query**:

```sql
SELECT
  COUNT(*)                  AS total_bookings,
  COUNT(DISTINCT call_id)   AS booked_calls
FROM bookings
WHERE created_at >= :window_from
  AND created_at <  :window_to;
```

**Return shape**:

```json
[ { "total_bookings": 17, "booked_calls": 13 } ]
```

The dashboard layer computes the ratio in Python using `safe_pct`-style
division so an empty `bookings` table never crashes:

```python
def bookings_per_booked_call(total: int, booked: int) -> float | None:
    if booked <= 0:
        return None  # surface as "—" in the UI
    return round(total / booked, 2)
```

**Null-handling**:

- Empty bookings table returns `total_bookings=0, booked_calls=0`. The Python
  layer maps that to `None` and the UI shows "—" with caption "Need 1+
  bookings."
- Never return `NaN` or `Infinity` from the API; `None` is the only allowed
  empty signal.

**WAF**: clean.

**Why two columns instead of computing the ratio in SQL**:

- Twin's Postgres handles `total / NULLIF(booked, 0)::float` fine, but pushing
  the division into the API gives us:
  1. A single call that powers BOTH M-080 and M-082 (the FastAPI layer caches
     the SELECT result and computes both metrics from it).
  2. Type-safe handling of the empty case (no `NaN` from a stray cast).
  3. Easier unit testing (a pure Python helper vs a Postgres expression).

---

## M-010 — Revenue Booked

**Question**: How many dollars did the agent close in this window?

**Grain**: sum of booked rates.

**Query**:

```sql
SELECT COALESCE(SUM(apply_rate), 0) AS revenue_booked
FROM bookings
WHERE created_at >= :window_from
  AND created_at <  :window_to;
```

**Return shape**:

```json
[ { "revenue_booked": 31250.0 } ]
```

**Null-handling**:

- `SUM` over an empty set returns `NULL` in Postgres. `COALESCE(SUM(x), 0)`
  forces a numeric `0` for clean JSON serialization.
- `apply_rate` is `NOT NULL` in the bookings DDL, so per-row nullability is
  not a concern.

**WAF**: clean. Single SUM, no quoted lists.

**Notes**:

- This is the headline KPI tile under v15. Under v14 it was
  `SUM(agreed_rate) WHERE call_outcome='load_booked'` against the multi-row
  calls_log; the v15 form is simpler because the bookings table IS the source
  of truth for booked revenue.
- Currency is implicit USD; the dashboard formats to `$1,850.00` at render.

---

## How to verify in Twin REST API

A quick smoke test using the Twin REST endpoint directly. Run from a shell
with `HAPPYROBOT_API_KEY` set:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${HAPPYROBOT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) AS total_calls FROM calls_log WHERE created_at >= '"'"'2026-04-20'"'"' AND created_at < '"'"'2026-04-28'"'"';"}' \
  https://platform.happyrobot.ai/api/v2/twin/sql
```

Expected response:

```json
{ "rows": [ { "total_calls": 42 } ], "count": 1 }
```

If you get `{"error": …}` with a Cloudflare reference number in the body, the
query hit the WAF — the most common cause is an inadvertent IN-list slipping
into the SQL string.

The v15 integration scripts in `tests/integration/v15/` issue exactly these
shape calls (INSERT a few rows, run the SELECT, assert the count, clean up).

---

## Cross-reference — query → metric → test scenario

| Metric                    | Query block       | Test scripts that exercise it    |
|---------------------------|-------------------|----------------------------------|
| M-001 Total Calls         | `M-001` above     | All five (TB1–TB5)               |
| M-080 Total Bookings      | `M-080` above     | TB1, TB2, TB3, TB4               |
| M-081 Calls w/o Booking   | `M-081` above     | TB5 (positive case), TB1/2/3/4 (negative) |
| M-082 Bookings/Booked Call| `M-082` above     | TB2 (multi-load), TB1 (1.0 case) |
| M-010 Revenue Booked      | `M-010` above     | TB1, TB2, TB3 (idempotency), TB4 |

Every TB script asserts at least the metric values that scenario directly
impacts; together they form a full Tier 1 regression suite.
