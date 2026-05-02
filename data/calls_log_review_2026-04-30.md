# calls_log review
_generated 2026-04-30T17:12:14.525007+00:00 UTC_

**N calls reviewed**: 3
**transcript formats**: `json_list`:3
**outcomes**: `call_abandoned`:2, `no_match`:1
**per-turn timestamps present**: 0/3
**tool event objects present**: 3/3

## death-point frequency
- 4× — Possible floor/internal leak
- 3× — No _hangup mentioned

---
## per-call detail

### Call `0b36b8d9-5197-4e3a-8abb-2d82ec78b8da`
`2026-04-30T04:15:44.989Z` · outcome=`call_abandoned` · sentiment=`negative` · CHS=`82` · duration=`145s`

**shape**: format=`json_list` · turns=21 · chars=6995 · est_tokens=409 · timestamps=False · tool_events=True
**roles**: assistant:12, user:6, tool:3
**audit**: _Carrier MC 367891 verified clean and was offered a matching Phoenix-to-Denver reefer at $2,100, but the call turned negative when the carrier pushed for a floor rate and then demanded someone who could honor an unsupported $1,000 claim. Agent stayed professional and did not disclose internal pricing logic, but the interaction ended without resolution after a tense rate dispute._
**death points:**
- No _hangup mentioned — call may have ended on carrier disconnect
- Possible floor/internal leak: pattern /\bfinal_floor\b/
- Possible floor/internal leak: pattern /\burgency_tier\b/

---

### Call `6fcf319a-b3ac-45ba-9eb9-70bc0931ec8b`
`2026-04-30T04:10:48.529Z` · outcome=`call_abandoned` · sentiment=`neutral` · CHS=`82` · duration=`93s`

**shape**: format=`json_list` · turns=18 · chars=5208 · est_tokens=305 · timestamps=False · tool_events=True
**roles**: assistant:11, user:6, tool:1
**audit**: _Carrier MC 1054287 verified as eligible, but the call never progressed to lane or equipment details because the carrier focused on fuel advance terms the agent could not provide. The agent stayed polite and offered a dispatch callback, but the interaction ended without load search or resolution, so minor deductions for incomplete engagement and flow._
**death points:**
- No _hangup mentioned — call may have ended on carrier disconnect

---

### Call `15df5c2f-6338-4edc-8cda-d00ea2887e0e`
`2026-04-30T04:09:08.333Z` · outcome=`no_match` · sentiment=`neutral` · CHS=`88` · duration=`141s`

**shape**: format=`json_list` · turns=27 · chars=7585 · est_tokens=378 · timestamps=False · tool_events=True
**roles**: assistant:15, user:9, tool:3
**audit**: _Carrier MC 632498 was verified as eligible, and the agent found one dry van option from Minneapolis to Chicago. The call ended without a deal after several unrealistic counters from the carrier; agent stayed polite and offered other options, with only minor flow deduction for a dragged-out negotiation._
**death points:**
- No _hangup mentioned — call may have ended on carrier disconnect
- Possible floor/internal leak: pattern /\bfinal_floor\b/
- Possible floor/internal leak: pattern /\burgency_tier\b/

---
