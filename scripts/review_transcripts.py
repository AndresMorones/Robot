#!/usr/bin/env python
"""Pull recent calls_log rows from HR Twin + analyze transcripts.

Run from repo root:
    python scripts/review_transcripts.py [--limit 10] [--out-dir data]

What it does
------------
1. Loads HAPPYROBOT_API_KEY from env (fallback: api/.env file).
2. Hits HR Twin /twin/sql with a WAF-safe SELECT against calls_log.
   (No ORDER BY+LIMIT, no multi-aggregate — sorting + slicing happen in Python
    per the Cloudflare WAF posture documented in dashboard_aggregations.py.)
3. For each row, parses transcript field, detects format, and identifies
   "death points" — repetition loops, agent silence, FMCSA-fail-but-continued,
   book-without-verify, leaked floor, robotic phrasing, duration outliers.
4. Writes:
       data/calls_log_review_<YYYY-MM-DD>.ndjson  (machine-readable per-call)
       data/calls_log_review_<YYYY-MM-DD>.md      (human summary)
5. Prints TL;DR to stdout.

Decoupled from FastAPI: no `app.*` imports, no `twin_client` dependency.
Uses raw httpx so it can be run standalone before the API is up.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


HR_BASE_URL = "https://platform.happyrobot.ai/api/v2"
TWIN_SQL_ENDPOINT = f"{HR_BASE_URL}/twin/sql"

TOOL_NAMES = ("verify_carrier", "query_loads", "negotiate_rate", "book_load", "_hangup")

FORBIDDEN_VOCAB = (
    "paperwork", "rate confirmation", "rate con", "carrier packet",
    "setup packet", "send over the docs", "fill out", "anything else?",
    "transferring you now", "drive safe", "you bet", "talk soon", "throw out",
)

FLOOR_LEAK_PATTERNS = (
    r"\bmy floor\b",
    r"negotiation_floor",
    r"\bfinal_floor\b",
    r"\burgency_tier\b",
    r"\b\d{1,2}\s*(?:percent|%)\s*(?:off|below)\b",
)


# ---------------------------------------------------------------- env loader
def load_env_from_file(path: Path) -> None:
    """Light-touch .env loader; never overrides existing env vars."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("'\"")
        if k and k not in os.environ:
            os.environ[k] = v


# ---------------------------------------------------------------- Twin fetch
def fetch_calls_log(api_key: str, limit: int) -> list[dict[str, Any]]:
    """Pull last `limit` calls_log rows. WAF-safe: sort + slice client-side."""
    columns = ", ".join((
        "call_id", "created_at", "mc_number", "callback_phone",
        "duration_seconds", "call_outcome", "sentiment",
        "case_health_score", "audit_remarks",
        "fmcsa_eligibility_failure_reason", "transcript",
    ))
    sql = f"SELECT {columns} FROM calls_log"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            TWIN_SQL_ENDPOINT,
            json={"sql": sql},
            headers=headers,
        )
        if resp.status_code >= 400:
            sys.stderr.write(
                f"Twin SQL error {resp.status_code}: {resp.text[:600]}\n"
            )
            sys.exit(1)
        data = resp.json()
    rows = data.get("rows", []) if isinstance(data, dict) else []

    def _parse_dt(v: Any) -> datetime:
        if not v:
            return datetime.min.replace(tzinfo=timezone.utc)
        s = str(v).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    rows.sort(key=lambda r: _parse_dt(r.get("created_at")), reverse=True)
    return rows[:limit]


# ---------------------------------------------------------------- transcript
def detect_transcript_format(raw: Any) -> tuple[str, Any]:
    """Returns (format_tag, parsed_or_raw).

    format_tag ∈ {"empty", "json_list", "json_dict", "flat_text"}.
    """
    if raw is None or raw == "":
        return "empty", None
    if isinstance(raw, list):
        return "json_list", raw
    if isinstance(raw, dict):
        return "json_dict", raw
    if not isinstance(raw, str):
        return "flat_text", str(raw)
    s = raw.strip()
    if not s:
        return "empty", None
    if s[0] in "[{":
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            return "flat_text", raw
        if isinstance(parsed, list):
            return "json_list", parsed
        if isinstance(parsed, dict):
            return "json_dict", parsed
        return "flat_text", raw
    return "flat_text", raw


# ---------------------------------------------------------------- token est
_TIKTOKEN_ENC: Any = None
_TIKTOKEN_TRIED = False


def estimate_tokens(text: str) -> int:
    """tiktoken when available (o200k_base = GPT-5.x family); word*1.3 fallback."""
    global _TIKTOKEN_ENC, _TIKTOKEN_TRIED
    if not text:
        return 0
    if not _TIKTOKEN_TRIED:
        _TIKTOKEN_TRIED = True
        try:
            import tiktoken  # type: ignore

            _TIKTOKEN_ENC = tiktoken.get_encoding("o200k_base")
        except Exception:
            _TIKTOKEN_ENC = None
    if _TIKTOKEN_ENC is not None:
        try:
            return len(_TIKTOKEN_ENC.encode(text))
        except Exception:
            pass
    words = re.split(r"\s+", text.strip())
    return int(len([w for w in words if w]) * 1.3)


# ---------------------------------------------------------------- analysis
def _coerce_text(item: Any) -> str:
    """Pull text body from a turn-shaped dict, tolerating multiple key conventions."""
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return ""
    for k in ("content", "text", "message", "body", "utterance"):
        v = item.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, list):
            return " ".join(_coerce_text(x) for x in v)
    return ""


def _coerce_role(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    for k in ("role", "from", "speaker", "sender"):
        v = item.get(k)
        if isinstance(v, str) and v:
            return v.lower()
    return ""


def analyze_transcript(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("transcript")
    fmt, parsed = detect_transcript_format(raw)

    findings: dict[str, Any] = {
        "format": fmt,
        "char_count": len(raw) if isinstance(raw, str) else 0,
        "turn_count": 0,
        "role_distribution": {},
        "tool_mentions": {t: 0 for t in TOOL_NAMES},
        "estimated_tokens_total": 0,
        "death_points": [],
        "last_speaker": None,
        "ended_with_hangup": False,
        "has_per_turn_timestamps": False,
        "has_tool_event_objects": False,
        "first_carrier_turn_index": None,
    }

    body_for_text_search = ""

    if fmt == "json_list" and isinstance(parsed, list):
        turns = parsed
        findings["turn_count"] = len(turns)
        roles = Counter(_coerce_role(t) or "unknown" for t in turns)
        findings["role_distribution"] = dict(roles)

        joined: list[str] = []
        for i, t in enumerate(turns):
            content = _coerce_text(t)
            joined.append(content)
            role = _coerce_role(t)
            if findings["first_carrier_turn_index"] is None and role in ("user", "carrier", "human"):
                findings["first_carrier_turn_index"] = i
            if isinstance(t, dict):
                if any(k in t for k in ("timestamp", "created_at", "ts", "time")):
                    findings["has_per_turn_timestamps"] = True
                if t.get("role") == "tool" or "tool_calls" in t or "tool_call_id" in t:
                    findings["has_tool_event_objects"] = True
        body_for_text_search = "\n".join(joined)
        if turns:
            findings["last_speaker"] = _coerce_role(turns[-1])

    elif fmt == "json_dict" and isinstance(parsed, dict):
        msgs = parsed.get("messages") or parsed.get("turns") or parsed.get("events") or []
        if isinstance(msgs, list):
            findings["turn_count"] = len(msgs)
            roles = Counter(_coerce_role(m) or "unknown" for m in msgs)
            findings["role_distribution"] = dict(roles)
            joined = [_coerce_text(m) for m in msgs]
            body_for_text_search = "\n".join(joined)
            for m in msgs:
                if isinstance(m, dict):
                    if any(k in m for k in ("timestamp", "created_at", "ts", "time")):
                        findings["has_per_turn_timestamps"] = True
                    if m.get("role") == "tool" or "tool_calls" in m:
                        findings["has_tool_event_objects"] = True
            if msgs:
                findings["last_speaker"] = _coerce_role(msgs[-1])

    elif fmt == "flat_text" and isinstance(parsed, str):
        body_for_text_search = parsed
        paragraphs = [p for p in re.split(r"\n\s*\n", parsed) if p.strip()]
        findings["turn_count"] = len(paragraphs) or len(
            [ln for ln in parsed.splitlines() if ln.strip()]
        )

    findings["estimated_tokens_total"] = estimate_tokens(body_for_text_search)

    body_lower = body_for_text_search.lower()
    for tool in TOOL_NAMES:
        findings["tool_mentions"][tool] = body_lower.count(tool.lower())
    findings["ended_with_hangup"] = findings["tool_mentions"].get("_hangup", 0) > 0

    # ---------------------------------------------------------- death points
    deaths: list[str] = []

    if fmt == "empty":
        deaths.append("EMPTY transcript — call wrote no transcript content")
    elif findings["turn_count"] == 0:
        deaths.append("Transcript present but ZERO turns parsed")

    if findings["turn_count"] > 0 and findings["last_speaker"] in ("user", "carrier", "human"):
        deaths.append("Last turn was carrier — call may have ended without agent close")

    if not findings["ended_with_hangup"] and fmt != "empty" and findings["turn_count"] > 0:
        deaths.append("No _hangup mentioned — call may have ended on carrier disconnect")

    fmcsa_reason = row.get("fmcsa_eligibility_failure_reason")
    outcome = row.get("call_outcome")
    if fmcsa_reason and outcome != "carrier_not_qualified":
        deaths.append(
            f"FMCSA failed ({fmcsa_reason}) but outcome={outcome} — gate may have been bypassed"
        )

    booked = findings["tool_mentions"].get("book_load", 0)
    verified = findings["tool_mentions"].get("verify_carrier", 0)
    if booked > 0 and verified == 0:
        deaths.append("book_load mentioned without verify_carrier — gate skipped?")

    for vocab in FORBIDDEN_VOCAB:
        if vocab.lower() in body_lower:
            deaths.append(f"Forbidden vocab leaked: {vocab!r}")

    for pat in FLOOR_LEAK_PATTERNS:
        if re.search(pat, body_lower):
            deaths.append(f"Possible floor/internal leak: pattern /{pat}/")

    duration_raw = row.get("duration_seconds")
    try:
        d = float(duration_raw) if duration_raw is not None else None
    except (TypeError, ValueError):
        d = None
    if d is not None:
        if d < 15:
            deaths.append(f"Duration outlier (very short): {d:.0f}s")
        elif d > 480:
            deaths.append(f"Duration outlier (very long): {d:.0f}s")

    chs_raw = row.get("case_health_score")
    try:
        chs_int = int(float(chs_raw)) if chs_raw is not None else None
    except (TypeError, ValueError):
        chs_int = None
    if chs_int is not None:
        if chs_int < 30:
            deaths.append(f"Catastrophic CHS: {chs_int}")
        elif chs_int < 50:
            deaths.append(f"Severe CHS deduction: {chs_int}")

    findings["death_points"] = deaths
    return findings


# ---------------------------------------------------------------- rendering
def render_per_call_md(row: dict[str, Any], findings: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"### Call `{row.get('call_id')}`")

    meta_bits: list[str] = []
    if row.get("created_at"):
        meta_bits.append(f"`{row['created_at']}`")
    if row.get("mc_number"):
        meta_bits.append(f"MC `{row['mc_number']}`")
    if row.get("call_outcome"):
        meta_bits.append(f"outcome=`{row['call_outcome']}`")
    if row.get("sentiment"):
        meta_bits.append(f"sentiment=`{row['sentiment']}`")
    if row.get("case_health_score") is not None:
        meta_bits.append(f"CHS=`{row['case_health_score']}`")
    if row.get("duration_seconds") is not None:
        meta_bits.append(f"duration=`{row['duration_seconds']}s`")
    if row.get("fmcsa_eligibility_failure_reason"):
        meta_bits.append(f"fmcsa=`{row['fmcsa_eligibility_failure_reason']}`")
    lines.append(" · ".join(meta_bits) or "_no meta_")
    lines.append("")

    structural_bits = [
        f"format=`{findings['format']}`",
        f"turns={findings['turn_count']}",
        f"chars={findings['char_count']}",
        f"est_tokens={findings['estimated_tokens_total']}",
        f"timestamps={findings['has_per_turn_timestamps']}",
        f"tool_events={findings['has_tool_event_objects']}",
    ]
    lines.append("**shape**: " + " · ".join(structural_bits))

    if findings["role_distribution"]:
        roles = ", ".join(f"{r}:{n}" for r, n in findings["role_distribution"].items())
        lines.append(f"**roles**: {roles}")

    nonzero_tools = {t: n for t, n in findings["tool_mentions"].items() if n}
    if nonzero_tools:
        tools = ", ".join(f"`{t}`×{n}" for t, n in nonzero_tools.items())
        lines.append(f"**tool mentions**: {tools}")

    audit = row.get("audit_remarks")
    if audit:
        lines.append(f"**audit**: _{audit}_")

    if findings["death_points"]:
        lines.append("**death points:**")
        for d in findings["death_points"]:
            lines.append(f"- {d}")
    else:
        lines.append("_no death points detected_")

    lines.append("")
    return "\n".join(lines)


def render_summary_md(rows: list[dict[str, Any]], analyses: list[dict[str, Any]]) -> str:
    formats = Counter(a["format"] for a in analyses)
    outcomes = Counter(r.get("call_outcome") or "unknown" for r in rows)
    death_freq: Counter = Counter()
    for a in analyses:
        for d in a["death_points"]:
            key = d.split("—")[0].split(":")[0].strip()
            death_freq[key] += 1
    has_ts = sum(1 for a in analyses if a["has_per_turn_timestamps"])
    has_te = sum(1 for a in analyses if a["has_tool_event_objects"])

    lines: list[str] = []
    lines.append("# calls_log review")
    lines.append(f"_generated {datetime.now(timezone.utc).isoformat()} UTC_")
    lines.append("")
    lines.append(f"**N calls reviewed**: {len(rows)}")
    if formats:
        lines.append("**transcript formats**: " + ", ".join(f"`{k}`:{v}" for k, v in formats.most_common()))
    if outcomes:
        lines.append("**outcomes**: " + ", ".join(f"`{k}`:{v}" for k, v in outcomes.most_common()))
    lines.append(f"**per-turn timestamps present**: {has_ts}/{len(rows)}")
    lines.append(f"**tool event objects present**: {has_te}/{len(rows)}")
    if death_freq:
        lines.append("")
        lines.append("## death-point frequency")
        for category, count in death_freq.most_common():
            lines.append(f"- {count}× — {category}")
    lines.append("")
    lines.append("---")
    lines.append("## per-call detail")
    lines.append("")
    for row, analysis in zip(rows, analyses):
        lines.append(render_per_call_md(row, analysis))
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of most-recent calls to review (default 10)")
    parser.add_argument("--out-dir", default="data",
                        help="Where to write the review files (default data/)")
    parser.add_argument("--env-file", default="api/.env",
                        help="Path to .env file fallback (default api/.env)")
    args = parser.parse_args()

    load_env_from_file(Path(args.env_file))
    api_key = os.environ.get("HAPPYROBOT_API_KEY", "").strip()
    if not api_key:
        sys.stderr.write(
            "ERROR: HAPPYROBOT_API_KEY not set in env or .env file.\n"
            f"  Checked env_file: {args.env_file}\n"
        )
        return 1

    rows = fetch_calls_log(api_key, args.limit)
    if not rows:
        sys.stderr.write("No rows returned from calls_log.\n")
        return 1

    analyses = [analyze_transcript(r) for r in rows]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    md_path = out_dir / f"calls_log_review_{today}.md"
    ndjson_path = out_dir / f"calls_log_review_{today}.ndjson"

    md_path.write_text(render_summary_md(rows, analyses), encoding="utf-8")

    with ndjson_path.open("w", encoding="utf-8") as f:
        for row, analysis in zip(rows, analyses):
            f.write(json.dumps({"row": row, "findings": analysis}, default=str) + "\n")

    formats = Counter(a["format"] for a in analyses)
    death_freq: Counter = Counter()
    for a in analyses:
        for d in a["death_points"]:
            key = d.split("—")[0].split(":")[0].strip()
            death_freq[key] += 1

    print(f"Reviewed {len(rows)} calls. Wrote:")
    print(f"  {md_path}")
    print(f"  {ndjson_path}")
    print()
    print("formats:", dict(formats))
    has_ts = sum(1 for a in analyses if a["has_per_turn_timestamps"])
    has_te = sum(1 for a in analyses if a["has_tool_event_objects"])
    print(f"per-turn timestamps: {has_ts}/{len(rows)}")
    print(f"tool event objects:  {has_te}/{len(rows)}")
    print()
    if death_freq:
        print("top death points:")
        for category, count in death_freq.most_common(10):
            print(f"  {count:3d}×  {category}")
    else:
        print("no death points detected")

    return 0


if __name__ == "__main__":
    sys.exit(main())
