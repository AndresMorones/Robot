"""IaC test — POST exactly ONE node to a target version, cloned from v5.

Used to bisect which addition (if any) breaks voice.

Usage:
    python scripts/iac/apply_one_node.py <version_id> <node_name_in_v5> <parent_name_in_target>

Example:
    python scripts/iac/apply_one_node.py 019dc8e8-... "Case Health Score" Extract
"""
import copy
import json
import os
import subprocess
import sys

if len(sys.argv) < 4:
    sys.exit("Usage: apply_one_node.py <version_id> <node_name_in_v5> <parent_name_in_target>")

TARGET_VERSION_ID = sys.argv[1]
NODE_NAME = sys.argv[2]
PARENT_NAME = sys.argv[3]

BASE = "https://platform.happyrobot.ai/api/v2"

KEY = None
if os.path.exists(".happyrobot.env"):
    for line in open(".happyrobot.env"):
        if line.startswith("HAPPYROBOT_API_KEY="):
            KEY = line.split("=", 1)[1].strip()
            break
KEY = KEY or os.environ.get("HAPPYROBOT_API_KEY")
if not KEY:
    sys.exit("Missing HAPPYROBOT_API_KEY")


def http(method, path, body=None):
    cmd = ["curl", "-s", "--ssl-no-revoke", "-X", method,
           "-H", f"Authorization: Bearer {KEY}",
           "-H", "Content-Type: application/json", BASE + path]
    if body is not None:
        with open("./_one_node_body.json", "w") as f:
            json.dump(body, f)
        cmd += ["--data-binary", "@./_one_node_body.json"]
    out = subprocess.check_output(cmd).decode()
    if body is not None:
        os.remove("./_one_node_body.json")
    return json.loads(out)


# Source: v5
v5 = json.load(open("scripts/iac/snapshots/v5_nodes.json"))
v5_node = next(n for n in v5["nodes"] if n["name"].strip() == NODE_NAME.strip())

# Target: get parent's id from current version
target_resp = http("GET", f"/versions/{TARGET_VERSION_ID}/nodes?page_size=100")
target_nodes = target_resp.get("data", target_resp)
parent_v_node = next(n for n in target_nodes if n["name"].strip() == PARENT_NAME.strip())
parent_id = parent_v_node["id"]
print(f"target version: {TARGET_VERSION_ID}")
print(f"parent: {PARENT_NAME!r} (id={parent_id})")
print(f"node to add: {NODE_NAME!r} (type={v5_node['type']}, ev={v5_node.get('event_id', '')[:8]})")

# Build body
n = copy.deepcopy(v5_node)
body = {
    "type": n["type"],
    "name": n["name"].strip(),
    "parent_node_id": parent_id,
}
if n.get("event_id"):
    body["event_id"] = n["event_id"]
if n.get("configuration") is not None:
    body["configuration"] = n["configuration"]
if n.get("function") is not None:
    f = n["function"]
    f.pop("tool_index_hash", None)
    f.pop("tool_index_id", None)
    body["function"] = f

print(f"body size: {len(json.dumps(body))} chars")

# POST
resp = http("POST", f"/versions/{TARGET_VERSION_ID}/nodes", {"nodes": [body]})
if "error" in resp or "data" not in resp:
    print(f"FAILED: {json.dumps(resp, indent=2)[:500]}")
    sys.exit(1)

created = resp["data"][0]
new_id = created["id"]
new_pid = created.get("persistent_id") or new_id
print(f"OK: created {NODE_NAME!r}")
print(f"  new id={new_id}")
print(f"  new persistent_id={new_pid}")
