"""Analyze v5 snapshot — print key config per node.

Reads top-level fields (prompt_md, model, initial_message, etc.) and configuration.
Uses 'parent_id' (read field) — note: WRITE field is 'parent_node_id'.
"""
import json, sys

SNAP = json.load(open("scripts/iac/snapshots/v5_nodes.json"))
nodes = SNAP["nodes"]
by_pid = {n["persistent_id"]: n for n in nodes}
by_id = {n["id"]: n for n in nodes}


def parent_name(n):
    pid = n.get("parent_id")
    if not pid:
        return "ROOT"
    p = by_id.get(pid)
    return p["name"] if p else f"<unknown:{pid[:8]}>"


def short(s, n=200):
    if not isinstance(s, str):
        return s
    s = s.replace("\n", "\\n")
    return s[:n] + ("..." if len(s) > n else "")


# === TREE ===
print(f"=== TREE (v5 — {len(nodes)} nodes) ===\n")
by_parent = {}
for n in nodes:
    by_parent.setdefault(n.get("parent_id"), []).append(n)


def print_tree(parent_id=None, depth=0):
    for n in sorted(by_parent.get(parent_id, []), key=lambda x: x.get("sort_index", 0)):
        nm = n["name"]
        tp = n["type"]
        ev = (n.get("event_id") or "")[:8]
        pid = n["persistent_id"][:8]
        complete = "[OK]" if n.get("is_complete") else "[X] "
        print(f"{'  '*depth}{complete} {nm}  [type={tp}, ev={ev}, pid={pid}]")
        print_tree(n["id"], depth + 1)


print_tree()

# === PER-NODE DETAIL ===
print("\n\n=== PER-NODE CONFIG ===\n")

INSPECT_KEYS = (
    # top-level
    "prompt_md", "initial_message", "model", "voice",
    # configuration sub-keys
    "tableName", "columnValues", "url", "headers", "params", "body", "method",
    "tags", "parameters", "schema", "code", "input_data",
    "transcription_context", "keyterms", "background", "agent",
    "max_duration_seconds", "enable_memory", "interaction_limit",
    "real_time_classifiers", "real_time_sentiment_classifier",
    "phone_number", "data", "ttl_days", "enable_feedback", "enable_location",
    "enable_transcript", "enable_transfer_summary",
    "filters", "limit", "orderByColumn", "orderByDirection",
    "max_buy", "condition", "agreed_rate", "posted_rate",
    "input", "prompt",
    "description", "message",
)


def show(n):
    print(f"\n--- {n['name']} (type={n['type']}, ev={(n.get('event_id') or '')[:8]}, pid={n['persistent_id'][:8]}, parent={parent_name(n)}, complete={n.get('is_complete')}) ---")
    cfg = n.get("configuration") or {}

    # top-level model
    if n.get("model"):
        m = n["model"]
        if isinstance(m, dict) and "static" in m:
            s = m.get("static", {})
            print(f"  model.static.id={s.get('id')!r}  model.static.name={s.get('name')!r}")
        else:
            print(f"  model={json.dumps(m)[:200]}")

    # initial message + prompt_md
    if n.get("initial_message"):
        # Plate paragraph[]; pull text
        try:
            ims = n["initial_message"]
            if isinstance(ims, list) and ims and ims[0].get("children"):
                txt = ims[0]["children"][0].get("text", "")
                print(f"  initial_message: {txt!r}")
        except Exception:
            pass
    if n.get("prompt_md"):
        print(f"  prompt_md (len={len(n['prompt_md'])}): {short(n['prompt_md'], 400)}")

    # configuration top-level interesting keys
    for k in INSPECT_KEYS:
        if k not in cfg:
            continue
        val = cfg[k]
        if isinstance(val, str):
            if len(val) < 200:
                print(f"  cfg.{k}: {val!r}")
            else:
                print(f"  cfg.{k} (str len={len(val)}): {short(val, 200)}")
        elif isinstance(val, list):
            s = json.dumps(val)
            if len(s) < 400:
                print(f"  cfg.{k}: {s}")
            else:
                print(f"  cfg.{k}: <list len={len(val)}, json={len(s)} chars>")
        elif isinstance(val, dict):
            s = json.dumps(val)
            if len(s) < 400:
                print(f"  cfg.{k}: {s}")
            else:
                print(f"  cfg.{k}: <dict {len(s)} chars>")
        else:
            print(f"  cfg.{k}: {val!r}")

    # any other configuration keys we didn't inspect
    other = sorted(set(cfg.keys()) - set(INSPECT_KEYS))
    if other:
        print(f"  cfg.<other keys>: {other}")


for n in nodes:
    show(n)

# Variables
print("\n\n=== VARIABLES ===")
for v in SNAP.get("variables", []):
    print(f"  {v.get('key')!r} dev={v.get('value_development')!r} pid={v.get('persistent_id', '')[:8]}")
print(f"  total: {len(SNAP.get('variables', []))}")
