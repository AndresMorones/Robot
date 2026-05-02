"""HR Run Python sidecar — `calculate_rate` tool child.

Fires when carrier provides a counter offer. Returns the FINAL floor the agent
must respect for the rest of the negotiation. Pickup-urgency tiers stack on top
of the workflow's `negotiation_floor_pct` variable (replace, not cumulative).

Tier logic (REPLACE, not cumulative):
  pickup > 24h           → urgency_drop = 0.0
  pickup ≤ 24h           → urgency_drop = 0.1
  pickup ≤ 12h           → urgency_drop = 0.2
  pickup ≤ 6h            → urgency_drop = 0.3

Final floor = loadboard_rate × (1 - negotiation_floor_pct - urgency_drop)

Inputs (passed via Input Data fields, all stringified per HR sandbox quirks):
  loadboard_rate          — listed rate of the load (number)
  pickup_datetime         — load pickup time (ISO or HR human format)
  negotiation_floor_pct   — workflow variable (default 0.10)
  now                     — Time.Now (HR human format) — optional, falls back to server time

Output:
  final_floor             — the floor the agent should never go below this round
  urgency_tier            — label: normal / elevated / high / critical / unknown
  hours_until_pickup      — float, or None if unparseable
  base_floor_pct          — workflow var as parsed
  urgency_drop            — tier adjustment applied
  final_floor_pct         — combined floor pct = base + urgency

Sandbox notes (per `reference_hr_python_sandbox_restrictions.md`):
  - NO leading-underscore identifiers (RestrictedPython rejects them)
  - NO `with` blocks
  - NO networking imports
  - Use str(e) not type(e).__name__ in exception strings
  - input_data is provided by HR runtime; output dict is read by HR runtime
"""

import datetime


def parse_float(v, default):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def parse_floor_pct(v):
    pct = parse_float(v, 0.10)
    if pct < 0:
        return 0.10
    if pct > 0.5:
        return 0.10
    return pct


def parse_human_dt(s):
    """Parse HR human format: 'Monday, April 27, 2026 at 7:38:35 AM EDT'.
    Returns naive datetime (timezone stripped) or None.
    """
    if not s or not isinstance(s, str):
        return None
    if " at " not in s:
        return None
    try:
        parts = s.split(" at ", 1)
        date_part = parts[0].strip()
        time_part = parts[1].strip()
        date_tokens = date_part.split(", ")
        if len(date_tokens) < 3:
            return None
        month_day_year = date_tokens[1] + ", " + date_tokens[2]
        time_tokens = time_part.split()
        time_str = time_tokens[0]
        ampm = time_tokens[1].upper() if len(time_tokens) > 1 else "AM"
        combined = month_day_year + " " + time_str + " " + ampm
        return datetime.datetime.strptime(combined, "%B %d, %Y %I:%M:%S %p")
    except Exception:
        return None


def parse_iso_dt(s):
    if not s or not isinstance(s, str):
        return None
    try:
        clean = s.strip().replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


def parse_dt(s):
    dt = parse_iso_dt(s)
    if dt is not None:
        return dt
    return parse_human_dt(s)


def hours_until(pickup_str, now_str):
    pickup_dt = parse_dt(pickup_str)
    if pickup_dt is None:
        return None
    now_dt = parse_dt(now_str) if now_str else None
    if now_dt is None:
        now_dt = datetime.datetime.now()
    delta = pickup_dt - now_dt
    return delta.total_seconds() / 3600.0


def urgency_drop_for_hours(hours):
    if hours is None:
        return 0.0
    if hours <= 6:
        return 0.3
    if hours <= 12:
        return 0.2
    if hours <= 24:
        return 0.1
    return 0.0


def urgency_label_for_hours(hours):
    if hours is None:
        return "unknown"
    if hours <= 6:
        return "critical"
    if hours <= 12:
        return "high"
    if hours <= 24:
        return "elevated"
    return "normal"


inp = input_data or {}
loadboard_rate = parse_float(inp.get("loadboard_rate"), 0.0)
base_floor_pct = parse_floor_pct(inp.get("negotiation_floor_pct"))
pickup_str = inp.get("pickup_datetime")
# Accept either key name from HR Input Data binding: `now` or `now_iso`.
# HR's Time.Now picker may surface as `now_iso` (the Eastern-time variant) or plain `now`.
now_str = inp.get("now") or inp.get("now_iso")

hours = hours_until(pickup_str, now_str)
urgency_drop = urgency_drop_for_hours(hours)
final_floor_pct = base_floor_pct + urgency_drop
if final_floor_pct > 0.5:
    final_floor_pct = 0.5

final_floor = loadboard_rate * (1.0 - final_floor_pct)

output = {
    "final_floor": round(final_floor, 2),
    "urgency_tier": urgency_label_for_hours(hours),
    "hours_until_pickup": round(hours, 1) if hours is not None else None,
    "base_floor_pct": base_floor_pct,
    "urgency_drop": urgency_drop,
    "final_floor_pct": final_floor_pct,
}
