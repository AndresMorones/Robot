#!/usr/bin/env bash
# TB4 — Mid-call hangup after partial bookings
#
# Simulates a call that books LOAD-188 successfully, then disconnects before
# any further bookings. Asserts:
#   - The completed booking SURVIVES in `bookings`.
#   - The post-call extractor writes a `calls_log` row with
#     call_outcome='call_abandoned'.
#   - M-081 (calls without booking) does NOT include this call — it has at
#     least one booking row, even though the call ultimately abandoned.
#
# Pairs with: docs/test-scenarios.md §TB4

set -euo pipefail

: "${HAPPYROBOT_API_KEY:?HAPPYROBOT_API_KEY must be exported}"
TWIN_URL="${TWIN_URL:-https://platform.happyrobot.ai/api/v2/twin/sql}"

CALL_ID="tb4-$(date +%s)-$$"
MC_NUMBER="tb4-mc-004"
LOAD_ID="LOAD-188"
APPLY_RATE="1850.0"

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
    echo "FAIL: TB4 — $1: expected=$2 actual=$3" >&2
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

echo "TB4: simulating partial-booking + hangup for ${CALL_ID}"

# Step 1: mid-call book_load fires successfully — bookings row lands.
twin_sql "INSERT INTO bookings (call_id, mc_number, load_id, apply_rate)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', '${LOAD_ID}', ${APPLY_RATE});" >/dev/null

# Step 2: call drops mid-conversation, post-call extractor tags it abandoned.
twin_sql "INSERT INTO calls_log (call_id, mc_number, carrier_name, call_outcome,
                                 sentiment, case_health_score, duration_seconds)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', 'TB4 Acme Trucking',
                  'call_abandoned', 'neutral', 65, 95);" >/dev/null

echo "TB4: asserting booking survived the abandon"

# Booking row survives.
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings WHERE call_id = '${CALL_ID}';")
assert_eq "Booking row survived hangup" "1" "$(extract_int "$resp" n)"

# Revenue counted (the booked load is real money even if the call abandoned).
resp=$(twin_sql "SELECT COALESCE(SUM(apply_rate), 0) AS revenue FROM bookings
                 WHERE call_id = '${CALL_ID}';")
assert_eq "M-010 revenue counted" "1850.0" "$(extract_float "$resp" revenue)"

# calls_log tagged correctly.
resp=$(twin_sql "SELECT call_outcome FROM calls_log WHERE call_id = '${CALL_ID}';")
assert_eq "call_outcome" "call_abandoned" "$(extract_str "$resp" call_outcome)"

# M-081 — this call has a booking, so it should NOT appear in
# calls-without-booking even though it abandoned.
resp=$(twin_sql "SELECT COUNT(*) AS n FROM calls_log c
                 WHERE c.call_id = '${CALL_ID}'
                   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.call_id = c.call_id);")
assert_eq "M-081 (abandoned-with-booking is NOT a no-booking call)" "0" "$(extract_int "$resp" n)"

echo "PASS: TB4 — hangup recovery (call_id=${CALL_ID})"
