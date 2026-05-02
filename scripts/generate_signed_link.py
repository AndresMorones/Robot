"""Generate a signed dashboard access link.

Usage (PowerShell):
    cd C:\\Users\\Andre\\OneDrive\\Documentos\\GitHub\\Robot
    $env:LINK_SIGNING_SECRET = "<your-32-byte-hex-secret>"
    python scripts\\generate_signed_link.py
    # optional: --days 14 --base https://robot-dashboard-andres-morones.fly.dev

Output: full URL ready to paste into the email.

The same LINK_SIGNING_SECRET must be set as a Fly secret on the dashboard app:
    fly secrets set LINK_SIGNING_SECRET=$env:LINK_SIGNING_SECRET --app robot-dashboard-andres-morones
"""

import argparse
import hashlib
import hmac
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30, help="Validity period in days (default 30)")
    parser.add_argument(
        "--base",
        default="https://robot-dashboard-andres-morones.fly.dev",
        help="Dashboard base URL",
    )
    args = parser.parse_args()

    secret = os.environ.get("LINK_SIGNING_SECRET", "")
    if not secret:
        print("ERROR: set LINK_SIGNING_SECRET env var first.", file=sys.stderr)
        print("PowerShell: $env:LINK_SIGNING_SECRET = '<hex-secret>'", file=sys.stderr)
        sys.exit(1)

    exp = int(time.time()) + args.days * 86400
    sig = hmac.new(secret.encode(), str(exp).encode(), hashlib.sha256).hexdigest()
    token = f"{exp}.{sig}"

    base = args.base.rstrip("/")
    url = f"{base}/?t={token}"
    print(url)
    print(f"\n(valid for {args.days} days; expires at unix {exp} = "
          f"{time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(exp))})", file=sys.stderr)


if __name__ == "__main__":
    main()
