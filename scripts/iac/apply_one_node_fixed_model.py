"""Test variant of apply_one_node: POST Case Health Score with FIXED model id.

Hypothesis: bad model.static.id ('gpt-4.1' = display name in id slot) corrupts voice.
This script overrides model.static.id to 'turbo-one' (valid registry id) before POST.

Usage:
    python scripts/iac/apply_one_node_fixed_model.py <version_id>
"""
import copy
import json
import os
import subprocess
import sys

VERSION_ID = sys.argv[1]
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
        with open("./_iac_body.json", "w") as f:
            json.dump(body, f)
        cmd += ["--data-binary", "@./_iac_body.json"]
    out = subprocess.check_output(cmd).decode()
    if body is not None:
        os.remove("./_iac_body.json")
    return json.loads(out)


# Load v5 source
v5 = json.load(open("scripts/iac/snapshots/v5_nodes.json"))
chs = next(n for n in v5["nodes"] if n["name"] == "Case Health Score")

# Get target version's Extract id
nodes = http("GET", f"/versions/{VERSION_ID}/nodes?page_size=100")
nodes = nodes.get("data", nodes)
extract_id = next(n["id"] for n in nodes if n["name"] == "Extract")

# Build body with FIXED model id
cfg = copy.deepcopy(chs["configuration"])
old_id = cfg["model"]["static"]["id"]
cfg["model"]["static"]["id"] = "turbo-one"
cfg["model"]["static"]["name"] = "gpt-4.1"
print(f"Model.id rewrite: '{old_id}' -> 'turbo-one' (registry id)")

body = {
    "type": chs["type"],
    "name": chs["name"],
    "parent_node_id": extract_id,
    "event_id": chs["event_id"],
    "configuration": cfg,
}

resp = http("POST", f"/versions/{VERSION_ID}/nodes", {"nodes": [body]})
if "data" in resp:
    created = resp["data"][0]
    print(f"OK created: id={created['id']} pid={created.get('persistent_id', created['id'])}")
else:
    print(f"FAILED: {json.dumps(resp, indent=2)[:500]}")
    sys.exit(1)
