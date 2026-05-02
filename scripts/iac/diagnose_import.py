"""Scan a post-import HR workflow JSON for stale references.

Strategy:
1. Build set of VALID persistent_ids (each node's own pid in this workflow).
2. Walk every config recursively, find every group_id and `call.static.id`.
3. Any reference pid NOT in the valid set is STALE.
4. Output: list of "node X has stale ref in field Y, points at <unknown>".

If a SOURCE export is provided (the JSON that was imported from), we can also
match by name to suggest "should be pid Z" corrections. Otherwise just flag.

Usage:
    python scripts/iac/diagnose_import.py <imported.json> [<source_export.json>]
"""
import json
import sys


def collect_valid_pids(nodes):
    """Set of all persistent_ids in this workflow + special tokens."""
    pids = {n["persistent_id"] for n in nodes}
    pids.add("current")  # special HR token
    pids.add("use_case_variables")  # workflow vars
    return pids


def name_to_pid(nodes):
    return {n["name"].strip(): n["persistent_id"] for n in nodes}


def find_stale_refs(obj, valid_pids, path="", findings=None):
    """Recursively walk obj, collect stale group_id and call.static.id refs."""
    if findings is None:
        findings = []
    if isinstance(obj, dict):
        # Detect group_id stale refs (Plate variable bindings)
        if "group_id" in obj and isinstance(obj["group_id"], str):
            gid = obj["group_id"]
            if gid not in valid_pids:
                vid = obj.get("variable_id", "?")
                findings.append({"path": path, "type": "group_id", "stale_pid": gid, "variable_id": vid})
        # Detect call.static.id (Voice Agent's call binding)
        if (
            isinstance(obj.get("static"), dict)
            and isinstance(obj["static"].get("id"), str)
            and "name" in obj["static"]
            and obj["static"]["name"] == "Web call"
            and obj["static"]["id"] not in valid_pids
        ):
            findings.append({"path": path, "type": "call.static.id", "stale_pid": obj["static"]["id"], "name": "Web call"})
        # Detect bad model.static.id (display name in id slot)
        if (
            isinstance(obj.get("static"), dict)
            and isinstance(obj["static"].get("id"), str)
            and "description" in obj["static"]  # model objects often have description
            or (
                isinstance(obj.get("type"), str)
                and obj.get("type") == "static"
                and isinstance(obj.get("static"), dict)
                and "id" in obj["static"]
                and "name" in obj["static"]
            )
        ):
            sid = obj.get("static", {}).get("id", "")
            sname = obj.get("static", {}).get("name", "")
            # Heuristic: id matches a known display name = bad
            BAD_AS_ID = {"gpt-4.1", "GPT-4.1", "gpt-4", "GPT-4"}
            if sid in BAD_AS_ID:
                findings.append({"path": path, "type": "bad_model_id", "stale_pid": sid, "should_be": "turbo-one"})

        for k, v in obj.items():
            find_stale_refs(v, valid_pids, f"{path}.{k}", findings)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_stale_refs(item, valid_pids, f"{path}[{i}]", findings)
    return findings


def main():
    imported_path = sys.argv[1]
    source_path = sys.argv[2] if len(sys.argv) > 2 else None

    imported = json.load(open(imported_path, encoding="utf-8"))
    nodes = imported["nodes"]
    valid_pids = collect_valid_pids(nodes)
    new_n2p = name_to_pid(nodes)

    if source_path:
        source = json.load(open(source_path, encoding="utf-8"))
        old_n2p = name_to_pid(source["nodes"])
        # old_pid -> new_pid by name
        old_to_new = {}
        for name, old_pid in old_n2p.items():
            if name in new_n2p:
                old_to_new[old_pid] = (name, new_n2p[name])
    else:
        old_to_new = None

    print(f"Imported workflow: {imported.get('version', {}).get('id')}")
    print(f"Nodes: {len(nodes)}")
    print(f"Valid pids: {len(valid_pids)}")
    print()

    # Per-node analysis
    total_findings = 0
    for n in nodes:
        cfg = n.get("configuration", {})
        node_findings = find_stale_refs(cfg, valid_pids, path=f"{n['name']}.configuration")
        # Also walk top-level fields like model, prompt, function for tools
        for top_key in ("model", "function", "prompt"):
            if n.get(top_key):
                f2 = find_stale_refs(n[top_key], valid_pids, path=f"{n['name']}.{top_key}")
                node_findings.extend(f2)

        # De-dup by (type, stale_pid, variable_id)
        seen = set()
        deduped = []
        for f in node_findings:
            key = (f["type"], f.get("stale_pid"), f.get("variable_id"))
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        if deduped:
            total_findings += len(deduped)
            print(f"=== {n['name']} ({len(deduped)} issue{'s' if len(deduped)>1 else ''}) ===")
            for f in deduped:
                if f["type"] == "group_id":
                    suggestion = ""
                    if old_to_new and f["stale_pid"] in old_to_new:
                        nm, new_pid = old_to_new[f["stale_pid"]]
                        suggestion = f"  -> in UI re-bind to '{nm}' (new pid {new_pid[:8]}...)"
                    print(f"  STALE group_id  variable={f['variable_id']!r}  stale={f['stale_pid'][:16]}...{suggestion}")
                elif f["type"] == "call.static.id":
                    print(f"  STALE call.static.id  stale={f['stale_pid'][:16]}... (re-bind 'Call source' in Voice Agent)")
                elif f["type"] == "bad_model_id":
                    print(f"  BAD MODEL ID  '{f['stale_pid']}' is a display name, change to '{f['should_be']}' (registry id)")
            print()

    print(f"TOTAL: {total_findings} fixes needed across {len([n for n in nodes if find_stale_refs(n.get('configuration',{}), valid_pids)])} nodes")


if __name__ == "__main__":
    main()
