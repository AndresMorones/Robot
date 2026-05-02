#!/usr/bin/env python
"""Seed mock token-usage values into existing calls_log rows.

Run from repo root:
    python scripts/seed_token_columns.py [--dry-run] [--seed 42] [--limit N]

Why: HR @-picker bindings on Log Event aren't done yet, so existing rows have
NULL token columns. This populates them with realistic mocks so the new
Telemetry dashboard widgets render real-looking RPM/TPM/percentile charts
before the HR UI batch lands.

When real bindings ship, future calls INSERT with HR's real token values; this
script's mocks remain on historical rows (UPDATE doesn't touch new INSERTs).

Distributions:
  Extract Call Details (per-call):
    input_tokens     ~ 700-1100 (median ~900)
    output_tokens    ~ 20-50
    reasoning_tokens ~ 0 (15% chance: 50-200)
    cached_input_pct ~ 0 / 0.1 / 0.3 / 0.5 / 0.7 (weights 40/15/20/15/10)
    uncached         = input - cached

  Case Health Score (per-call, processes full transcript — bigger):
    input_tokens     ~ 1500-2500 (median ~1900)
    output_tokens    ~ 50-120
    reasoning_tokens ~ 0 (15% chance: 100-300)
    cached_input_pct ~ same distribution as extract

Reproducible via --seed.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Any

import httpx

HR_BASE = "https://platform.happyrobot.ai/api/v2"
TWIN_SQL = f"{HR_BASE}/twin/sql"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("'\"")
        if k and k not in os.environ:
            os.environ[k] = v


def execute_sql(api_key: str, sql: str) -> dict[str, Any] | None:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(TWIN_SQL, json={"sql": sql}, headers=headers)
        if resp.status_code >= 400:
            sys.stderr.write(f"SQL error {resp.status_code}: {resp.text[:500]}\n")
            return None
        return resp.json()
    except httpx.HTTPError as e:
        sys.stderr.write(f"HTTP error: {e}\n")
        return None


def fetch_call_ids(api_key: str) -> list[str]:
    data = execute_sql(
        api_key,
        "SELECT call_id FROM calls_log WHERE call_id IS NOT NULL",
    )
    if not data:
        return []
    return [r["call_id"] for r in data.get("rows", []) if r.get("call_id")]


def gen_extract_tokens() -> dict[str, int]:
    inp = random.randint(700, 1100)
    out = random.randint(20, 50)
    reasoning = 0 if random.random() > 0.15 else random.randint(50, 200)
    cache_pct = random.choices(
        [0.0, 0.1, 0.3, 0.5, 0.7],
        weights=[40, 15, 20, 15, 10],
    )[0]
    cached = int(inp * cache_pct)
    uncached = inp - cached
    return {
        "input": inp,
        "output": out,
        "reasoning": reasoning,
        "cached_input": cached,
        "uncached_input": uncached,
    }


def gen_chs_tokens() -> dict[str, int]:
    inp = random.randint(1500, 2500)
    out = random.randint(50, 120)
    reasoning = 0 if random.random() > 0.15 else random.randint(100, 300)
    cache_pct = random.choices(
        [0.0, 0.1, 0.3, 0.5, 0.7],
        weights=[40, 15, 20, 15, 10],
    )[0]
    cached = int(inp * cache_pct)
    uncached = inp - cached
    return {
        "input": inp,
        "output": out,
        "reasoning": reasoning,
        "cached_input": cached,
        "uncached_input": uncached,
    }


def update_row(
    api_key: str,
    call_id: str,
    ext: dict[str, int],
    chs: dict[str, int],
) -> bool:
    safe_id = call_id.replace("'", "''")
    sql = (
        "UPDATE calls_log SET "
        f"extract_input_tokens = {ext['input']}, "
        f"extract_output_tokens = {ext['output']}, "
        f"extract_reasoning_tokens = {ext['reasoning']}, "
        f"extract_cached_input_tokens = {ext['cached_input']}, "
        f"extract_uncached_input_tokens = {ext['uncached_input']}, "
        f"chs_input_tokens = {chs['input']}, "
        f"chs_output_tokens = {chs['output']}, "
        f"chs_reasoning_tokens = {chs['reasoning']}, "
        f"chs_cached_input_tokens = {chs['cached_input']}, "
        f"chs_uncached_input_tokens = {chs['uncached_input']} "
        f"WHERE call_id = '{safe_id}'"
    )
    return execute_sql(api_key, sql) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be updated without hitting Twin")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for reproducibility")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only seed this many rows (default: all)")
    parser.add_argument("--env-file", default="api/.env",
                        help="Path to .env file fallback")
    args = parser.parse_args()

    random.seed(args.seed)
    load_env(Path(args.env_file))
    api_key = os.environ.get("HAPPYROBOT_API_KEY", "").strip()
    if not api_key:
        sys.stderr.write(
            "ERROR: HAPPYROBOT_API_KEY not set in env or .env file.\n"
            f"  Checked env_file: {args.env_file}\n"
        )
        return 1

    call_ids = fetch_call_ids(api_key)
    if not call_ids:
        sys.stderr.write("No calls_log rows found.\n")
        return 1

    if args.limit:
        call_ids = call_ids[: args.limit]

    print(f"Found {len(call_ids)} rows to seed (seed={args.seed}, dry-run={args.dry_run}).")
    print()

    success = 0
    failures: list[str] = []
    for i, call_id in enumerate(call_ids, 1):
        ext = gen_extract_tokens()
        chs = gen_chs_tokens()
        prefix = f"[{i:>3}/{len(call_ids)}] {call_id[:8]}..."

        if args.dry_run:
            print(
                f"{prefix} ext={ext['input']:>4}/{ext['output']:>3} "
                f"(cached {ext['cached_input']:>4}) | "
                f"chs={chs['input']:>4}/{chs['output']:>3} "
                f"(cached {chs['cached_input']:>4})"
            )
            success += 1
            continue

        if update_row(api_key, call_id, ext, chs):
            print(
                f"{prefix} ext_in={ext['input']:>4}, chs_in={chs['input']:>4}, "
                f"cached_pct={int(ext['cached_input']/ext['input']*100) if ext['input'] else 0:>2}/"
                f"{int(chs['cached_input']/chs['input']*100) if chs['input'] else 0:>2}"
            )
            success += 1
        else:
            print(f"{prefix} FAILED")
            failures.append(call_id)

    print()
    print(f"Seeded {success}/{len(call_ids)} rows.")
    if failures:
        print(f"  Failures ({len(failures)}): {', '.join(f[:8] for f in failures[:10])}")
    return 0 if success == len(call_ids) else 1


if __name__ == "__main__":
    sys.exit(main())
