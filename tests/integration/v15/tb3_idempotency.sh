#!/usr/bin/env bash
# TB3 — Idempotency on duplicate book_load
#
# Simulates HR Write-to-Twin retrying the same INSERT (same call_id + load_id)
# and asserts:
#   - First INSERT succeeds.
#   - Second INSERT fails with constraint violation `bookings_call_load_uniq`.
#   - Exactly ONE row survives (revenue not double-counted).
#
# This validates the UNIQUE (call_id, load_id) guard in the bookings DDL.
#
# Pairs with: docs/test-scenarios.md §TB3, data/twin_schema_v15_bookings.sql

set -euo pipefail

: "${HAPPYROBOT_API_KEY:?HAPPYROBOT_API_KEY must be exported}"
TWIN_URL="${TWIN_URL:-https://platform.happyrobot.ai/api/v2/twin/sql}"

CALL_ID="tb3-$(date +%s)-$$"
MC_NUMBER="tb3-mc-003"
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

# Like twin_sql but captures HTTP status code via -w; used for the duplicate
# INSERT where we EXPECT a 4xx with a constraint-violation body.
twin_sql_status() {
  local sql="$1"
  local body
  body=$(printf '{"sql": %s}' "$(printf '%s' "$sql" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")
  curl -sS -X POST \
    -H "Authorization: Bearer ${HAPPYROBOT_API_KEY}" \
    -H "Content-Type: application/json" \
    -w "\n__HTTP_STATUS__:%{http_code}" \
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
    echo "FAIL: TB3 — $1: expected=$2 actual=$3" >&2
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

echo "TB3: simulating duplicate INSERT for ${CALL_ID} / ${LOAD_ID}"

# First INSERT — must succeed.
twin_sql "INSERT INTO bookings (call_id, mc_number, load_id, apply_rate)
          VALUES ('${CALL_ID}', '${MC_NUMBER}', '${LOAD_ID}', ${APPLY_RATE});" >/dev/null

# Second INSERT (the simulated retry) — must fail on UNIQUE (call_id, load_id).
echo "TB3: issuing duplicate INSERT — expecting constraint violation"
resp_full=$(twin_sql_status "INSERT INTO bookings (call_id, mc_number, load_id, apply_rate)
            VALUES ('${CALL_ID}', '${MC_NUMBER}', '${LOAD_ID}', ${APPLY_RATE});" || true)

# Pull the trailing status line and the body separately.
status=$(printf '%s' "$resp_full" | tail -n1 | sed 's/^__HTTP_STATUS__://')
body=$(printf '%s' "$resp_full" | sed '$d')

# Constraint name OR generic uniqueness language must appear in the response.
echo "  Twin response status: ${status}"
if printf '%s' "$body" | grep -qiE 'bookings_call_load_uniq|duplicate key|unique constraint|already exists'; then
  echo "  OK uniqueness violation surfaced in response body"
else
  echo "FAIL: TB3 — duplicate INSERT did not surface a uniqueness violation" >&2
  echo "       status=${status}" >&2
  echo "       body=${body}" >&2
  exit 1
fi

# Confirm exactly ONE row survived.
resp=$(twin_sql "SELECT COUNT(*) AS n FROM bookings WHERE call_id = '${CALL_ID}';")
assert_eq "Bookings row count after duplicate INSERT" "1" "$(extract_int "$resp" n)"

# Revenue not double-counted.
resp=$(twin_sql "SELECT COALESCE(SUM(apply_rate), 0) AS revenue FROM bookings
                 WHERE call_id = '${CALL_ID}';")
assert_eq "M-010 revenue (single, not doubled)" "1850.0" "$(extract_float "$resp" revenue)"

echo "PASS: TB3 — idempotency on duplicate book_load (call_id=${CALL_ID})"
