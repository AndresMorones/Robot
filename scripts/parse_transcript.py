"""CLI wrapper around scripts/transcript_parser.py::parse_transcript.

Reads a transcript JSON document (a list of turn dicts) from --file or stdin
and writes the parsed result as JSON to stdout.

Exit codes:
  0  success
  2  input JSON failed to parse  -> {"error": "...", "stage": "input_parse"}
  3  unexpected parse error       -> {"error": "...", "stage": "parse"}

Usage examples
--------------

Bash (pipe stdin):
    cat transcript.json | python scripts/parse_transcript.py --pretty

Next.js route handler (real consumer — lift into your own file):

    // dashboard/src/app/api/parse-transcript/route.ts
    import { spawn } from 'node:child_process';

    export async function POST(req: Request) {
      const transcript = await req.json();
      return new Promise<Response>((resolve) => {
        const proc = spawn('python', ['scripts/parse_transcript.py']);
        let out = '', err = '';
        proc.stdout.on('data', (d) => (out += d));
        proc.stderr.on('data', (d) => (err += d));
        proc.on('close', (code) => {
          if (code !== 0) resolve(Response.json({ error: err || out }, { status: 500 }));
          else resolve(new Response(out, { headers: { 'content-type': 'application/json' } }));
        });
        proc.stdin.write(JSON.stringify(transcript));
        proc.stdin.end();
      });
    }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_parser import parse_transcript  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse a transcript JSON document.")
    ap.add_argument("--file", help="Path to transcript JSON. Reads stdin if omitted.")
    ap.add_argument("--pretty", action="store_true", help="Indent output JSON.")
    args = ap.parse_args()

    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()

    try:
        turns = json.loads(raw)
    except json.JSONDecodeError as e:
        json.dump({"error": str(e), "stage": "input_parse"}, sys.stdout)
        return 2

    try:
        result = parse_transcript(turns)
    except Exception as e:
        json.dump({"error": str(e), "stage": "parse"}, sys.stdout)
        return 3

    json.dump(result, sys.stdout, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
