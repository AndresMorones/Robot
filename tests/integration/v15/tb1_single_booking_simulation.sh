#!/usr/bin/env bash
# TB1 — Single-booking happy path
#
# Simulates a carrier call that books LOAD-188 at $1850, then runs the Tier 1
# dashboard SQL queries (M-001, M-080, M-081, M-082, M-010) and asserts each
# returns the expected value for this call_id.
#
# Cleanup is registered via `trap` so any failure mid-script still DELETEs the
# test rows. Re-runnable; produces the same pass/fail result every time.
#
# Pairs with:
#   - docs/test-scenarios.md §TB1
#   - docs/v15-dashboard-sql-queries.md
#   - data/twin_schema_v15_bookings.sql

set -euo pipefail

# --------------------------------------------------------------------------- env
: "${HAPPYROBOT_API_KEY:?HAPPYROBOT_API_KEY must be exported}"
TWIN_URL="${TWIN_URL:-https://platform.happyrobot.ai/api/v2/twin/sql}"

CALL_ID="tb1-$(date +%s)-$$"
MC_NUMBER="tb1-mc-001"
LOAD_ID="LOAD-188"
APPLY_RATE="1850.0"

# ----------------------------------------------------------------------- helpers
twin_sql() {
  # twin_sql "<single statement SQL>" -> stdout = response body
  local sql="$1"
  local body
  body=$(printf '{"sql": %s}' "$(printf '%s' "$sql" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")
  curl -sS -X POST \
    -H "Authorization: Bearer ${HAPPYROBOT_API_KEY}" \
    -H "Content-Type: application/json" \
    --data "$body" \
    "$TWIN_URL"
}

extract_int() {
  # Pull a single integer-valued column from a Twin SQL response by name.
  # extract_int "$response" "n" -> "1"
  python3 -c "import json,sys; r=json.loads(sys.argv[1]); rows=r.get('rows') or []; print(int(rows[0].get(sys.argv[2], 0)) if rows else 0)" "$1" "$2"
}

extract_float() {
  python3 -c "import json,sys; r=json.loads(sys.argv[1]); rows=r.get('rows') or []; print(float(rows[0].get(sys.argv[2], 0.0)) if rows else 0.0)" "$1" "$2"
}

assert_eq() {
  # assert_eq "label" "expected" "actual"
  if [[ "$2" != "$3" ]]; then
    echo "FAIL: TB1 — $1: expected=$2 actual=$3" >&2
    exit 1
  fi
  echo "  OK $1 = $3"
}

# ----------------------------------------------------------------------- cleanup
cleanup() {
  twin_sql "DELETE FROM bookings WHERE call_id = '${CALL_ID}';"  >/dev/null || true
  twin_sql "DELETE FROM calls_log WHERE call_id = '${CALL_ID}';" >/dev/null || true
}
trap cleanup EXIT

# Pre-emptive cleanup in case a prior crashed run left rows behind.
cleanup

# ------------------------------------------------------------------- simulate
echo "TB1: simulating single-booking call ${CALL_ID}"

twin_sql "INSERT INTO bookings (call_id, mc_number, load_id, apply_rate)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', '${LOAD_ID}', ${APPLY_RATE});" >/dev/null

twin_sql "INSERT INTO calls_log (call_id, mc_number, carrier_name, call_outcome,
                                 sentiment, case_health_score, duration_seconds)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', 'TB1 Acme Trucking',
                  'load_booked', 'positive', 90, 180);" >/dev/null

# -------------------------------------------------------------------- assert
echo "TB1: asserting Tier 1 metrics for ${CALL_ID}"

# M-001 — Total Calls (this call_id contributes 1)
resp=$(twin_sql "SELECT COUNT(*) AS n FROM calls_log WHERE call_id = '${CALL_ID}';")
assert_eq "M-001 Total Calls" "1" "$(extract_int "$resp" n)"

# M-080 — Total Bookings (this call_id contributes 1)
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings WHERE call_id = '${CALL_ID}';")
assert_eq "M-080 Total Bookings" "1" "$(extract_int "$resp" n)"

# M-081 — Calls without Booking (this call IS booked → 0)
resp=$(twin_sql "SELECT COUNT(*) AS n FROM calls_log c
                 WHERE c.call_id = '${CALL_ID}'
                   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);")
assert_eq "M-081 Calls w/o Booking (this call)" "0" "$(extract_int "$resp" n)"

# M-082 — Bookings per Booked Call (this call: 1/1 = 1.0)
resp=$(twin_sql "SELECT COUNT(*) AS bookings, COUNT(DISTINCT call_id) AS booked_calls
                 FROM bookings WHERE call_id = '${CALL_ID}';")
b=$(extract_int "$resp" bookings)
bc=$(extract_int "$resp" booked_calls)
assert_eq "M-082 numerator (bookings)" "1" "$b"
assert_eq "M-082 denominator (booked_calls)" "1" "$bc"

# M-010 — Revenue Booked (this call contributes apply_rate)
resp=$(twin_sql "SELECT COALESCE(SUM(apply_rate), 0) AS revenue FROM bookings
                 WHERE call_id = '${CALL_ID}';")
assert_eq "M-010 Revenue Booked" "1850.0" "$(extract_float "$resp" revenue)"

echo "PASS: TB1 — single-booking happy path (call_id=${CALL_ID})"
