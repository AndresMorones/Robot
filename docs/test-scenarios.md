# Test Scenarios — v15 Two-Table Booking Architecture

> Five end-to-end test scenarios validating the `calls_log` (post-call grain) +
> `bookings` (booking grain) split. Each scenario is runnable two ways:
>
> 1. **Real HR test web call** — execute the dialogue against the deployed agent
>    and inspect Twin rows via the HR Twin SQL editor.
> 2. **Twin REST simulation** — run the matching `tests/integration/v15/tb*.sh`
>    script to INSERT the rows that would have been written, then assert
>    dashboard SQL returns the expected metric values.
>
> Pairs with: `docs/v15-two-table-schema.md`,
> `data/twin_schema_v15_bookings.sql`,
> `data/twin_schema_v15_calls_log_cleanup.sql`,
> `docs/v15-dashboard-sql-queries.md`,
> `tests/integration/v15/README.md`.

---

## Coverage matrix

| ID  | Scenario                          | Architecture feature verified                                    | Bookings rows | calls_log rows | Outcome                  |
|-----|-----------------------------------|------------------------------------------------------------------|--------------:|---------------:|--------------------------|
| TB1 | Single-booking happy path         | Mid-call `book_load` → bookings INSERT; post-call calls_log row |             1 |              1 | `load_booked`            |
| TB2 | Multi-booking happy path          | Multiple `book_load` fires per call; declined load NOT persisted |             2 |              1 | `load_booked`            |
| TB3 | Idempotency on duplicate book     | `UNIQUE (call_id, load_id)` rejects HR webhook retry            |             1 |              1 | `load_booked`            |
| TB4 | Mid-call hangup after partial book| `bookings` survives independently of calls_log writer           |             1 |              1 | `call_abandoned`         |
| TB5 | FMCSA decline (zero bookings)     | calls_log writes without any companion bookings row              |             0 |              1 | `carrier_not_qualified`  |

Tier 1 dashboard metrics each scenario impacts:

| ID  | M-001 Total Calls | M-080 Total Bookings | M-081 Calls w/o Booking | M-082 Bookings/Booked Call | M-010 Revenue Booked |
|-----|------------------:|---------------------:|------------------------:|---------------------------:|---------------------:|
| TB1 |                +1 |                   +1 |                       0 |                       1.00 |              +$1,850 |
| TB2 |                +1 |                   +2 |                       0 |                       2.00 |              +$2,800 |
| TB3 |                +1 |                   +1 |                       0 |                       1.00 |              +$1,850 |
| TB4 |                +1 |                   +1 |                       0 |                       1.00 |              +$1,850 |
| TB5 |                +1 |                    0 |                      +1 |                       n/a  |                   $0 |

Aggregated across all five (clean run, no duplicates surviving): **5 calls,
5 bookings, 1 call without a booking, 1.25 bookings per booked call,
$8,350 revenue booked**.

---

## TB1 — Single-booking happy path

### Preconditions

- HR agent running on `inbound-carrier-v4`.
- `loads` table seeded; `LOAD-188` exists with a listed rate around $1,900–$2,000.
- MC `123456` returns FMCSA-eligible (active, authorized).
- `calls_log` and `bookings` tables created per migrations.

### Conversation script

| Turn  | Speaker | Line                                                                                          |
|-------|---------|-----------------------------------------------------------------------------------------------|
| 1     | Agent   | "Carrier sales, who am I speaking with?"                                                      |
| 2     | Carrier | "This is Mike with MC 123456 — I'm looking for a dry van out of Dallas to Atlanta."           |
| 3     | Agent   | (fires `verify_carrier`) "Got you, Mike. Confirming Acme Trucking — that you?"                |
| 4     | Carrier | "Yep."                                                                                        |
| 5     | Agent   | (fires `search_loads_by_lane`) "Got LOAD-188, Dallas-Atlanta dry van, picks up tomorrow at $1,900." |
| 6     | Carrier | "Best you can do is $1,850?"                                                                  |
| 7     | Agent   | "I can do $1,850. Booking it — fires `book_load(load_id=LOAD-188, apply_rate=1850)`."         |
| 8     | Carrier | "Appreciate it, talk soon."                                                                   |
| 9     | Agent   | (ends call gracefully)                                                                        |

### Tool fires expected

- `verify_carrier` — once, MC 123456, returns eligible.
- `search_loads_by_lane` — once, returns ≥1 row including LOAD-188.
- `book_load` — exactly once, `(call_id=<HR call_id>, load_id="LOAD-188", apply_rate=1850, mc_number="123456")`.

### Twin row state expected post-call

`bookings` (1 row):

| call_id  | mc_number | load_id   | apply_rate |
|----------|-----------|-----------|-----------:|
| `tb1-…`  | 123456    | LOAD-188  |     1850.0 |

`calls_log` (1 row):

| call_id  | mc_number | call_outcome  | sentiment | case_health_score | fmcsa_eligibility_failure_reason |
|----------|-----------|---------------|-----------|------------------:|----------------------------------|
| `tb1-…`  | 123456    | `load_booked` | positive  |              ≥ 85 | NULL                             |

### Dashboard verification queries

After the call lands, the dashboard SQL in `docs/v15-dashboard-sql-queries.md`
should return:

```sql
-- M-080 confirmation: bookings recorded
SELECT COUNT(*) AS n FROM bookings WHERE call_id = 'tb1-001';
-- → 1
```

```sql
-- M-010 confirmation: revenue logged
SELECT SUM(apply_rate) AS revenue FROM bookings WHERE call_id = 'tb1-001';
-- → 1850
```

```sql
-- M-081 confirmation: this call IS booked, so it should NOT appear in calls-without-booking
SELECT COUNT(*) AS n FROM calls_log c
WHERE c.call_id = 'tb1-001'
  AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);
-- → 0
```

### Runner

```bash
HAPPYROBOT_API_KEY=… bash tests/integration/v15/tb1_single_booking_simulation.sh
```

---

## TB2 — Multi-booking happy path

### Preconditions

- Same as TB1.
- `LOAD-201`, `LOAD-188`, `LOAD-244` all present in `loads`.
- Carrier intends to take two loads in one conversation.

### Conversation script

| Turn  | Speaker | Line                                                                                                  |
|-------|---------|-------------------------------------------------------------------------------------------------------|
| 1     | Agent   | "Carrier sales, who am I speaking with?"                                                              |
| 2     | Carrier | "Mike, MC 123456, I've got a truck in Texas and another empty in Georgia tonight — what do you have?" |
| 3     | Agent   | (fires `verify_carrier`) "Confirmed Acme Trucking. Pulling lanes."                                    |
| 4     | Agent   | (fires `search_loads_by_lane`) "Got LOAD-201 Houston-Memphis at $2,000, LOAD-188 Dallas-Atlanta at $1,900, LOAD-244 Atlanta-Charlotte at $1,000." |
| 5     | Carrier | "LOAD-201 is too cheap. LOAD-188 at $1,850?"                                                          |
| 6     | Agent   | "Done. (fires `book_load(LOAD-188, 1850)`) — what about the Georgia truck?"                           |
| 7     | Carrier | "LOAD-244 at $950."                                                                                   |
| 8     | Agent   | "Done — (fires `book_load(LOAD-244, 950)`). Two loads booked, anything else?"                         |
| 9     | Carrier | "That's it, thanks."                                                                                  |
| 10    | Agent   | (ends call gracefully)                                                                                |

### Tool fires expected

- `verify_carrier` — once.
- `search_loads_by_lane` — once or twice (if agent re-searches for the GA truck).
- `book_load` — **twice**, in order:
  1. `(call_id=<x>, load_id="LOAD-188", apply_rate=1850, mc_number="123456")`
  2. `(call_id=<x>, load_id="LOAD-244", apply_rate=950, mc_number="123456")`
- LOAD-201 — **NOT** booked. The declined-load decision lives only in the
  transcript; no row is written for it anywhere.

### Twin row state expected post-call

`bookings` (2 rows, same `call_id`):

| call_id  | mc_number | load_id   | apply_rate |
|----------|-----------|-----------|-----------:|
| `tb2-…`  | 123456    | LOAD-188  |     1850.0 |
| `tb2-…`  | 123456    | LOAD-244  |      950.0 |

`calls_log` (1 row):

| call_id  | mc_number | call_outcome  | sentiment | case_health_score |
|----------|-----------|---------------|-----------|------------------:|
| `tb2-…`  | 123456    | `load_booked` | positive  |              ≥ 85 |

**Critical assertion**: a search for any row referencing `LOAD-201` in
`bookings` for this `call_id` returns zero rows. The declined load is NOT
persisted.

### Dashboard verification queries

```sql
-- M-080: two bookings landed
SELECT COUNT(*) AS n FROM bookings WHERE call_id = 'tb2-001';
-- → 2
```

```sql
-- M-082 numerator + denominator for this call
SELECT COUNT(*) AS bookings, COUNT(DISTINCT call_id) AS booked_calls
FROM bookings WHERE call_id = 'tb2-001';
-- → bookings=2, booked_calls=1, ratio = 2.0
```

```sql
-- Declined-load assertion: LOAD-201 must NOT appear
SELECT COUNT(*) AS n FROM bookings WHERE call_id = 'tb2-001' AND load_id = 'LOAD-201';
-- → 0
```

### Runner

```bash
HAPPYROBOT_API_KEY=… bash tests/integration/v15/tb2_multi_booking_simulation.sh
```

---

## TB3 — Idempotency on duplicate `book_load`

### Preconditions

- Same as TB1.
- HR's Write-to-Twin component retries on transient failure; the `bookings`
  table holds `UNIQUE (call_id, load_id)`.

### Conversation script

Identical to TB1. The retry happens at the HR Write-to-Twin layer, not in the
voice flow — the carrier and agent see the booking succeed once.

### Tool fires expected

- `book_load` fires once from the Voice Agent's perspective.
- HR Write-to-Twin issues an INSERT; the first INSERT succeeds.
- HR Write-to-Twin retries the same INSERT (network blip / 5xx simulation).
  Postgres rejects the duplicate with constraint violation
  `bookings_call_load_uniq`. HR's Write-to-Twin treats the unique-violation as
  a benign no-op (writes succeeded once already).

### Twin row state expected post-call

`bookings` — exactly **one** row, not two:

| call_id  | mc_number | load_id   | apply_rate |
|----------|-----------|-----------|-----------:|
| `tb3-…`  | 123456    | LOAD-188  |     1850.0 |

`calls_log` — exactly one row, `load_booked`.

### Dashboard verification queries

```sql
-- Idempotency assertion: still exactly one bookings row
SELECT COUNT(*) AS n FROM bookings WHERE call_id = 'tb3-001';
-- → 1 (NOT 2)
```

```sql
-- Revenue not double-counted
SELECT SUM(apply_rate) AS revenue FROM bookings WHERE call_id = 'tb3-001';
-- → 1850 (NOT 3700)
```

The script directly attempts a duplicate INSERT and asserts the second one
fails with a uniqueness violation. The Twin REST `/twin/sql` endpoint surfaces
the constraint name in the error body — the script greps for
`bookings_call_load_uniq`.

### Runner

```bash
HAPPYROBOT_API_KEY=… bash tests/integration/v15/tb3_idempotency.sh
```

---

## TB4 — Mid-call hangup after partial bookings

### Preconditions

- Same as TB1.
- Carrier disconnects mid-conversation after the first booking succeeds but
  before the agent can offer or book a second load.

### Conversation script

| Turn  | Speaker | Line                                                                                  |
|-------|---------|---------------------------------------------------------------------------------------|
| 1     | Agent   | "Carrier sales, who am I speaking with?"                                              |
| 2     | Carrier | "Mike, MC 123456, dry van Dallas-Atlanta and another for the GA truck if you have one." |
| 3     | Agent   | (fires `verify_carrier` + `search_loads_by_lane`) "Confirmed. LOAD-188 Dallas-Atlanta $1,900." |
| 4     | Carrier | "$1,850 and book it."                                                                 |
| 5     | Agent   | (fires `book_load(LOAD-188, 1850)`) "Booked. About the GA truck — got LOAD-244…"       |
| 6     | Carrier | *(call drops — silence / disconnect)*                                                  |
| 7     | Agent   | (post-call extraction tags `call_abandoned`)                                          |

### Tool fires expected

- `verify_carrier` — once.
- `search_loads_by_lane` — once.
- `book_load` — **once** (LOAD-188 only, before the drop).
- No `book_load` for LOAD-244.

### Twin row state expected post-call

`bookings` (1 row — the one that landed before the disconnect):

| call_id  | mc_number | load_id   | apply_rate |
|----------|-----------|-----------|-----------:|
| `tb4-…`  | 123456    | LOAD-188  |     1850.0 |

`calls_log` (1 row, written by post-call extraction with the abandon tag):

| call_id  | mc_number | call_outcome     | sentiment | case_health_score |
|----------|-----------|------------------|-----------|------------------:|
| `tb4-…`  | 123456    | `call_abandoned` | neutral   |     50–80 (deduct for hangup) |

**Critical invariant**: the booking that completed BEFORE the hangup survives
in `bookings` even though the call ultimately tagged as abandoned. The dashboard
counts the booking as revenue and the call as abandoned. They reconcile via
`call_id` JOIN at query time.

### Dashboard verification queries

```sql
-- Booking survived
SELECT COUNT(*) AS n FROM bookings WHERE call_id = 'tb4-001';
-- → 1
```

```sql
-- Call tagged abandoned, but is NOT in calls-without-booking
-- (because a booking row exists for it)
SELECT COUNT(*) AS n
FROM calls_log c
WHERE c.call_id = 'tb4-001'
  AND c.call_outcome = 'call_abandoned'
  AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);
-- → 0
```

### Runner

```bash
HAPPYROBOT_API_KEY=… bash tests/integration/v15/tb4_hangup_recovery.sh
```

---

## TB5 — FMCSA decline (zero bookings)

### Preconditions

- Same as TB1.
- MC `999000` returns FMCSA `INACTIVE` (or any non-eligible status).

### Conversation script

| Turn  | Speaker | Line                                                                              |
|-------|---------|-----------------------------------------------------------------------------------|
| 1     | Agent   | "Carrier sales, who am I speaking with?"                                          |
| 2     | Carrier | "John, MC 999000, looking for a load."                                            |
| 3     | Agent   | (fires `verify_carrier`) — returns INACTIVE.                                      |
| 4     | Agent   | "Hey John, I appreciate the call but FMCSA is showing your authority as inactive — I'm not able to book this one. Worth giving them a shout to clear it." |
| 5     | Carrier | "Got it, thanks."                                                                 |
| 6     | Agent   | (ends call politely)                                                              |

### Tool fires expected

- `verify_carrier` — once, returns ineligible (status=INACTIVE).
- `search_loads_by_lane` — **NOT** fired (gated on FMCSA pass).
- `book_load` — **NOT** fired.

### Twin row state expected post-call

`bookings` — **zero rows**.

`calls_log` (1 row):

| call_id  | mc_number | call_outcome           | sentiment | case_health_score | fmcsa_eligibility_failure_reason |
|----------|-----------|------------------------|-----------|------------------:|----------------------------------|
| `tb5-…`  | 999000    | `carrier_not_qualified`| positive  |              ≥ 90 | INACTIVE                         |

**Customer-experience principle**: a polite decline still scores high CHS —
this is per `docs/dashboard-design-philosophy.md` Principle 1 ("legitimate
business outcomes don't penalize health scores").

### Dashboard verification queries

```sql
-- M-081: this call is in the calls-without-booking bucket
SELECT COUNT(*) AS n
FROM calls_log c
WHERE c.call_id = 'tb5-001'
  AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);
-- → 1
```

```sql
-- Zero bookings rows for this call
SELECT COUNT(*) AS n FROM bookings WHERE call_id = 'tb5-001';
-- → 0
```

```sql
-- FMCSA failure reason captured
SELECT fmcsa_eligibility_failure_reason FROM calls_log WHERE call_id = 'tb5-001';
-- → 'INACTIVE'
```

### Runner

```bash
HAPPYROBOT_API_KEY=… bash tests/integration/v15/tb5_fmcsa_decline.sh
```

---

## How to run all scenarios

```bash
cd c:/Users/Andre/OneDrive/Documentos/GitHub/Robot
export HAPPYROBOT_API_KEY=hr_…   # never commit
for f in tests/integration/v15/tb*.sh; do
  bash "$f" || { echo "FAIL: $f"; exit 1; }
done
echo "All 5 v15 scenarios passed."
```

Each script is idempotent — it cleans up its rows on exit so a re-run produces
the same result. See `tests/integration/v15/README.md` for per-script details
and how to run against a deployed Fly app.
