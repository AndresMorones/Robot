"""Load dummy seed data into HR Twin DB via REST /sql endpoint.

Splits each batch SQL file on `-- === STATEMENT BREAK ===`, strips comments,
and POSTs each non-empty statement individually. Reports success / unique-violation
/ unexpected error counts per batch and aggregate.

Run from repo root or api/:
    cd api && uv run python ../scripts/load_dummy_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

# Allow running from repo root or api/
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
API_DIR = REPO_ROOT / "api"
sys.path.insert(0, str(API_DIR))

from app.config import settings  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
BATCH_FILES = [
    DATA_DIR / "dummy_seed_batch_1.sql",
    DATA_DIR / "dummy_seed_batch_2.sql",
    DATA_DIR / "dummy_seed_batch_3.sql",
]
BREAK = "-- === STATEMENT BREAK ==="
SQL_URL = f"{settings.hr_base_url.rstrip('/')}/twin/sql"


def split_statements(text: str) -> list[str]:
    """Split on the break marker; strip pure-comment / blank lines from each chunk."""
    out: list[str] = []
    for chunk in text.split(BREAK):
        # Drop comment-only and blank lines, preserve in-line content.
        lines = [
            ln for ln in chunk.splitlines()
            if ln.strip() and not ln.lstrip().startswith("--")
        ]
        stmt = "\n".join(lines).strip()
        if stmt:
            out.append(stmt)
    return out


def is_unique_violation(body: str) -> bool:
    b = body.lower()
    return (
        "unique" in b
        or "duplicate key" in b
        or "already exists" in b
        or "23505" in b
    )


def main() -> int:
    if not settings.happyrobot_api_key:
        print("ERROR: HAPPYROBOT_API_KEY not set in environment / api/.env", file=sys.stderr)
        return 2

    headers = {
        "Authorization": f"Bearer {settings.happyrobot_api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    totals = {"ok": 0, "dup": 0, "err": 0}

    with httpx.Client(timeout=30.0, headers=headers) as client:
        for path in BATCH_FILES:
            if not path.exists():
                print(f"\n[{path.name}] MISSING — skipping")
                continue
            print(f"\n[{path.name}]")
            statements = split_statements(path.read_text(encoding="utf-8"))
            print(f"  parsed {len(statements)} statement(s)")
            for i, stmt in enumerate(statements, start=1):
                preview = stmt.split("\n", 1)[0][:80]
                try:
                    resp = client.post(SQL_URL, json={"sql": stmt})
                except httpx.HTTPError as e:
                    print(f"  #{i} TRANSPORT FAIL :: {preview!r} :: {e}")
                    totals["err"] += 1
                    continue

                if resp.status_code < 400:
                    print(f"  #{i} OK            :: {preview!r}")
                    totals["ok"] += 1
                else:
                    body_snip = resp.text[:200]
                    if is_unique_violation(body_snip):
                        print(f"  #{i} DUP (skip)    :: {preview!r}")
                        totals["dup"] += 1
                    else:
                        print(
                            f"  #{i} ERROR {resp.status_code} :: {preview!r} "
                            f":: {body_snip[:120]}"
                        )
                        totals["err"] += 1

        # ----- verification -----
        print("\n[verification]")
        for table in ("calls_log", "bookings"):
            try:
                resp = client.post(SQL_URL, json={"sql": f"SELECT COUNT(*) AS n FROM {table}"})
                resp.raise_for_status()
                rows = resp.json().get("rows") or []
                n = rows[0].get("n") if rows else "?"
                print(f"  {table}: total rows = {n}")
            except httpx.HTTPError as e:
                print(f"  {table}: COUNT(*) failed :: {e}")

    print("\n[totals]")
    print(f"  ok:  {totals['ok']}")
    print(f"  dup: {totals['dup']}")
    print(f"  err: {totals['err']}")
    return 0 if totals["err"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
