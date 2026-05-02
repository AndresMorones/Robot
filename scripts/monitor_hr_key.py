"""HR API key stability monitor — polls /twin/sql every 5 min for 12 hours.

Captures the EXACT moment HAPPYROBOT_API_KEY stops working (if it does).
Logs every poll to a file with ISO timestamp + status + response preview.

Usage (Terminal B):
    cd C:/Users/Andre/OneDrive/Documentos/GitHub/Robot
    python scripts/monitor_hr_key.py

Reads HAPPYROBOT_API_KEY from env (preferred) or falls back to hardcoded constant.
Logs to scripts/hr-key-monitor.log (gitignored).
"""

import datetime
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

KEY = os.environ.get("HAPPYROBOT_API_KEY", "")
if not KEY:
    sys.stderr.write(
        "ERROR: HAPPYROBOT_API_KEY not set. "
        "Export it before running:\n"
        "  $env:HAPPYROBOT_API_KEY = 'sk_live_...'   (PowerShell)\n"
        "  export HAPPYROBOT_API_KEY=sk_live_...     (bash)\n"
    )
    sys.exit(1)
# Use GET /twin/tables/{name} (lightweight + bypasses Cloudflare WAF rules
# that block certain SQL patterns like `COUNT(*) AS alias`).
URL = "https://platform.happyrobot.ai/api/v2/twin/tables/calls_log?limit=1"
POLL_INTERVAL_SEC = 300
DURATION_SEC = 24 * 3600
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hr-key-monitor.log")


def poll():
    req = urllib.request.Request(
        URL,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Accept": "application/json",
        },
        method="GET",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return resp.getcode(), resp.read()[:300].decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", errors="replace")
    except Exception as e:
        return 0, repr(e)[:300]


def log(line):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    full = f"[{ts}] {line}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(full + "\n")
    print(full, flush=True)


def main():
    start = time.time()
    log(f"=== monitor START key={KEY[:12]}... interval={POLL_INTERVAL_SEC}s duration={DURATION_SEC // 3600}h ===")

    poll_num = 0
    last_status = None
    consecutive_fail = 0
    auth_failure_logged = False
    persistent_failure_logged = False

    while time.time() - start < DURATION_SEC:
        poll_num += 1
        code, body = poll()
        ok = code == 200
        elapsed_min = (time.time() - start) / 60

        if ok:
            consecutive_fail = 0
        else:
            consecutive_fail += 1

        # 401 = auth failure (the smoking gun — key died)
        if code == 401 and not auth_failure_logged:
            log(f"!!! AUTH FAILURE poll#{poll_num} elapsed={elapsed_min:.1f}min status=401 body={body!r}")
            auth_failure_logged = True

        # 3 consecutive non-200 = persistent issue (gateway down, etc.)
        if consecutive_fail >= 3 and not persistent_failure_logged:
            log(f"!!! PERSISTENT FAILURE poll#{poll_num} elapsed={elapsed_min:.1f}min status={code} consecutive={consecutive_fail} body={body!r}")
            persistent_failure_logged = True

        if code != last_status:
            log(f"poll#{poll_num} status={code} CHANGE body={body[:120]!r}")
            last_status = code
        else:
            log(f"poll#{poll_num} status={code}")

        time.sleep(POLL_INTERVAL_SEC)

    log(f"=== monitor END polls={poll_num} auth_failure={'yes' if auth_failure_logged else 'never'} persistent_failure={'yes' if persistent_failure_logged else 'never'} ===")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("=== monitor INTERRUPTED by user ===")
        sys.exit(0)
