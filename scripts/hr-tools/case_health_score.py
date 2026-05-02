# HR Run Python action — case_health_score
#
# Customer-experience deduction model: start at 100, subtract for failures.
# CHS measures how the call FELT to the carrier, not whether the agent was compliant.
# FMCSA decline is correct business behavior and does NOT deduct.
# Customer disengagement, customer dissatisfaction, and agent role-breaks DO deduct.
#
# RestrictedPython sandbox constraints (verified 2026-04-26/27):
#   - No leading-underscore identifiers (vars, functions, aliases)
#   - No dunder access (__name__, __class__, etc.)
#   - No networking modules
#   - re, datetime, json, math allowed
#
# Input Data (HR @ picker mappings):
#   transcript                        string  Voice Agent.transcript (full call)
#   sentiment_end                     string  Classify Sentiment.response.sentiment
#   sentiment_start                   string  optional — same node if it emits start, else default neutral
#   call_outcome                      string  Classify Outcome.response.call_outcome
#   duration_seconds                  number  Voice Agent AIC duration (optional)
#
# Output:
#   case_health_score   int 0-100
#   deductions          list of {code, points, why} entries
#   rationale           string <=200 chars
#
# Threshold: 70 = pass. Most clean calls land 90-100. Bad reactions / disconnects / role breaks drop below 70.

import re

PASSING_THRESHOLD = 70

# ---- DEDUCTION CONSTANTS (edit here to retune) -----------------------------

DEDUCT_DISCONNECT_MID_CALL = 25
DEDUCT_NO_ANSWER = 30
DEDUCT_AGENT_SILENT_LONG = 20
DEDUCT_AGENT_REPEAT_LOOP = 15
DEDUCT_TOOL_LEAK = 15
DEDUCT_FLOOR_LEAK = 15
DEDUCT_AUTHORITY_ACCEPTED = 25
DEDUCT_VERY_NEGATIVE_END = 20

DEDUCT_NEGATIVE_END = 10
DEDUCT_SENTIMENT_INVERSION = 15
DEDUCT_VAR_LEAK = 10
DEDUCT_BOOKED_NO_READBACK = 8
DEDUCT_ROUND_NUMBER_EACH = 3
DEDUCT_ROUND_NUMBER_CAP = 6
DEDUCT_OVER_THREE_ROUNDS = 5
DEDUCT_ESCALATION_PHRASE = 10

NO_ANSWER_DURATION_THRESHOLD = 30  # seconds
SHORT_CALL_NO_RESOLUTION_THRESHOLD = 30  # seconds

# ---- DETECTION PATTERNS ----------------------------------------------------

TOOL_NAME_PATTERNS = [
    r"\bverify_carrier\b",
    r"\bsearch_loads_by_lane\b",
    r"\bfind_available_loads\b",
    r"\bcalculate_rate\b",
    r"\bapply_demo_adjustment\b",
]

VAR_NAME_PATTERNS = [
    r"\bnegotiation_floor_pct\b",
    r"\bmax_negotiation_rounds\b",
    r"\bagent_name\b",
    r"\bcompany_name\b",
]

FLOOR_LEAK_PATTERNS = [
    r"my floor is",
    r"the floor (?:is|on this)",
    r"my minimum",
    r"lowest i can (?:do|go)",
    r"bottom number",
    r"\d+\s*(?:percent|%)\s*(?:off|discount|below)",
    r"we discount",
    r"hard cap at",
]

ESCALATION_PATTERNS = [
    r"waste of my time",
    r"you'?re useless",
    r"this is a joke",
    r"you guys are way off",
    r"\brip(?:ping)? me off\b",
    r"\bripoff\b",
    r"forget it",
    r"never calling back",
    r"i'?m done",
]

READBACK_PATTERNS = [
    r"that'?s load-",
    r"recap",
    r"so to confirm",
    r"alright[,]? (?:that'?s|we have)",
    r"transfer was successful",
]

ROUND_NUMBER_PATTERN = re.compile(r"\$\s?\d{1,3}(?:[,.]?\d{3})*?[,.]?(?:000|500)\b")

# ---- HELPERS ---------------------------------------------------------------

def lower_safe(v):
    if v is None:
        return ""
    try:
        return str(v).lower()
    except Exception:
        return ""

def to_float(v, default):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def to_int(v, default):
    try:
        if v is None:
            return default
        return int(float(v))
    except Exception:
        return default

def any_match(text, patterns):
    for pat in patterns:
        if re.search(pat, text):
            return True
    return False

def count_matches(text, patterns):
    total = 0
    for pat in patterns:
        total = total + len(re.findall(pat, text))
    return total

def sentiment_rank(s):
    table = {
        "very_negative": -2,
        "negative": -1,
        "neutral": 0,
        "positive": 1,
        "very_positive": 2,
    }
    return table.get(s, 0)

def split_turns(text):
    # Best-effort speaker split. Transcripts vary; this catches "Agent:" / "Carrier:" labels.
    # Falls back to single block if labels absent.
    lines = text.split("\n")
    agent_lines = []
    carrier_lines = []
    for line in lines:
        ls = line.strip().lower()
        if ls.startswith("agent:") or ls.startswith("paul:") or ls.startswith("broker:"):
            agent_lines.append(ls)
        elif ls.startswith("carrier:") or ls.startswith("driver:") or ls.startswith("dispatcher:"):
            carrier_lines.append(ls)
    return ("\n".join(agent_lines), "\n".join(carrier_lines))

def detect_repeat_loop(agent_text):
    # Simple: find any 30-char substring that repeats 2+ times
    if len(agent_text) < 60:
        return False
    seen = {}
    step = 10
    win = 30
    i = 0
    while i + win <= len(agent_text):
        chunk = agent_text[i:i + win]
        if len(chunk.strip()) >= 20:
            seen[chunk] = seen.get(chunk, 0) + 1
            if seen[chunk] >= 2:
                return True
        i = i + step
    return False

# ---- MAIN ------------------------------------------------------------------

inp = input_data or {}
transcript_raw = inp.get("transcript") or ""
transcript = lower_safe(transcript_raw)
sentiment_end = lower_safe(inp.get("sentiment_end")).strip() or "neutral"
sentiment_start = lower_safe(inp.get("sentiment_start")).strip() or "neutral"
call_outcome = lower_safe(inp.get("call_outcome")).strip() or "call_abandoned"
duration_seconds = to_float(inp.get("duration_seconds"), 0.0)

agent_text, carrier_text = split_turns(transcript)
# Fallback: if no labels detected, treat full transcript as agent-side for leak detection
if not agent_text:
    agent_text = transcript

deductions = []
score = 100

# --- HARD: customer disengagement -------------------------------------------

if call_outcome == "call_abandoned":
    if duration_seconds > 0 and duration_seconds < NO_ANSWER_DURATION_THRESHOLD:
        score = score - DEDUCT_NO_ANSWER
        deductions.append({"code": "no_answer", "points": DEDUCT_NO_ANSWER, "why": "carrier did not engage past greeting"})
    else:
        score = score - DEDUCT_DISCONNECT_MID_CALL
        deductions.append({"code": "disconnect_mid_call", "points": DEDUCT_DISCONNECT_MID_CALL, "why": "call ended without resolution"})

# --- HARD: agent role breaks ------------------------------------------------

if any_match(agent_text, TOOL_NAME_PATTERNS):
    score = score - DEDUCT_TOOL_LEAK
    deductions.append({"code": "tool_name_leak", "points": DEDUCT_TOOL_LEAK, "why": "agent disclosed internal tool name"})

if any_match(agent_text, FLOOR_LEAK_PATTERNS):
    score = score - DEDUCT_FLOOR_LEAK
    deductions.append({"code": "floor_leak", "points": DEDUCT_FLOOR_LEAK, "why": "agent disclosed floor or discount math"})

if any_match(agent_text, VAR_NAME_PATTERNS):
    score = score - DEDUCT_VAR_LEAK
    deductions.append({"code": "var_name_leak", "points": DEDUCT_VAR_LEAK, "why": "agent disclosed internal variable name"})

if detect_repeat_loop(agent_text):
    score = score - DEDUCT_AGENT_REPEAT_LOOP
    deductions.append({"code": "agent_repeat_loop", "points": DEDUCT_AGENT_REPEAT_LOOP, "why": "agent repeated same utterance verbatim"})

# --- HARD: customer dissatisfaction (very_negative) -------------------------

if sentiment_end == "very_negative":
    score = score - DEDUCT_VERY_NEGATIVE_END
    deductions.append({"code": "very_negative_end", "points": DEDUCT_VERY_NEGATIVE_END, "why": "carrier ended call hostile or angry"})

# --- SOFT: sentiment trajectory ---------------------------------------------

if sentiment_end == "negative":
    score = score - DEDUCT_NEGATIVE_END
    deductions.append({"code": "negative_end", "points": DEDUCT_NEGATIVE_END, "why": "carrier ended unhappy"})

start_rank = sentiment_rank(sentiment_start)
end_rank = sentiment_rank(sentiment_end)
if start_rank >= 1 and end_rank <= -1:
    score = score - DEDUCT_SENTIMENT_INVERSION
    deductions.append({"code": "sentiment_inversion", "points": DEDUCT_SENTIMENT_INVERSION, "why": "started positive, ended negative — agent inflamed"})

# --- SOFT: escalation language ----------------------------------------------

if carrier_text and any_match(carrier_text, ESCALATION_PATTERNS):
    score = score - DEDUCT_ESCALATION_PHRASE
    deductions.append({"code": "carrier_escalation", "points": DEDUCT_ESCALATION_PHRASE, "why": "carrier used escalation language"})

# --- SOFT: booking flow issues ----------------------------------------------

if call_outcome == "load_booked":
    if not any_match(agent_text, READBACK_PATTERNS):
        score = score - DEDUCT_BOOKED_NO_READBACK
        deductions.append({"code": "booked_no_readback", "points": DEDUCT_BOOKED_NO_READBACK, "why": "booking confirmed without explicit readback"})

# --- SOFT: round-number counters --------------------------------------------

round_count = len(ROUND_NUMBER_PATTERN.findall(agent_text))
if round_count > 0:
    rn_deduct = min(round_count * DEDUCT_ROUND_NUMBER_EACH, DEDUCT_ROUND_NUMBER_CAP)
    score = score - rn_deduct
    deductions.append({"code": "round_number_counter", "points": rn_deduct, "why": "agent used round-thousand dollar amounts"})

# --- SOFT: over 3 rounds ----------------------------------------------------

round_mentions = len(re.findall(r"\bround\s+(?:one|two|three|four|five|1|2|3|4|5)\b", transcript))
if round_mentions > 3:
    score = score - DEDUCT_OVER_THREE_ROUNDS
    deductions.append({"code": "over_three_rounds", "points": DEDUCT_OVER_THREE_ROUNDS, "why": "negotiation exceeded 3-round limit"})

# --- Clamp + rationale ------------------------------------------------------

if score < 0:
    score = 0
if score > 100:
    score = 100

status = "pass" if score >= PASSING_THRESHOLD else "below threshold"
if not deductions:
    rationale = "Score 100. Clean call — outcome=" + call_outcome + ", sentiment=" + sentiment_end + "."
else:
    top = deductions[0]["code"]
    rationale = "Score " + str(score) + " (" + status + "). " + str(len(deductions)) + " deductions; primary: " + top + "."

if len(rationale) > 200:
    rationale = rationale[:197] + "..."

output = {
    "case_health_score": int(score),
    "deductions": deductions,
    "rationale": rationale,
}
