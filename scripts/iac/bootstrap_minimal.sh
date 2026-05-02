#!/usr/bin/env bash
# IaC: Inbound Carrier Sales — minimal bootstrap (Stage 1)
# Creates 4 workflow variables, sets minimal Prompt body, publishes to development.
# Verified working 2026-04-26 against workflow "3" (id 019dc723-57fb-78ad-90e3-9674205b305c).
#
# Stage 2 follows: adds 4 tools + post-call chain + Write Twin (see bootstrap_full.sh).
#
# Usage:
#   export HAPPYROBOT_API_KEY=sk_live_...
#   bash scripts/iac/bootstrap_minimal.sh <workflow_id> <version_id> <prompt_node_id>

set -euo pipefail

KEY="${HAPPYROBOT_API_KEY:?Set HAPPYROBOT_API_KEY}"
WORKFLOW_ID="${1:?Pass workflow_id}"
VERSION_ID="${2:?Pass version_id}"
PROMPT_NODE_ID="${3:?Pass prompt_node_id}"
BASE="https://platform.happyrobot.ai/api/v2"

# 1. Create 4 workflow variables
for kv in "negotiation_floor_pct:0.10" "max_negotiation_rounds:3" "agent_name:Paul" "company_name:Acme Logistics"; do
  k="${kv%%:*}"; v="${kv#*:}"
  curl -s --ssl-no-revoke -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d "{\"key\":\"$k\",\"value_production\":\"$v\",\"value_staging\":\"$v\",\"value_development\":\"$v\"}" \
    "$BASE/workflows/$WORKFLOW_ID/variables" > /dev/null
  echo "var: $k"
done

# 2. PUT prompt body (use prompt_md — HR auto-converts to Plate JSON)
cat > /tmp/prompt_body.json <<'JSON'
{
  "type": "prompt",
  "prompt_md": "You are Paul, a freight broker rep at Acme Logistics taking inbound calls from motor carriers looking for loads.\n\nBe efficient and professional. When a carrier calls, ask for their MC number first. Acknowledge their response and confirm.",
  "initial_message_md": "Thank you for calling Acme Logistics, this is Paul. How can I help?",
  "model": {"type":"static","static":{"id":"gpt-4.1","name":"gpt-4.1"}}
}
JSON
curl -s --ssl-no-revoke -X PUT -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  --data-binary @/tmp/prompt_body.json "$BASE/versions/$VERSION_ID/nodes/$PROMPT_NODE_ID" > /dev/null
echo "prompt: set"

# 3. Publish to development
curl -s --ssl-no-revoke -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"environment":"development"}' "$BASE/versions/$VERSION_ID/publish" > /dev/null
echo "published: development"
