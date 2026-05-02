#!/usr/bin/env bash
# TB2 — Multi-booking happy path
#
# Simulates a single call_id that books TWO loads (LOAD-188 at $1850, LOAD-244
# at $950) and DECLINES a third (LOAD-201). Asserts:
#   - 2 bookings rows, both pointing at the same call_id
#   - LOAD-201 NOT present in bookings (declined load not persisted anywhere
#     except the transcript, which we don't write here)
#   - M-082 ratio = 2.0 for this call_id
#   - M-010 revenue = $1850 + $950 = $2800
#
# Pairs with: docs/test-scenarios.md §TB2

set -euo pipefail

: "${HAPPYROBOT_API_KEY:?HAPPYROBOT_API_KEY must be exported}"
TWIN_URL="${TWIN_URL:-https://platform.happyrobot.ai/api/v2/twin/sql}"

CALL_ID="tb2-$(date +%s)-$$"
MC_NUMBER="tb2-mc-002"

twin_sql() {
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
  python3 -c "import json,sys; r=json.loads(sys.argv[1]); rows=r.get('rows') or []; print(int(rows[0].get(sys.argv[2], 0)) if rows else 0)" "$1" "$2"
}

extract_float() {
  python3 -c "import json,sys; r=json.loads(sys.argv[1]); rows=r.get('rows') or []; print(float(rows[0].get(sys.argv[2], 0.0)) if rows else 0.0)" "$1" "$2"
}

assert_eq() {
  if [[ "$2" != "$3" ]]; then
    echo "FAIL: TB2 — $1: expected=$2 actual=$3" >&2
    exit 1
  fi
  echo "  OK $1 = $3"
}

cleanup() {
  twin_sql "DELETE FROM bookings WHERE call_id = '${CALL_ID}';"  >/dev/null || true
  twin_sql "DELETE FROM calls_log WHERE call_id = '${CALL_ID}';" >/dev/null || true
}
trap cleanup EXIT
cleanup

echo "TB2: simulating multi-booking call ${CALL_ID}"

# Two book_load fires → two bookings rows for the same call_id.
twin_sql "INSERT INTO bookings (call_id, mc_number, load_id, apply_rate)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', 'LOAD-188', 1850.0);" >/dev/null
twin_sql "INSERT INTO bookings (call_id, mc_number, load_id, apply_rate)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', 'LOAD-244', 950.0);" >/dev/null

# LOAD-201 was declined — explicitly NOT inserted. Asserted below.

twin_sql "INSERT INTO calls_log (call_id, mc_number, carrier_name, call_outcome,
                                 sentiment, case_health_score, duration_seconds)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', 'TB2 Acme Trucking',
                  'load_booked', 'positive', 88, 240);" >/dev/null

echo "TB2: asserting multi-booking row state"

# M-080 — exactly 2 bookings for this call
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings WHERE call_id = '${CALL_ID}';")
assert_eq "M-080 bookings count" "2" "$(extract_int "$resp" n)"

# Declined-load assertion: LOAD-201 must NOT be in bookings
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings
                 WHERE call_id = '${CALL_ID}' AND load_id = 'LOAD-201';")
assert_eq "Declined LOAD-201 not persisted" "0" "$(extract_int "$resp" n)"

# Booked loads ARE present (sanity)
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings
                 WHERE call_id = '${CALL_ID}' AND load_id = 'LOAD-188';")
assert_eq "LOAD-188 persisted" "1" "$(extract_int "$resp" n)"
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings
                 WHERE call_id = '${CALL_ID}' AND load_id = 'LOAD-244';")
assert_eq "LOAD-244 persisted" "1" "$(extract_int "$resp" n)"

# M-082 — bookings per booked call for this call_id: 2 / 1 = 2.0
resp=$(twin_sql "SELECT COUNT(*) AS bookings, COUNT(DISTINCT call_id) AS booked_calls
                 FROM bookings WHERE call_id = '${CALL_ID}';")
assert_eq "M-082 numerator" "2" "$(extract_int "$resp" bookings)"
assert_eq "M-082 denominator" "1" "$(extract_int "$resp" booked_calls)"

# M-010 — revenue across both bookings
resp=$(twin_sql "SELECT COALESCE(SUM(apply_rate), 0) AS revenue FROM bookings
                 WHERE call_id = '${CALL_ID}';")
assert_eq "M-010 revenue (1850 + 950)" "2800.0" "$(extract_float "$resp" revenue)"

# M-081 — this call IS booked, so it should NOT count in calls-without-booking
resp=$(twin_sql "SELECT COUNT(*) AS n FROM calls_log c
                 WHERE c.call_id = '${CALL_ID}'
                   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);")
assert_eq "M-081 (this call is booked)" "0" "$(extract_int "$resp" n)"

# calls_log invariant — exactly ONE row regardless of bookings count
resp=$(twin_sql "SELECT COUNT(*) AS n FROM calls_log WHERE call_id = '${CALL_ID}';")
assert_eq "calls_log row count (one per call)" "1" "$(extract_int "$resp" n)"

echo "PASS: TB2 — multi-booking happy path (call_id=${CALL_ID})"
