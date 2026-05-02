"""IaC Phase A — POST 8 missing nodes from v5 into v6.

CORRUPTION-SAFE: only POSTs new nodes; never PUTs existing ones.

Reads v5 snapshot as the canonical config source. Reuses persistent_ids that
are stable across the fork chain (Prompt, Extract, Classify, etc.). Remaps
references to nodes that get newly-created.

Skips Computations and Carrier Sales Auditor per user direction; reroutes:
  - Case Health Score parent: Computations -> Extract
  - Classify Sentiment parent: Carrier Sales Auditor -> Case Health Score
  - Write to Twin: drops Auditor-sourced columns (final_offer_position,
    posted_price_increase).

Usage:
    python scripts/iac/apply_phase_a.py
"""
import copy
import json
import os
import subprocess
import sys

VERSION_ID = sys.argv[1] if len(sys.argv) > 1 else "019dc8ae-a0e9-7946-83fc-a47d9be3e70c"
INCLUDE_POPUP = "--include-popup" in sys.argv  # Initiate New Contact triggers HR auto-rewire corruption; OFF by default
BASE = "https://platform.happyrobot.ai/api/v2"

# Read API key
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
    cmd = [
        "curl", "-s", "--ssl-no-revoke", "-X", method,
        "-H", f"Authorization: Bearer {KEY}",
        "-H", "Content-Type: application/json",
        BASE + path,
    ]
    if body is not None:
        body_path = "./_iac_body.json"
        with open(body_path, "w") as f:
            json.dump(body, f)
        cmd += ["--data-binary", f"@{body_path}"]
    out = subprocess.check_output(cmd).decode()
    if body is not None:
        os.remove(body_path)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"Bad response from {method} {path}: {out[:500]}")


def remap_group_ids(obj, remap):
    """Recursively rewrite any group_id values matching remap dict keys."""
    if isinstance(obj, dict):
        if "group_id" in obj and isinstance(obj["group_id"], str) and obj["group_id"] in remap:
            obj["group_id"] = remap[obj["group_id"]]
        for v in obj.values():
            remap_group_ids(v, remap)
    elif isinstance(obj, list):
        for item in obj:
            remap_group_ids(item, remap)


# Load v5 snapshot
v5 = json.load(open("scripts/iac/snapshots/v5_nodes.json"))
v5_by_name = {n["name"]: n for n in v5["nodes"]}
v5_by_id = {n["id"]: n for n in v5["nodes"]}

# Get current v6 nodes -> name -> node_id, persistent_id
v6_resp = http("GET", f"/versions/{VERSION_ID}/nodes?page_size=100")
v6_nodes = v6_resp.get("data", v6_resp)
v6_by_name = {n["name"]: n for n in v6_nodes}

# Verify v6 has the parents we need
REQUIRED_V6_PARENTS = ["Prompt", "Analyze Incoming Conversation", "Extract"]
for p in REQUIRED_V6_PARENTS:
    if p not in v6_by_name:
        sys.exit(f"v6 missing required parent node: {p!r}")

# Order of additions: parent before child
# NOTE: Initiate New Contact (popup) under Analyze Incoming Conversation triggers
# HR auto-rewire of Classify (which was sibling) — the rewire is a hidden parent_id
# mutation that corrupts runtime. Default skip; add via UI later if needed.
ADD_PLAN = [
    # (v5_name, override_parent_name_or_None_for_use_v5_parent)
    ("negotiate_evaluate", "Prompt"),
    ("Calculate Carrier Cost", "negotiate_evaluate"),
    ("search_loads_by_lane", "Prompt"),
    ("Fetch Loads ", "search_loads_by_lane"),  # NOTE: trailing space in v5 name
    ("Case Health Score", "Extract"),  # skip Computations parent (added before Initiate New Contact to avoid rewire)
    ("Classify Sentiment", "Case Health Score"),  # skip Carrier Sales Auditor parent
    ("Write to Twin", "Classify Sentiment"),
]
if INCLUDE_POPUP:
    # Insert popup if explicitly enabled — KNOWN to trigger HR auto-rewire corruption
    ADD_PLAN.insert(4, ("Initiate New Contact", "Analyze Incoming Conversation"))

# Columns to drop from Write to Twin (reference skipped Carrier Sales Auditor)
WRITE_TWIN_DROP_COLUMNS = {"final_offer_position", "posted_price_increase"}

# Build remap dict as we POST. Initially: shared persistent_ids stay the same
# (Prompt, Analyze Incoming Conversation, Extract, Classify, etc. — already in v6
# with same pid). Any v5 pid we DON'T remap stays the same.
# Only newly-created nodes need entries here.
remap = {}

# Pre-populate remap from any nodes already created in v6 (idempotency on re-run).
# Match by name; map v5_pid -> v6_pid for shared name.
for v5n in v5["nodes"]:
    nm = v5n["name"].strip()
    if nm in v6_by_name:
        v6n = v6_by_name[nm]
        if v5n["persistent_id"] != v6n["persistent_id"]:
            remap[v5n["persistent_id"]] = v6n["persistent_id"]

# Track v6 newly-created nodes for parent lookups within this run
new_v6_by_name = {}


def get_parent_v6_node_id(parent_name):
    """Look up parent's v6 node_id (database id, not persistent_id)."""
    if parent_name in new_v6_by_name:
        return new_v6_by_name[parent_name]["id"]
    if parent_name in v6_by_name:
        return v6_by_name[parent_name]["id"]
    raise KeyError(f"Cannot find parent node {parent_name!r} in v6")


def build_body(v5_node, parent_v6_id):
    """Build POST body for a single node, deep-copied + remapped."""
    n = copy.deepcopy(v5_node)
    body = {
        "type": n["type"],
        "name": n["name"].strip(),  # strip trailing spaces (e.g., "Fetch Loads ")
        "parent_node_id": parent_v6_id,
    }
    if n.get("event_id"):
        body["event_id"] = n["event_id"]
    if n.get("configuration") is not None:
        cfg = n["configuration"]
        # Special handling for Write to Twin: drop skipped columns
        if n["name"].strip() == "Write to Twin" and "columnValues" in cfg:
            cfg["columnValues"] = [
                cv for cv in cfg["columnValues"]
                if cv.get("columnName") not in WRITE_TWIN_DROP_COLUMNS
            ]
        # Remap group_ids inside configuration
        remap_group_ids(cfg, remap)
        body["configuration"] = cfg
    if n.get("function") is not None:
        f = n["function"]
        # Strip tool_index_hash + tool_index_id (HR-managed, will be regenerated)
        f.pop("tool_index_hash", None)
        f.pop("tool_index_id", None)
        remap_group_ids(f, remap)
        body["function"] = f
    # Top-level fields for prompt/voice agent — but we don't add those nodes in Phase A
    # so this branch is unused.
    return body


def post_node(body):
    payload = {"nodes": [body]}
    resp = http("POST", f"/versions/{VERSION_ID}/nodes", payload)
    if "error" in resp or "data" not in resp:
        print(f"  FAILED: {json.dumps(resp, indent=2)[:500]}")
        return None
    return resp["data"][0]


# Execute plan
print(f"=== Phase A: adding {len(ADD_PLAN)} nodes to v6 ({VERSION_ID}) ===\n")
for v5_name, parent_name in ADD_PLAN:
    v5_node = v5_by_name.get(v5_name)
    if not v5_node:
        print(f"SKIP: {v5_name!r} not found in v5")
        continue

    # Idempotency: skip if v6 already has this name
    if v5_name.strip() in v6_by_name or v5_name.strip() in new_v6_by_name:
        print(f"SKIP: {v5_name!r} already exists in v6")
        continue

    parent_v6_id = get_parent_v6_node_id(parent_name)
    body = build_body(v5_node, parent_v6_id)
    print(f"POST {v5_name!r} -> parent={parent_name!r} (parent_id={parent_v6_id[:8]}...)")
    print(f"  body keys: {list(body.keys())}, body size: {len(json.dumps(body))} chars")

    created = post_node(body)
    if not created:
        print(f"  STOP: failed to create {v5_name!r}")
        sys.exit(1)

    new_id = created["id"]
    # POST response may not include persistent_id; fall back to id (same value for new nodes)
    new_pid = created.get("persistent_id") or new_id
    print(f"  created: id={new_id[:8]}... pid={new_pid[:8]}...")

    # Track the new pid -> remap any future references
    old_pid = v5_node["persistent_id"]
    if old_pid != new_pid:
        remap[old_pid] = new_pid

    new_v6_by_name[v5_name.strip()] = {"id": new_id, "persistent_id": new_pid}

print("\n=== Done. Newly created nodes in v6: ===")
for name, info in new_v6_by_name.items():
    print(f"  {name}: id={info['id']}, pid={info['persistent_id']}")

# Save remap for later phases
with open("scripts/iac/snapshots/v6_phase_a_remap.json", "w") as f:
    json.dump({
        "v6_version_id": VERSION_ID,
        "newly_created": new_v6_by_name,
        "v5_to_v6_pid_remap": remap,
    }, f, indent=2)
print("\nSaved remap to scripts/iac/snapshots/v6_phase_a_remap.json")
