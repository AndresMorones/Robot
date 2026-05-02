"""Snapshot all nodes of a HappyRobot workflow version + its variables.

Usage:
    python scripts/iac/snapshot_version.py <version_id> <out_path>

Reads HAPPYROBOT_API_KEY from .happyrobot.env at repo root.
"""
import json, os, subprocess, sys

KEY = None
env_path = ".happyrobot.env"
if os.path.exists(env_path):
    for line in open(env_path):
        if line.startswith("HAPPYROBOT_API_KEY="):
            KEY = line.split("=", 1)[1].strip()
            break
KEY = KEY or os.environ.get("HAPPYROBOT_API_KEY")
if not KEY:
    sys.exit("Missing HAPPYROBOT_API_KEY")

BASE = "https://platform.happyrobot.ai/api/v2"


def get(path):
    out = subprocess.check_output([
        "curl", "-s", "--ssl-no-revoke",
        "-H", f"Authorization: Bearer {KEY}",
        BASE + path,
    ]).decode()
    return json.loads(out)


def main():
    version_id = sys.argv[1]
    out_path = sys.argv[2]

    # Get version details (includes workflow_id)
    version = get(f"/versions/{version_id}")
    workflow_id = version.get("workflow_id") or version.get("data", {}).get("workflow_id")

    # Some endpoints wrap in {data: ...}
    if "data" in version and isinstance(version["data"], dict):
        version = version["data"]
        workflow_id = version.get("workflow_id")

    # List nodes
    nodes_resp = get(f"/versions/{version_id}/nodes?page_size=100")
    nodes_list = nodes_resp.get("data", nodes_resp)

    # Get full detail for each node
    nodes_full = []
    for n in nodes_list:
        node_id = n["id"]
        detail = get(f"/versions/{version_id}/nodes/{node_id}")
        if "data" in detail:
            detail = detail["data"]
        nodes_full.append(detail)

    # Workflow vars
    vars_data = []
    if workflow_id:
        v = get(f"/workflows/{workflow_id}/variables?page_size=100")
        vars_data = v.get("data", v)

    snapshot = {
        "workflow_id": workflow_id,
        "version_id": version_id,
        "version_meta": {k: version.get(k) for k in ("name", "slug", "version_number", "is_published", "is_live")},
        "node_count": len(nodes_full),
        "nodes": nodes_full,
        "variables": vars_data,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Saved {out_path}: workflow={workflow_id}, version={version_id}, nodes={len(nodes_full)}")
    print()
    print("Node tree:")
    for n in nodes_full:
        pid = n.get("persistent_id", "")[:8]
        parent = n.get("parent_node_id", "")[:8] or "—"
        nm = n.get("name", "?")
        tp = n.get("type", "?")
        ev = n.get("event_id", "")[:8]
        print(f"  {nm:<35} type={tp:<10} ev={ev} pid={pid} parent={parent}")


if __name__ == "__main__":
    main()
