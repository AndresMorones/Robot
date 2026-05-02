"""
Programmatically add a 'Write to Twin' action node to inbound-carrier v4
as a child of Classify Sentiment, writing 20 columns to calls_log.

Reproducible IaC: re-run-safe via the version-id check (will create a duplicate
node if you don't first delete the existing one — there is no built-in upsert).

Usage:
    python scripts/add_write_twin_node.py <HAPPYROBOT_API_KEY>
or:
    HAPPYROBOT_API_KEY=sk_live_... python scripts/add_write_twin_node.py

Verified working 2026-04-25. Uses curl under the hood (subprocess) because urllib
gets 401'd by HR's auth gateway on POSTs, while curl works fine — header
discrepancy in user-agent / accept that wasn't worth debugging.
"""
import json
import os
import subprocess
import sys

API_KEY = os.environ.get("HAPPYROBOT_API_KEY") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not API_KEY:
    sys.exit("Missing HAPPYROBOT_API_KEY env or arg")

BASE = "https://platform.happyrobot.ai/api/v2"
VERSION_ID = "019dc0f8-cd64-755b-9b4d-52961ffe15e0"
PARENT_NODE_ID = "019dc0f8-cd7b-70af-bf3f-c6feff910179"  # Classify Sentiment
EVENT_ID = "7021bfff-3e47-459c-b871-b0271ca04d9f"        # Write to Twin

# Group IDs (persistent_ids) for @ picker sources, learned via available-vars introspection.
G_CURRENT       = "current"
G_EXTRACT       = "3272b1bf-a18d-4cf4-996c-eac7993ae98e"
G_CLASSIFY      = "63f6b048-9a9e-457d-a8fd-4fcd684405d9"
G_CLASSIFY_SENT = "019dbf39-a0d8-7a12-a038-51f331fd39d2"
G_CASE_HEALTH   = "019dbf2d-4518-7b36-9c3c-4c985d8fb0b9"
G_AUDITOR       = "019dbf38-f679-7de1-9b5e-31738470d536"
G_ANALYZE       = "9f573f87-aa28-4583-973a-a103b519ad9c"

# (twin_column, twin_type, group_id, variable_id) — 20 mappings; id + created_at are auto.
MAPPINGS = [
    ("call_id",                          "text",   G_CURRENT,       "run_id"),
    ("mc_number",                        "text",   G_EXTRACT,       "response.mc_number"),
    ("carrier_name",                     "text",   G_EXTRACT,       "response.carrier_name"),
    ("load_id",                          "text",   G_EXTRACT,       "response.reference_number"),
    ("equipment_type",                   "text",   G_EXTRACT,       "response.equipment_type"),
    ("pitched_loadboard_rate",           "float8", G_EXTRACT,       "response.listed_rate"),
    ("agreed_rate",                      "float8", G_EXTRACT,       "response.agreed_rate"),
    ("num_negotiation_rounds",           "int8",   G_EXTRACT,       "response.num_negotiation_rounds"),
    ("call_outcome",                     "text",   G_CLASSIFY,      "response.classification"),
    ("sentiment",                        "text",   G_CLASSIFY_SENT, "response.classification"),
    ("case_health_score",                "int8",   G_CASE_HEALTH,   "response.case_health_score"),
    ("audit_remarks",                    "text",   G_CASE_HEALTH,   "response.health_score_reasoning"),
    ("fmcsa_eligibility_failure_reason", "text",   G_EXTRACT,       "response.decline_reason"),
    ("duration_seconds",                 "int8",   G_ANALYZE,       "duration"),
    ("transcript",                       "text",   G_ANALYZE,       "transcript"),
    ("sentiment_start",                  "text",   G_CASE_HEALTH,   "response.sentiment_start"),
    ("sentiment_trajectory",             "text",   G_CASE_HEALTH,   "response.sentiment_trajectory"),
    ("final_offer_position",             "text",   G_AUDITOR,       "final_offer_position"),
    ("posted_price_increase",            "float8", G_AUDITOR,       "posted_price_increase"),
    ("p90_latency_ms",                   "float8", G_ANALYZE,       "p90_latency_ms"),
]


def variable_paragraph(group_id, variable_id):
    """Plate Paragraph[] containing a single @-picker variable reference."""
    return [
        {
            "type": "paragraph",
            "children": [
                {"text": ""},
                {
                    "type": "variable",
                    "children": [{"text": ""}],
                    "group_id": group_id,
                    "variable_id": variable_id,
                },
                {"text": ""},
            ],
        }
    ]


def build_node():
    column_values = [
        {
            "columnName": col,
            "type": twin_type,
            "isPrimary": False,
            "value": variable_paragraph(gid, vid),
        }
        for col, twin_type, gid, vid in MAPPINGS
    ]
    return {
        "type": "action",
        "event_id": EVENT_ID,
        "name": "Write to Twin",
        "parent_node_id": PARENT_NODE_ID,  # NOT parent_id
        "configuration": {
            "tableName": "calls_log",
            "columnValues": column_values,
        },
    }


def post_via_curl(path, body):
    body_path = "./_post_body.json"
    with open(body_path, "w") as f:
        json.dump(body, f)
    cmd = [
        "curl", "-s", "--ssl-no-revoke", "-X", "POST",
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "Content-Type: application/json",
        "--data-binary", f"@{body_path}",
        BASE + path,
    ]
    out = subprocess.check_output(cmd).decode()
    os.remove(body_path)
    return json.loads(out)


def main():
    payload = {"nodes": [build_node()]}
    print(f"POST /versions/{VERSION_ID}/nodes — 1 Write Twin node, 20 columns")
    resp = post_via_curl(f"/versions/{VERSION_ID}/nodes", payload)
    if "error" in resp:
        print("FAILED:", json.dumps(resp, indent=2))
        sys.exit(1)
    created_id = resp["data"][0]["id"]
    print(f"Created node: {created_id}")
    print(f"Verify: curl -H 'Authorization: Bearer $HAPPYROBOT_API_KEY' \\")
    print(f"  https://platform.happyrobot.ai/api/v2/versions/{VERSION_ID}/nodes/{created_id}")


if __name__ == "__main__":
    main()
