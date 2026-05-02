# HR Run Python action — calculate_rate sidecar
#
# Capability-demo for the inbound carrier voice agent.
# 18:00-23:59 America/New_York: floor relaxes by 0.5 percentage points (EOD inventory pressure).
# Daytime: floor unchanged.
#
# RestrictedPython sandbox constraints (per reference_hr_python_sandbox_restrictions.md):
#   - No leading-underscore identifiers (variables, functions, aliases)
#   - No dunder access (__name__, __class__, etc.)
#   - No networking modules (urllib still works for plain stdlib HTTP if needed)
#   - HR's Time.Now picker returns human format like "Monday, April 27, 2026 at 7:38:35 AM EDT"
#
# Input Data (HR @ picker mappings):
#   loadboard_rate          number   from upstream Tool param calculate_rate.loadboard_rate
#   negotiation_floor_pct   number   from Workflow Variables → negotiation_floor_pct
#   now_iso                 string   from Time → Now (HR human format OR ISO; both handled)
#
# Output:
#   adjusted_floor          number   the dollar floor for the agent to use as F
#   floor_adjustment        number   delta in percentage points (negative = relaxed downward)
#   effective_floor_pct     number   the discount fraction actually applied
#   reason_code             string   "EOD_NY" or "DAYTIME_NY"
#   applied_at_hour         number   the hour-of-day used (0-23)
#   loadboard_rate          number   echo

import datetime

try:
    import pytz
    NY = pytz.timezone("America/New_York")
except Exception:
    NY = None


def to_float(v, default):
    try:
        return float(v)
    except Exception:
        return default


def parse_hour(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    # Try ISO 8601 first
    try:
        dt_obj = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt_obj.hour
    except Exception:
        pass
    # Try HR human format: "Monday, April 27, 2026 at 7:38:35 AM EDT"
    if " at " in s:
        try:
            time_part = s.split(" at ", 1)[1]
            tokens = time_part.split()
            time_str = tokens[0]
            ampm = ""
            if len(tokens) > 1:
                ampm = tokens[1].upper()
            hour_val = int(time_str.split(":")[0])
            if ampm == "PM" and hour_val < 12:
                hour_val = hour_val + 12
            elif ampm == "AM" and hour_val == 12:
                hour_val = 0
            return hour_val
        except Exception:
            pass
    return None


inp = input_data or {}
loadboard_rate = to_float(inp.get("loadboard_rate"), 0.0)
floor_pct = to_float(inp.get("negotiation_floor_pct"), 0.10)

hour = parse_hour(inp.get("now_iso"))

if hour is None:
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if NY is not None:
        try:
            hour = now_utc.astimezone(NY).hour
        except Exception:
            hour = now_utc.hour
    else:
        hour = now_utc.hour

if 18 <= hour <= 23:
    floor_adjustment_pct = -0.5
    reason_code = "EOD_NY"
else:
    floor_adjustment_pct = 0.0
    reason_code = "DAYTIME_NY"

effective_floor_pct = max(0.0, min(0.5, floor_pct + abs(floor_adjustment_pct) / 100.0))
adjusted_floor = round(loadboard_rate * (1.0 - effective_floor_pct), 2)

output = {
    "adjusted_floor": adjusted_floor,
    "floor_adjustment": floor_adjustment_pct,
    "effective_floor_pct": round(effective_floor_pct, 4),
    "reason_code": reason_code,
    "applied_at_hour": hour,
    "loadboard_rate": loadboard_rate,
}
