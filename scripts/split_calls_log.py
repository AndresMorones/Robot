"""One-off: split the single-line audit JSON into one row per line so Read can chunk it."""
import json
from pathlib import Path

SRC = Path(r"c:/Users/Andre/OneDrive/Documentos/GitHub/Robot/data/calls_log_review_2026-04-27.json")
DST = Path(r"c:/Users/Andre/OneDrive/Documentos/GitHub/Robot/data/calls_log_review_2026-04-27.ndjson")

rows = json.loads(SRC.read_text(encoding="utf-8"))
with DST.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False, default=str))
        f.write("\n")
print(f"wrote {len(rows)} rows to {DST}")
