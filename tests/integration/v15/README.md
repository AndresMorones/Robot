# v15 Integration Tests — Twin REST + Dashboard SQL

Five end-to-end scripts that exercise the v15 two-table architecture
(`calls_log` + `bookings`) by INSERTing simulated rows via the HR Twin REST
SQL endpoint, running the Tier 1 dashboard SQL queries, and asserting the
metric values match expectation. Each script cleans up after itself.

## Index

| Script                                   | Scenario (`docs/test-scenarios.md`) | What it asserts                                                  |
|------------------------------------------|-------------------------------------|------------------------------------------------------------------|
| `tb1_single_booking_simulation.sh`       | TB1 — single-booking happy path     | 1 booking row, 1 calls_log row, M-010 += apply_rate              |
| `tb2_multi_booking_simulation.sh`        | TB2 — multi-booking happy path      | 2 booking rows for one call_id, declined load NOT persisted      |
| `tb3_idempotency.sh`                     | TB3 — duplicate INSERT guard        | UNIQUE (call_id, load_id) rejects the retry; 1 row survives      |
| `tb4_hangup_recovery.sh`                 | TB4 — partial booking + hangup      | Bookings already-recorded survive `call_abandoned` post-call tag |
| `tb5_fmcsa_decline.sh`                   | TB5 — FMCSA decline, zero bookings  | calls_log row exists with NO bookings rows; M-081 += 1           |

## Prerequisites

1. **Schema migrations applied**: `data/twin_schema_v15_calls_log_cleanup.sql`
   then `data/twin_schema_v15_bookings.sql` (paste each statement block into
   the HR Twin SQL editor — see `docs/v15-two-table-schema.md` §"Migration
   order").
2. **`HAPPYROBOT_API_KEY` exported**: the org-level Twin API key. Never
   hardcoded in scripts; never committed.
3. **`bash`, `curl`, `python3`** (for JSON pretty-printing in error messages)
   on `PATH`. `jq` is NOT required — scripts use grep/python fallbacks for
   portability across Git Bash on Windows and macOS/Linux.

## Run a single scenario

```bash
export HAPPYROBOT_API_KEY=hr_…
bash tests/integration/v15/tb1_single_booking_simulation.sh
```

A passing run prints a green `PASS: TB1 …` line and exits 0. A failing run
prints the expected vs actual diff and exits non-zero. Scripts always run
their cleanup block via `trap` so a failure mid-script still removes the
test rows.

## Run all five

From the repo root:

```bash
export HAPPYROBOT_API_KEY=hr_…
for f in tests/integration/v15/tb*.sh; do
  echo "--- Running $f ---"
  bash "$f" || { echo "FAIL: $f"; exit 1; }
done
echo "All 5 v15 scenarios passed."
```

## Local vs deployed

The scripts hit the **HR Twin REST endpoint directly** at
`https://platform.happyrobot.ai/api/v2/twin/sql`. They do NOT route through
your local FastAPI or the deployed Fly app — they are testing the Twin layer
itself.

To verify the dashboard backend serves the same numbers, after a successful
script run hit the dashboard endpoint (locally or deployed) within the same
filter window:

```bash
# Local FastAPI
curl -sS -H "Authorization: Bearer ${API_BEARER_TOKEN}" \
  "http://localhost:8000/v1/dashboard/funnel?window=1d"

# Deployed Fly app
curl -sS -H "Authorization: Bearer ${API_BEARER_TOKEN}" \
  "https://robot-api-andres-morones.fly.dev/v1/dashboard/funnel?window=1d"
```

The dashboard's M-001 / M-080 / M-081 / M-082 / M-010 should reflect the rows
the script INSERTed (until the cleanup block removes them at script exit).

## Idempotency

Every script is idempotent: a clean re-run produces the same pass/fail result.
The `cleanup` function in each script DELETEs by `call_id` LIKE `'tb<N>-%'`
on entry **and** on exit (`trap`), so leftover rows from a crashed run get
swept up by the next invocation.

## How rows are isolated

Each scenario uses a unique `call_id` prefix:

| Scenario | call_id pattern |
|----------|-----------------|
| TB1      | `tb1-<run_id>`  |
| TB2      | `tb2-<run_id>`  |
| TB3      | `tb3-<run_id>`  |
| TB4      | `tb4-<run_id>`  |
| TB5      | `tb5-<run_id>`  |

`<run_id>` is a UUID-like timestamp suffix to avoid collision when two
developers run scripts simultaneously against the same Twin. The MC numbers
(`tb1-mc`, etc.) are chosen to never collide with real FMCSA-valid carriers.

## Adding a new scenario

1. Pick the next free `tb<N>` prefix.
2. Copy `tb1_single_booking_simulation.sh` as a template.
3. Update the scenario doc in `docs/test-scenarios.md` with a new section
   under the same heading style.
4. Add a row to the index table at the top of this README.

## Pairs with

- `docs/test-scenarios.md` — the human-readable test plan
- `docs/v15-dashboard-sql-queries.md` — the SQL each script asserts against
- `docs/v15-two-table-schema.md` — the migration order + ER diagram
- `api/app/services/twin_client.py` — the FastAPI execution path that runs
  the same SQL in production
