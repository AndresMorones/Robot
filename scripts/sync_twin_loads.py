"""Mirror a HappyRobot Twin table to a local JSON file via the paginated REST read API.

Twin REST constraints (probed 2026-04-26, see docs/handoffs/2026-04-26-twin-search-architecture.md §4):
  - GET /api/v2/twin/tables/{name}?limit=&offset= returns {tableName, kind, rows, total}
  - Hard cap of 500 rows per call (HTTP 400 if you ask for more)
  - Filter query params (e.g. origin_state=TX) are silently ignored — full table only
  - Auth via Authorization: Bearer <HAPPYROBOT_API_KEY>

Run from repo root:  python scripts/sync_twin_loads.py --table loads
Stdlib-only so the script works without the api/ venv active.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://platform.happyrobot.ai/api/v2/twin/tables"
MAX_PAGE_SIZE = 500

log = logging.getLogger("sync_twin_loads")


def fetch_page(table: str, limit: int, offset: int, api_key: str) -> dict:
    """One Twin REST call. Raises RuntimeError on HTTP/JSON failure."""
    qs = urllib.parse.urlencode({"limit": limit, "offset": offset})
    url = f"{API_BASE}/{urllib.parse.quote(table)}?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from Twin: {e.read().decode('utf-8', 'replace')[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error talking to Twin: {e.reason}") from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Twin returned non-JSON body: {body[:200]!r}") from e


def fetch_all(table: str, page_size: int, api_key: str) -> list[dict]:
    """Paginate until offset+len(rows) >= total. Empty mid-page is treated as fatal."""
    rows: list[dict] = []
    offset = 0
    page_num = 1
    total: int | None = None
    while True:
        payload = fetch_page(table, page_size, offset, api_key)
        page_rows = payload.get("rows") or []
        page_total = payload.get("total")
        if not isinstance(page_total, int):
            raise RuntimeError(f"Twin response missing integer 'total': {payload!r}")
        if total is None:
            total = page_total
        pages = max(1, (total + page_size - 1) // page_size)
        log.info("page %d/%d: %d rows (offset %d)", page_num, pages, len(page_rows), offset)
        if not page_rows and offset < total:
            raise RuntimeError(f"empty page at offset {offset} but total={total} — partial fetch")
        rows.extend(page_rows)
        offset += len(page_rows)
        page_num += 1
        if offset >= total or not page_rows:
            break
    if len(rows) != total:
        raise RuntimeError(f"row count mismatch: got {len(rows)}, total reported {total}")
    return rows


def write_atomic(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=output.name + ".", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, output)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def main() -> int:
    p = argparse.ArgumentParser(description="Mirror a HappyRobot Twin table to local JSON.")
    p.add_argument("--table", default="loads")
    p.add_argument("--output", default=None, help="Default: data/twin_mirror/{table}.json")
    p.add_argument("--page-size", type=int, default=MAX_PAGE_SIZE)
    p.add_argument("--api-key-env", default="HAPPYROBOT_API_KEY")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not 1 <= args.page_size <= MAX_PAGE_SIZE:
        log.error("--page-size must be 1..%d (Twin hard cap)", MAX_PAGE_SIZE)
        return 1

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        log.error("env var %s is not set", args.api_key_env)
        return 1

    output = Path(args.output) if args.output else Path("data/twin_mirror") / f"{args.table}.json"

    try:
        rows = fetch_all(args.table, args.page_size, api_key)
        write_atomic(rows, output)
    except RuntimeError as e:
        log.error("%s", e)
        return 1

    log.info("wrote %d rows from %s to %s", len(rows), args.table, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
