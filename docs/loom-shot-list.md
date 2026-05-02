# 5-min Loom shot list — Inbound Carrier Voice Agent demo

**Total runtime target:** 5:00 (4:30–5:15 acceptable)
**Format:** Loom desktop app, single take preferred, max 2 retries
**Voice:** conversational, not scripted; cursor visible; no apologies

---

## 0:00–0:30 — Opening + problem framing (~30s, ~75 spoken words)

**Screen:** title card OR first frame of HappyRobot workflow editor at full-screen.

**Say:**
> "Hi Carlos. I'm Andres — this is my Inbound Carrier Sales take-home. The brokerage problem I'm solving: carrier sales reps spend 60-80% of their day on FMCSA verification, lane matching, and rate negotiation. That's high-friction, low-leverage work. This voice agent handles first-touch — verifies, matches, negotiates within policy, books mid-call, transfers to a sales rep for paperwork. Built on HappyRobot, deployed on Fly. Let me show you."

---

## 0:30–2:00 — HappyRobot voice agent walkthrough (~90s, ~225 words)

**Screen:** HR workflow editor with `inbound-carrier-sales-new` workflow visible. Zoom out to show the full graph.

**Say:**
> "Here's the workflow. Voice Agent at the front, four tools under it — verify_carrier, query_loads, negotiate_rate, book_load. Then post-call: AI Extract, Case Health Score, and a Twin Write to calls_log."

**Click into the Prompt node.** Scroll the prompt body briefly. **Say:**
> "v4.3 prompt — FMCSA 7-check AND-gate, troubleshoot-first principle so we don't false-decline on bad ASR, decline scripts for each failure mode, anti-jailbreak rules. Three worked examples at the bottom."

**Click verify_carrier.** Show the FMCSA URL with the webKey.
> "verify_carrier hits FMCSA QCMobile directly — 7-check gate runs against the response."

**Click query_loads → Read-from-Twin child.** Show the filters.
> "query_loads has two modes — single-load lookup or lane search. Reads from the Twin loads table directly."

**Click negotiate_rate → Run Python child (`calculate_rate.py`).** Scroll to the tier urgency block.
> "The negotiation engine is in a Python sidecar — the LLM never sees the floor or the urgency math. Prompt injection can't extract them because they're not in context. Pickup within 6 hours drops the floor; over 24 hours the broker holds the line."

**Click book_load → Update Booking Record (Twin Write).**
> "book_load fires mid-call to the bookings table. UNIQUE constraint on call_id + load_id catches idempotency on retries."

**Pan post-call chain.**
> "Post-call: Extract emits the outcome enum, CHS scores the call and emits sentiment + audit remarks, then everything writes to calls_log."

**Mention briefly:** "28 languages enabled. Contact Intelligence on for repeat carriers."

---

## 2:00–3:30 — Live web call demo (~90s)

**Screen:** HR web call URL open in browser. Have the script ready.

**Say:**
> "Let me make a real call."

**Click the web-call URL → call connects.**

**Speak as carrier (in your normal voice):**
> "Hi, this is Mike from Express Trucking. MC two-five-oh-eight-one-nine. Looking for a load Dallas to Atlanta tomorrow, dry van."

**Agent responds:** verifies (you'll hear FMCSA hum), pitches a load with rate.

**Counter:** "What about $4,200?"

**Agent calls negotiate_rate, counters back** (somewhere between floor and ask).

**Accept:** "Yeah, deal at [agent's counter]."

**Agent calls book_load → success → recap → mock transfer:**
> "Locked in on [LOAD-XXXX], Dallas to Atlanta, [rate] — confirmed?"
> "Transferring you to our sales team to finalize the paperwork."
> "Transfer was successful and now you can wrap up the conversation."

**Hang up.**

> "That's the full flow — verify, search, pitch, negotiate, book mid-call, recap, sales-rep handoff."

---

## 3:30–4:30 — Dashboard tour (~60s, ~150 words)

**Screen:** open `https://robot-dashboard-andres-morones.fly.dev/dashboard` in a new tab.

**Say:**
> "Here's the call I just made — it's already in the dashboard."

**Click the Funnel tab.**
> "Funnel: total calls, FMCSA passed, loads pitched, booked. Conversion at every stage."

**Click Economics.**
> "Economics is the headline tab. Avg loadboard rate vs avg agreed rate side-by-side. The Effective Delta — green when we got below list, amber when we paid above. That's the one number a brokerage owner cares about."

**Hover the Effective Delta tooltip.** Show the formula.

**Click Operational.**
> "Avg call duration, FMCSA decline rate, abandon rate."

**Click Quality.**
> "Sentiment, outcome, CHS distribution buckets. Avg CHS, audit remark samples."

**Navigate to /dashboard/carriers.**
> "Per-carrier rollup — every MC we've talked to, conversion rate, avg agreed rate, last call timestamp."

**Click into MC 250819.**
> "Drilldown — full call history, sentiment + outcome breakdowns, every conversation logged."

---

## 4:30–5:00 — Architecture closing + roadmap (~30s, ~75 words)

**Screen:** README architecture diagram OR repo top-level on GitHub.

**Say:**
> "Stack: containerized FastAPI + Next.js 15 + shadcn + Recharts. Two Fly apps, HTTPS, Bearer auth on every endpoint. Twin Postgres native — no DB to provision."

> "Tier-2 roadmap: load-booked-status lifecycle, custom evals + adversarial suite activation, real-time call monitor, anti-fraud carrier verification, multi-broker tenancy."

> "Full broker doc with the full roadmap is in the repo. Thanks Carlos — looking forward to the next conversation."

---

## Production tips

- **Use Loom desktop app** (better quality than browser extension)
- **Keep cursor visible** — Loom has a setting for this
- **Single take preferred**; max 2 retries; if section 3 (live demo) goes badly, restart from 2:00 boundary
- **Don't apologize** for anything (even hiccups); just keep moving
- **Don't speak the script verbatim** — this is shot list + outline, not a teleprompter
- **If FMCSA timeout during the live call,** the agent's troubleshoot-first behavior kicks in (retry once with filler) — call that out as a feature, not a bug
- **End screen:** leave the carrier drilldown view up for ~3 seconds after your last word so the viewer can read it

## Pre-recording checklist

- [ ] HR workflow `inbound-carrier-sales-new` published to Production env (or Development if Production not set up)
- [ ] FastAPI deployed at robot-api-andres-morones.fly.dev (curl /healthz returns ok)
- [ ] Dashboard deployed at robot-dashboard-andres-morones.fly.dev (renders without 401)
- [ ] At least 3 fresh demo calls in calls_log (not the 8 stale test rows)
- [ ] LOAD-XXXX you'll book during demo is `available` status
- [ ] Mic + audio levels checked
- [ ] Browser tabs minimized to: HR workflow editor, web-call URL, dashboard

---

## Common failure modes during recording

- **Agent says "Transfer was successful and now you can wrap up the conversation" without recap** → v4.3 prompt fix wasn't pasted; redo Phase A1 Edit 2
- **Agent asks the same question 3+ times** → filler-vs-answer rule from v4.3 not landed; check the prompt body
- **Dashboard shows empty** → verify Bearer secret matches between API and Dashboard Fly apps
- **Twin SQL Cloudflare WAF block** → certain queries (info_schema, complex IN-lists) trigger blocks; the dashboard should not hit those — if it does, check the SQL in dashboard_aggregations.py
