"""Same analyzer as analyze_v5.py but for v6. Quick copy."""
import json

SNAP = json.load(open("scripts/iac/snapshots/v6_nodes.json"))
nodes = SNAP["nodes"]
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


print(f"=== TREE (v6 — {len(nodes)} nodes) ===\n")
print_tree()

# Brief per-node config
print("\n\n=== BRIEF CONFIG ===\n")
for n in nodes:
    cfg = n.get("configuration") or {}
    nm = n["name"]
    tp = n["type"]
    ev = (n.get("event_id") or "")[:8]
    pid = n["persistent_id"][:8]
    parent = parent_name(n)

    print(f"--- {nm} (type={tp}, ev={ev}, pid={pid}, parent={parent}, complete={n.get('is_complete')}) ---")

    # model
    if n.get("model"):
        m = n["model"]
        if isinstance(m, dict) and "static" in m:
            s = m.get("static", {})
            print(f"  model.static.id={s.get('id')!r}  name={s.get('name')!r}")
    if n.get("prompt_md"):
        print(f"  prompt_md len={len(n['prompt_md'])}: {short(n['prompt_md'], 200)}")
    if n.get("initial_message"):
        try:
            txt = n["initial_message"][0]["children"][0]["text"]
            print(f"  initial_message: {txt!r}")
        except Exception:
            pass

    # cfg keys to show
    for k in ("tableName", "url", "filters", "tags", "parameters", "code",
              "transcription_context", "keyterms", "phone_number"):
        if k in cfg:
            v = cfg[k]
            if isinstance(v, str):
                print(f"  cfg.{k}: {v!r}" if len(v) < 80 else f"  cfg.{k} len={len(v)}: {short(v,150)}")
            elif isinstance(v, list):
                print(f"  cfg.{k}: <list len={len(v)}, json {len(json.dumps(v))} chars>")
            else:
                print(f"  cfg.{k}: {json.dumps(v)[:200]}")

    other = sorted(set(cfg.keys()) - {"tableName","url","filters","tags","parameters","code","transcription_context","keyterms","phone_number","headers","params","input","prompt","model","authType","ignore5XX","data","ttl_days","enable_feedback","enable_location","enable_ttl_days","enable_transcript","enable_transfer_summary","limit","orderByColumn","orderByDirection","background","agent","enable_memory","interaction_limit","enable_denoised_stt","real_time_classifiers","real_time_sentiment_classifier","call","samplePayload","values","worksheet","updateMode","spreadsheet","input_data","columnValues","max_buy","condition","agreed_rate","posted_rate"})
    if other:
        print(f"  cfg.other: {other}")
    print()
