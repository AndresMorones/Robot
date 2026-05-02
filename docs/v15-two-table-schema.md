# v15 Two-Table Schema — calls_log + bookings

## Purpose

The v15 architecture splits call-level state and booking-level state into two
tables joined on `call_id`. This replaces the v14 multi-load Loop pattern, which
encoded bookings as additional `calls_log` rows discriminated by `booking_seq`.

### `calls_log` — post-call grain

One row per call, written once at call-end by the HR post-call extraction +
classification chain. Holds carrier identity, call outcome, sentiment, audit
remarks, the Case Health Score, FMCSA failure reason, callback phone, duration,
and the full transcript. Zero load-specific fields — those live in `bookings`.

### `bookings` — booking grain

One row per booking, written mid-call the moment the HR `book_load` tool fires
through the Write-to-Twin component. Each row points back to its call via
`call_id` and to the booked load via `load_id`. The mid-call write means the
dashboard can show "N bookings in flight right now" without waiting for the
post-call chain to finish.

## Final `calls_log` columns

| Column                            | Type             | Notes                                                |
|-----------------------------------|------------------|------------------------------------------------------|
| id                                | BIGSERIAL        | PK                                                   |
| created_at                        | TIMESTAMPTZ      | DEFAULT NOW()                                        |
| call_id                           | TEXT             | UNIQUE — natural key from HR                         |
| mc_number                         | TEXT             |                                                      |
| carrier_name                      | TEXT             |                                                      |
| call_outcome                      | TEXT             | Classify Outcome enum                                |
| sentiment                         | TEXT             | Classify Sentiment enum                              |
| case_health_score                 | BIGINT           | 0–100, deduction model                               |
| audit_remarks                     | TEXT             | Case Health Score reasoning text                     |
| fmcsa_eligibility_failure_reason  | TEXT             | Set when FMCSA decline closes the call               |
| callback_phone                    | TEXT             | Extract.response.callback_phone                      |
| duration_seconds                  | BIGINT           | Total call wall-clock                                |
| transcript                        | TEXT             | Full call transcript                                 |

## Final `bookings` columns

| Column      | Type             | Notes                                          |
|-------------|------------------|------------------------------------------------|
| id          | BIGSERIAL        | PK                                             |
| created_at  | TIMESTAMPTZ      | DEFAULT NOW(), mid-call write timestamp        |
| call_id     | TEXT             | NOT NULL, JOIN key back to calls_log.call_id   |
| mc_number   | TEXT             | NOT NULL, denormalized for carrier lookup      |
| load_id     | TEXT             | NOT NULL, points at loads.load_id              |
| apply_rate  | DOUBLE PRECISION | NOT NULL, the booked rate                      |

Constraints + indexes on `bookings`:

- `UNIQUE (call_id, load_id)` — idempotency guard against webhook retries.
- `INDEX (created_at DESC)` — dashboard time-window queries.
- `INDEX (call_id)` — JOIN to calls_log.
- `INDEX (mc_number)` — carrier lookup.
- `INDEX (load_id)` — popular-loads metric.

## ER diagram

```
+-----------------------------+              +--------------------------------+
|         calls_log           |              |           bookings             |
+-----------------------------+              +--------------------------------+
| id              BIGSERIAL PK|              | id            BIGSERIAL PK     |
| created_at      TIMESTAMPTZ |              | created_at    TIMESTAMPTZ      |
| call_id         TEXT UNIQUE |<------------ | call_id       TEXT NOT NULL    |
| mc_number       TEXT        |   1 : 0..N   | mc_number     TEXT NOT NULL    |
| carrier_name    TEXT        |              | load_id       TEXT NOT NULL ---+--> loads.load_id
| call_outcome    TEXT        |              | apply_rate    DOUBLE NOT NULL  |
| sentiment       TEXT        |              +--------------------------------+
| case_health_score BIGINT    |              UNIQUE (call_id, load_id)
| audit_remarks   TEXT        |
| fmcsa_eligibility_           |
|   failure_reason TEXT       |
| callback_phone  TEXT        |
| duration_seconds BIGINT     |
| transcript      TEXT        |
+-----------------------------+
```

A call can have zero bookings (declined, FMCSA fail, hangup) or many bookings
(carrier books multiple loads in one conversation). The relationship is
informal — there is no formal FOREIGN KEY because HR Twin write ordering is not
guaranteed (mid-call `bookings` writes can land before the post-call
`calls_log` write). Application-layer JOINs are LEFT JOINs from `calls_log`.

## Idempotency rationale

HR webhooks retry on transient failures — network blips, 5xx responses, timeout
on the Twin side. Without a uniqueness guard, a retried `book_load` fire would
double-count revenue and inflate the popular-loads metric. The natural key for
"this exact booking" is `(call_id, load_id)`: a single call can book the same
load at most once, regardless of how many times the webhook fires. Postgres
rejects the duplicate INSERT with constraint violation `bookings_call_load_uniq`,
which HR's Write-to-Twin component treats as a benign no-op.

We deliberately do NOT include `apply_rate` in the uniqueness key. If a retry
ever carried a different rate (it shouldn't), we want the loud failure.

## Migration order

Run in this exact sequence against the live HR Twin (zero production rows, so
the cleanup is non-destructive):

1. **`data/twin_schema_v15_calls_log_cleanup.sql`** — strips load-grain columns
   and indexes from `calls_log`, promotes `call_id` to UNIQUE. 9 statements.
2. **`data/twin_schema_v15_bookings.sql`** — creates the `bookings` table,
   uniqueness constraint, and 4 indexes. 6 statements.
3. **Verify** with empty SELECTs in the HR Twin SQL editor:

   ```sql
   SELECT COUNT(*) FROM calls_log;
   ```

   ```sql
   SELECT COUNT(*) FROM bookings;
   ```

   Both should return `0`. Then sanity-check the column list:

   ```sql
   SELECT column_name FROM information_schema.columns WHERE table_name = 'calls_log' ORDER BY ordinal_position;
   ```

   ```sql
   SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings' ORDER BY ordinal_position;
   ```

   Expect the 13 calls_log columns and 6 bookings columns listed above.

Each SQL file is split on `-- === STATEMENT BREAK ===` markers because the HR
Twin SQL editor accepts only a single statement per submission. Paste one block
at a time.
