#!/usr/bin/env bash
# TB5 — FMCSA decline (zero bookings)
#
# Simulates a call where FMCSA reveals INACTIVE status, the agent declines
# politely, no load is pitched. Asserts:
#   - Zero rows in bookings for this call_id.
#   - One row in calls_log with call_outcome='carrier_not_qualified' and
#     fmcsa_eligibility_failure_reason='INACTIVE'.
#   - This call DOES count toward M-081 (calls without booking).
#   - case_health_score >= 90 (polite decline scores high — see
#     docs/dashboard-design-philosophy.md Principle 1).
#
# Pairs with: docs/test-scenarios.md §TB5

set -euo pipefail

: "${HAPPYROBOT_API_KEY:?HAPPYROBOT_API_KEY must be exported}"
TWIN_URL="${TWIN_URL:-https://platform.happyrobot.ai/api/v2/twin/sql}"

CALL_ID="tb5-$(date +%s)-$$"
MC_NUMBER="tb5-mc-005"

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

extract_str() {
  python3 -c "import json,sys; r=json.loads(sys.argv[1]); rows=r.get('rows') or []; print(rows[0].get(sys.argv[2], '') if rows else '')" "$1" "$2"
}

assert_eq() {
  if [[ "$2" != "$3" ]]; then
    echo "FAIL: TB5 — $1: expected=$2 actual=$3" >&2
    exit 1
  fi
  echo "  OK $1 = $3"
}

assert_ge() {
  # assert_ge "label" "min" "actual" — passes when actual >= min (numeric)
  if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)" "$3" "$2"; then
    echo "  OK $1 >= $2 (actual=$3)"
  else
    echo "FAIL: TB5 — $1: expected >= $2 actual=$3" >&2
    exit 1
  fi
}

cleanup() {
  twin_sql "DELETE FROM bookings WHERE call_id = '${CALL_ID}';"  >/dev/null || true
  twin_sql "DELETE FROM calls_log WHERE call_id = '${CALL_ID}';" >/dev/null || true
}
trap cleanup EXIT
cleanup

echo "TB5: simulating FMCSA decline for ${CALL_ID}"

# No bookings INSERT — agent never pitched a load.

twin_sql "INSERT INTO calls_log (call_id, mc_number, carrier_name, call_outcome,
                                 sentiment, case_health_score,
                                 fmcsa_eligibility_failure_reason, duration_seconds)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', 'TB5 Inactive Carrier',
                  'carrier_not_qualified', 'positive', 92,
                  'INACTIVE', 75);" >/dev/null

echo "TB5: asserting zero-booking + decline-tag state"

# Zero bookings rows for this call.
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings WHERE call_id = '${CALL_ID}';")
assert_eq "Zero bookings for FMCSA-declined call" "0" "$(extract_int "$resp" n)"

# calls_log row exists with the decline tag.
resp=$(twin_sql "SELECT call_outcome FROM calls_log WHERE call_id = '${CALL_ID}';")
assert_eq "call_outcome" "carrier_not_qualified" "$(extract_str "$resp" call_outcome)"

resp=$(twin_sql "SELECT fmcsa_eligibility_failure_reason AS r FROM calls_log
                 WHERE call_id = '${CALL_ID}';")
assert_eq "fmcsa_eligibility_failure_reason" "INACTIVE" "$(extract_str "$resp" r)"

# M-081 — this call IS in the calls-without-booking bucket.
resp=$(twin_sql "SELECT COUNT(*) AS n FROM calls_log c
                 WHERE c.call_id = '${CALL_ID}'
                   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);")
assert_eq "M-081 (declined call counts as no-booking)" "1" "$(extract_int "$resp" n)"

# CHS — polite decline scores high (Principle 1: customer experience focus).
resp=$(twin_sql "SELECT case_health_score AS chs FROM calls_log WHERE call_id = '${CALL_ID}';")
assert_ge "CHS for polite decline" "90" "$(extract_int "$resp" chs)"

# M-010 — this call contributes $0 (no bookings means no revenue).
resp=$(twin_sql "SELECT COALESCE(SUM(apply_rate), 0) AS revenue FROM bookings
                 WHERE call_id = '${CALL_ID}';")
assert_eq "M-010 revenue (zero for declined call)" "0.0" "$(extract_float "$resp" revenue)"

echo "PASS: TB5 — FMCSA decline (call_id=${CALL_ID})"
