# Dashboard v2 — Metric Catalog (Research)

Research artifact for the Robot inbound carrier voice agent dashboard upgrade. Output of the "Freight ops data analyst" sub-agent (goliath stream #1). Companion docs: UX/IA tabs (`02-ux-ia.md`), Visualization spec, Engineering feasibility, Branding tokens.

---

## 1. Industry research summary

A production freight brokerage dashboard fights for screen real estate against tools the broker owner already trusts. The competitive bar:

**McLeod LoadMaster (and PowerBroker)** — dominant TMS in mid-market US brokerage. Their executive dashboard idiom: dense KPI strips across the top (loads booked today, gross margin %, available capacity, AR aging) with stacked operational drill-tables underneath. McLeod's Operations Dashboard emphasizes margin per load, driver/carrier utilization, and on-time pickup/delivery percentages, with green/amber/red traffic lights on every KPI vs target. Implicit framing: brokers care less about absolute counts than counts-vs-target and trend direction.

**DAT Power / DAT iQ** — the lane-rate data platform. DAT's analytics surface carrier-side gold: lane-by-lane spot-rate distributions (15th/50th/85th percentiles), broker-vs-spot rate spread, and capacity heatmaps showing tightness by origin region. Visual idiom: heavy choropleth/geo-heatmaps, shaded interquartile spread bands, and lane-pair tables ranked by rate volatility. Anyone familiar with DAT expects a dashboard to *show me the lanes*, not just totals.

**Truckstop Brokerage / Truckstop Load Board** — emphasizes funnel conversion (loads posted → views → calls → bookings) and broker-credit/score telemetry. Spreadsheet-dense, less infographic.

**DispatchTrack** — last-mile, but its UX patterns leak into freight: real-time status pills, rolling "active now" panels, ETA confidence bands. The "live operations" vibe (heartbeat tick, stale-data warning) is a DispatchTrack signature.

**Trimble TMS (TMW Suite, Engage Lane)** — broker dashboards lean into network-effect metrics: lane profitability ranking, contract-vs-spot mix, customer concentration, carrier-base health (active vs dormant). Visual: muted enterprise blue/grey, dense tables, sparklines inline in cells.

**Freightwaves SONAR** — index/forecast oriented. Popularized indices like OTRI (Outbound Tender Reject Index), TSTOPVRPM (rate-per-mile by lane), and the heatmap-of-the-US visual that brokers screenshot into their morning emails. Lesson: brokers respond to *named indices* with crisp definitions and a single number that summarizes a complex situation.

**Salesforce Service Cloud + Industry Cloud (Freight)** — call-center idiom: AHT (average handle time), first-call-resolution, CSAT, queue depth, agent occupancy. Heavy use of agent-leaderboard tables and time-of-day heatmaps for staffing.

**Synthesized patterns** any production freight dashboard must respect:
1. KPI strip on top with vs-target and vs-yesterday deltas, traffic-light coloring.
2. Geo / lane visualization — brokers expect to see flows.
3. Funnel view of the conversion path (posted → engaged → booked).
4. Time-of-day heatmaps for staffing and demand-pattern analysis.
5. Carrier-base health (active / repeat / dormant / churned).
6. Rate spread vs market reference (DAT-style band).
7. Named indices that compress complex situations into one number.
8. Color: muted enterprise palette (navy/slate/amber/forest), not SaaS gradients. Density over whitespace. Sparklines inline. Mono-spaced numerics.

The dashboard should *feel* like McLeod-meets-SONAR with a DispatchTrack-style live panel. That sets the visual idiom for the Visualization sub-agent.

---

## 2. Persona-tab mapping

Four personas, six proposed tabs. The split avoids one-tab-per-persona (which forces redundancy) — instead, each tab has a *primary* persona but is readable by the others.

| Tab | Primary persona | Secondary readers | Why it earns a tab |
|---|---|---|---|
| **1. Live Ops** | Dispatch lead | Broker owner | "What's happening right now" — active calls (HR Monitor API), last 5 calls rolling, today vs yesterday delta strip. The on-floor view. |
| **2. Bookings & Revenue** | Broker owner | Sales rep | The money tab. Bookings volume, revenue, effective rate delta, win-rate funnel, rate-spread band. Owner opens this first thing. |
| **3. Lanes & Loads** | Sales rep | Dispatch lead | Lane heatmap, equipment mix, load aging, stale-load alerts, lane profitability ranking. Sales rep hunts here for re-pricing targets. |
| **4. Carriers** | Sales rep | Broker owner | Top carriers by revenue, repeat-loyalty index, ghost-carrier count, FMCSA decline reasons, stale-carrier alerts. The CRM-shaped tab. |
| **5. Quality & Agent** | Broker owner | FDE | Sentiment trend, CHS distribution, audit-remarks clusters, call duration outliers, drop-off funnel, transcript review. Agent performance. |
| **6. System Health** | FDE | Broker owner | API latency, Twin freshness, webhook delivery, FMCSA error rate, cache hit ratio, deploy version. The "is anything broken" view. |

Justification:
- **Live Ops** is its own tab (not the top of every other tab) because heartbeat polling conflicts visually with deep historical analysis.
- **Bookings & Revenue** stays separate from **Lanes & Loads** because the broker owner asks "how much money did we make" *before* "where are the gaps" — different question, different decision speed.
- **Carriers** isolates MC-level identity so the other tabs ignore privacy/PII concerns.
- **Quality & Agent** consolidates everything that requires a transcript, so the FDE can drill there for prompt-tuning.
- **System Health** earns a tab even at MVP because brokers actively distrust black-box AI — visible plumbing builds trust.

Drilldown chain (locked answer #4): Tab → row in any table → detail page (call detail, carrier detail, lane detail, load detail). All deep-linkable so engineers can paste URLs in Slack.

---

## 3. Master metric catalog

Grouped by tab. Creativity legend: 1 = basic count, 2 = standard KPI, 3 = mid-creative analytical view, 4 = differentiated insight, 5 = novel/unexpected.

### Tab 1 — Live Ops

| # | Metric | Persona | Decision | Calculation | SQL feasibility | Time window | Creativity | Effort |
|---|---|---|---|---|---|---|---|---|
| 1.1 | **Active Calls Now** | Dispatch | "Do we have capacity? Should I jump in?" | HR Monitor API list of `call.in_progress` rooms, polled 10s, cached server-side. | Out of Twin — needs FastAPI proxy. | Live (≤10s) | 4 | Med |
| 1.2 | **Last 5 Calls Rolling** | Dispatch | "What just happened?" | `calls_log` rows by `created_at DESC` capped 5 (Python-side, since WAF blocks LIMIT). | Pull-and-slice. | Live | 2 | Low |
| 1.3 | **Today vs Yesterday Delta Strip** | Broker | "Are we ahead or behind?" | Group `bookings` and `calls_log` by date; render today + yesterday with %-delta and arrow. | Simple GROUP BY. | Today vs prior | 3 | Low |
| 1.4 | **Bookings Pacing Gauge** | Broker | "Are we on track for daily target?" | Compare bookings-so-far-today against expected-by-this-hour curve (derived from prior-week hourly distribution). | Python-side. | Today | 5 | Med |
| 1.5 | **Time-to-First-Word (silence latency)** | FDE | "Is the agent feeling laggy on pickup?" | Parse first agent utterance timestamp from transcript; histogram. | Python regex over transcript. | Live + week | 5 | High |
| 1.6 | **Call Volume Heartbeat (last 60min sparkline)** | Dispatch | "Is volume rising or falling right now?" | Bucket `calls_log` by minute over last hour. | Simple GROUP BY (minute trunc). | Live | 3 | Low |
| 1.7 | **Active-Call Sentiment Pulse** | Dispatch | "Is the call going badly? Should a human jump?" | If HR Monitor exposes mid-call sentiment → live tile. Else: defer to Tier-2. | Schema/HR change. | Live | 5 | High |

### Tab 2 — Bookings & Revenue

| # | Metric | Persona | Decision | Calculation | SQL feasibility | Time window | Creativity | Effort |
|---|---|---|---|---|---|---|---|---|
| 2.1 | **Total Bookings (window)** | Broker | "Did we hit target?" | COUNT(*) on `bookings` filtered by `created_at`. | Simple. | 1d / 1w / 1m / etc | 1 | Low |
| 2.2 | **Total Revenue (window)** | Broker | Same. | SUM(apply_rate) — WAF blocks aggregate; pull rows + Python-sum. | Pull + Python. | All windows | 1 | Low |
| 2.3 | **Average Apply Rate** | Broker | "Are we under-pricing?" | mean(apply_rate). | Python-side. | All windows | 2 | Low |
| 2.4 | **Effective Rate Delta over Time** | Broker | "Are we losing margin to negotiation drift?" | For each booking, `apply_rate - loadboard_rate` joined `bookings.load_id = loads.load_id`. Time-series of daily mean delta. | Two pulls + Python join. | Week / month / 6mo | 5 | Med |
| 2.5 | **Booking Rate (calls→bookings)** | Broker | "Is the funnel converting?" | bookings.count / calls_log.count over same window. | Two simple counts. | All windows | 2 | Low |
| 2.6 | **First-Call Booking Rate (new MCs)** | Sales rep | "Are we closing first-time carriers?" | Of MCs whose first `calls_log` row is in window, fraction with a tied `bookings` row. | Python join. | Week / month | 4 | Med |
| 2.7 | **Booking Velocity (call.start → booking)** | FDE | "How fast does the agent close?" | bookings.created_at − calls_log.created_at; histogram. | Python join. | Week | 4 | Med |
| 2.8 | **Rate Spread Distribution Histogram** | Broker | "Where do most bookings land vs loadboard?" | Bin (apply_rate − loadboard_rate) into 25-bucket histogram. | Python-side. | Week / month | 4 | Low |
| 2.9 | **Concession Curve by Round** | Broker | "How much do we give up per round?" | If `negotiation_rounds` captured (NOT in current schema) — flag schema change. Else proxy: order bookings within a call. | Schema change flagged. | Week | 5 | High |
| 2.10 | **Lost Opportunity Estimate** | Broker | "What did we leave on the table?" | (calls without booking).count × median apply_rate over same lane × estimated pickup margin. | Python-side. | Week / month | 5 | Med |
| 2.11 | **Multi-Load-per-Call Win Rate** | Sales rep | "Are we cross-selling?" | Calls with bookings.count > 1 / calls with ≥1 booking. | Python group-by call_id. | Week / month | 5 | Low |
| 2.12 | **Revenue per Call (RPC)** | Broker | "Yield per touchpoint" | total_revenue / total_calls. | Python-side. | All windows | 3 | Low |
| 2.13 | **Booking Heatmap (hour × weekday)** | Dispatch | "When do bookings actually happen?" | Bucket by HOUR(created_at) × DOW. | GROUP BY date_trunc OK. | Month / 12wk | 4 | Med |
| 2.14 | **Bookings vs Target line + band** | Broker | "Are we trending toward goal?" | Daily bookings vs configured daily target with rolling 7-day band. | Python-side. | Month / 6mo | 3 | Low |

### Tab 3 — Lanes & Loads

| # | Metric | Persona | Decision | Calculation | SQL feasibility | Time window | Creativity | Effort |
|---|---|---|---|---|---|---|---|---|
| 3.1 | **Lane Heatmap (origin → dest geo flow)** | Sales rep | "Where is volume concentrated?" | Aggregate bookings.count by (origin_state, dest_state) joined via loads. Choropleth or arc map. | Pull joined rows + Python aggregate. | Month / 12wk | 5 | High |
| 3.2 | **Top 20 Lanes by Revenue** | Sales rep | "Which lanes are paying the bills?" | SUM(apply_rate) by (origin_city, dest_city) joined. | Python-side. | Week / month | 4 | Low |
| 3.3 | **Lane Profitability Ranking (vs loadboard baseline)** | Broker | "Which lanes have the best margin spread?" | mean(apply_rate − loadboard_rate) per lane, sorted. | Python-side. | Month | 5 | Med |
| 3.4 | **Equipment Mix Snapshot** | Sales rep | "What equipment dominates demand?" | Bookings by `loads.equipment_type` GROUP BY. | Simple GROUP BY. | All windows | 2 | Low |
| 3.5 | **Equipment Mix Shift over time** | Sales rep | "Is reefer share rising?" | Stacked-area chart of equipment mix by week. | Python-side. | 12wk / 6mo | 4 | Med |
| 3.6 | **Reefer-vs-Dry-Van Conversion Differential** | Sales rep | "Which equipment converts better?" | booking_rate split by equipment_type. | Python-side. | Month | 5 | Low |
| 3.7 | **Stale Load Alert** | Sales rep | "Which loads need re-pricing?" | Loads with posted_at > 48h and no booking. Highlighted table. | Pull all + Python filter. | Live / today | 4 | Low |
| 3.8 | **Load Aging Histogram** | Sales rep | "Are we sitting on inventory?" | Bin (now − posted_at) by hour for unbooked loads. | Python-side. | Live | 3 | Low |
| 3.9 | **Lane Rate Volatility** | Broker | "Where are we fighting carriers hardest?" | StdDev(apply_rate) per lane over month. | Python-side. | Month / 6mo | 5 | Med |
| 3.10 | **Pickup Window Pressure** | Dispatch | "Which loads are close to pickup with no carrier?" | Unbooked loads where `pickup_datetime − now < 24h`. | Pull + Python filter. | Live | 4 | Low |
| 3.11 | **Commodity Mix Treemap** | Sales rep | "What commodities drive volume?" | Bookings GROUP BY commodity_type (joined). | Simple. | Month | 3 | Low |
| 3.12 | **Lane Demand Index (calls per lane / bookings per lane)** | Broker | "Where's interest without conversion?" | calls referencing a lane / bookings on that lane. | Python-side. | Month | 5 | High |

### Tab 4 — Carriers

| # | Metric | Persona | Decision | Calculation | SQL feasibility | Time window | Creativity | Effort |
|---|---|---|---|---|---|---|---|---|
| 4.1 | **Top 10 Most Valuable Carriers** | Broker | "Who do we owe a thank-you call?" | SUM(apply_rate) by mc_number joined call → booking. | Python-side. | Month / 6mo / 1y | 4 | Low |
| 4.2 | **Repeat Carrier Loyalty Index** | Sales rep | "Who's coming back?" | Count distinct call dates per MC ÷ window-days; bucket bronze/silver/gold. | Python-side. | Month / 6mo | 5 | Med |
| 4.3 | **Ghost Carrier Index** | Broker | "How leaky is the top of funnel?" | MCs with ≥1 call but 0 bookings ever / total distinct MCs. | Python-side. | All windows | 5 | Low |
| 4.4 | **Stale Carrier Alert** | Sales rep | "Who's gone quiet?" | Repeat-carrier MCs (≥3 prior calls) whose last call > 21d ago. | Python-side. | 6mo lookback | 5 | Med |
| 4.5 | **FMCSA Decline Rate** | Broker | "How clean is our inbound?" | calls_log.count where fmcsa_eligibility_failure_reason IS NOT NULL ÷ total. | Simple. | All windows | 2 | Low |
| 4.6 | **FMCSA Decline Reason Breakdown** | Broker | "Why are we declining?" | GROUP BY fmcsa_eligibility_failure_reason. | Simple GROUP BY. | Week / month | 3 | Low |
| 4.7 | **New vs Returning MC mix** | Sales rep | "Are we building a base?" | First-call vs repeat MC counts per day. | Python-side. | Month / 6mo | 3 | Low |
| 4.8 | **Carrier Concentration Risk (Herfindahl)** | Broker | "Are we over-reliant on one MC?" | Σ(carrier_revenue / total_revenue)² → HHI score. | Python-side. | Month / 6mo | 5 | Low |
| 4.9 | **Carrier Sentiment Average** | Broker | "Who's annoyed when they call us?" | mean(sentiment_numeric) per MC. | Python-side. | 6mo | 4 | Low |
| 4.10 | **Carrier Lifetime Value (CLV)** | Broker | "What's an MC worth long-term?" | SUM(apply_rate) per MC over 6mo. | Python-side. | 6mo / 1y | 4 | Low |

### Tab 5 — Quality & Agent

| # | Metric | Persona | Decision | Calculation | SQL feasibility | Time window | Creativity | Effort |
|---|---|---|---|---|---|---|---|---|
| 5.1 | **Sentiment Distribution** | Broker | "Are calls trending angry?" | GROUP BY sentiment over window. | Simple. | Week / month | 2 | Low |
| 5.2 | **Sentiment Over Time (line)** | Broker | "Is quality decaying?" | Daily sentiment_numeric mean. | Python-side. | Month / 6mo | 3 | Low |
| 5.3 | **CHS Distribution Histogram** | FDE | "Where do scores cluster?" | Bin case_health_score by 10. | Python-side. | Week / month | 3 | Low |
| 5.4 | **CHS Decay Trend (week-over-week)** | FDE | "Is the agent regressing?" | Mean CHS by week; alert on -10pt drop. | Python-side. | 12wk / 6mo | 5 | Med |
| 5.5 | **Audit Remarks Cluster Analysis** | FDE | "What categories of issues recur?" | Tokenize audit_remarks; regex bucket: pricing / fmcsa / availability / objection / fraud / other. | Python-side. | Month | 5 | Med |
| 5.6 | **Call Duration Distribution** | FDE | "Is the agent rambling?" | Histogram of duration_seconds. | Python-side. | Week / month | 2 | Low |
| 5.7 | **Call Duration Outliers (top/bottom 5%)** | FDE | "Pull these for transcript review." | Filter top 5% / bottom 5% by duration. | Python-side. | Week | 4 | Low |
| 5.8 | **Drop-off Funnel** | Broker | "Where do calls die?" | Stages: calls_started → fmcsa_passed → load_pitched → negotiation_engaged → booked. From call_outcome enum + booking presence. | Python-side. | Week / month | 5 | Med |
| 5.9 | **Sentiment-Outcome Correlation** | FDE | "Does positive sentiment actually predict booking?" | 2×3 contingency: sentiment(neg/neu/pos) × outcome(booked/not). Lift / chi-sq. | Python-side. | Month | 5 | Med |
| 5.10 | **First-Pass FMCSA Pass Rate** | Broker | "Inbound quality score" | calls where outcome NOT 'fmcsa_decline' ÷ total. | Simple. | All windows | 2 | Low |
| 5.11 | **Outcome Mix (call_outcome donut)** | Dispatch | "What's the call mix?" | GROUP BY call_outcome. | Simple. | Week | 2 | Low |
| 5.12 | **Friday-Afternoon Drag (weekly cyclicality)** | Broker | "Are weekends worth staffing?" | Booking rate by DOW × hour bucket; flag low-points. | Python-side. | 12wk | 4 | Med |
| 5.13 | **Transcript Review Queue (low CHS sample)** | FDE | "What needs human review?" | Calls where CHS < 70, paged + searchable. | Pull + Python filter. | Week / month | 4 | Low |
| 5.14 | **Negotiation Length Distribution** | FDE | "Is negotiation collapsing or dragging?" | Count rounds per call (regex over transcript or dedicated field — schema flag). | Python regex; or schema change. | Month | 4 | Med |

### Tab 6 — System Health

| # | Metric | Persona | Decision | Calculation | SQL feasibility | Time window | Creativity | Effort |
|---|---|---|---|---|---|---|---|---|
| 6.1 | **API p50 / p95 Latency** | FDE | "Is the dashboard slow?" | Prom histogram (already wired). | Outside Twin. | Live | 2 | Low |
| 6.2 | **Twin Query Time** | FDE | "Is Twin lagging?" | Wrap each Twin call in span; expose timing. | Outside Twin. | Live | 3 | Low |
| 6.3 | **Cache Hit Ratio** | FDE | "Is caching helping?" | TTLCache hits / (hits+misses). | Outside Twin. | Live | 3 | Low |
| 6.4 | **Webhook Delivery Lag** | FDE | "How stale is data?" | now − max(calls_log.created_at). | Python-side. | Live | 3 | Low |
| 6.5 | **HR Workflow Version + Deploy SHA** | FDE | "What's running in prod?" | Static read of fly env + HR workflow version label. | Outside Twin. | Live | 2 | Low |
| 6.6 | **Twin Row Counts (calls_log / bookings / loads)** | FDE | "Is data flowing?" | COUNT each table. Single-aggregate is OK per WAF. | Simple. | Live | 1 | Low |
| 6.7 | **Active-Call HR Monitor Reachability** | FDE | "Is HR Monitor up?" | Last successful Monitor poll timestamp + ok/error pill. | Outside Twin. | Live | 3 | Low |
| 6.8 | **Empty-State / Null-Field Anomaly Counter** | FDE | "Are extracts coming back blank?" | Daily count of calls where audit_remarks IS NULL / sentiment IS NULL / mc_number IS NULL. | Simple GROUP BY. | Day / week | 4 | Low |

**Cross-tab catalog total: 65 metrics**

---

## 4. Top 10 ranked recommendations (MVP shortlist)

Ranked by *production demo impact × implementation cost*.

1. **Effective Rate Delta over Time (2.4)** — directly satisfies user requirement #7, joins the two big tables, creativity 5, demonstrably the *agent-is-saving-margin* story for the broker.
2. **Drop-off Funnel (5.8)** — visualizes the entire pipeline in one chart; the single most legible "is this agent working" view.
3. **Lane Heatmap (3.1)** — every freight broker expects a geo flow chart; not having one signals "non-freight" tooling. SONAR/DAT shorthand.
4. **Bookings vs Target (2.14)** — pacing and target awareness is the broker-owner morning ritual.
5. **Top 10 Most Valuable Carriers (4.1)** — drives the next-week sales-call list, immediately actionable.
6. **CHS Decay Trend (5.4)** — shows the agent's quality holding (or not) over time; differentiates Robot from any "we just deployed an LLM" demo.
7. **Active Calls Now + Last 5 Rolling (1.1 + 1.2)** — the live-ops heartbeat; satisfies user requirement #6c (HR Monitor active-call detection).
8. **Sentiment-Outcome Correlation (5.9)** — surprises the customer in a demo; proves we *measured* whether sentiment predicts revenue, not just charted it.
9. **Audit Remarks Cluster Analysis (5.5)** — turns the free-text remark column into a strategic categorical KPI; nobody else surfaces this.
10. **Lost Opportunity Estimate (2.10)** — gives the broker owner a dollar number for the gap; converts negative space (calls that didn't book) into a story.

These 10 collectively touch all 6 tabs except System Health (which earns a tab regardless because trust). Creativity scores: 5,5,5,3,4,5,4+2,5,5,5 — average 4.4. Mostly Low-Med effort.

---

## 5. Anti-recommendations

Metrics to deliberately NOT show, even though they look attractive:

- **Total Calls (raw COUNT alone)** — vanity. Inbound volume is set by HR/marketing, not by us. Show only as the funnel-top denominator, never headlined.
- **Average Sentiment Score (single number)** — collapses too much; sentiment is bimodal in real call traffic, the average is meaningless. Show the distribution.
- **Conversion Rate without time window** — gameable by re-defining "conversion." Always tie to a date window with comparison.
- **Number of Tools Called** — engineering metric, not operational; belongs in logs not dashboard.
- **Carrier Score / Quality Tiers we invent** — without a feedback loop these become circular ("the carrier scored well because we said so"). Defer until at least 200 bookings of ground truth.
- **AI Confidence / Probability of Success** — opaque, not actionable, triggers prompt-engineering pushback in demos.
- **Revenue Forecasts** — single-broker MVP can't fit a forecast model honestly; placeholder forecasts erode trust faster than no forecast.
- **Per-Agent Leaderboards** — we have ONE agent; ranking it against itself is theater.
- **Live Geo Map of Trucks** — we don't have GPS data; faking it (with origin lat/long only) is misleading.
- **Aggregate Cost-per-Call $** — without a true LLM cost feed, any number we put up is fictional. Defer to System Health once Prom metrics include token counts.

Principle: every shipped metric should change a decision the persona actually makes this week. If it doesn't, kill it.

---

## Final summary

- **Total candidate metrics**: 65
- **Distribution by creativity score**: 1 → 3, 2 → 11, 3 → 14, 4 → 16, 5 → 21
- **Top 5 must-ship MVP**: Effective Rate Delta over Time (2.4), Drop-off Funnel (5.8), Lane Heatmap (3.1), Active Calls Now + Last 5 Rolling (1.1 + 1.2), Top 10 Most Valuable Carriers (4.1)
- **Top 5 Tier-2**: Sentiment-Outcome Correlation (5.9), Audit Remarks Cluster Analysis (5.5), CHS Decay Trend (5.4), Lost Opportunity Estimate (2.10), Carrier Concentration Herfindahl (4.8)
- **Schema-change flags**: `calls_log.first_word_at_seconds`, `calls_log.negotiation_rounds`, `bookings.sequence_in_call`, `loads.status` + `loads.booked_at` (last already deferred memory)
- **HR-workflow-change flags**: Monitor mid-call sentiment exposure, `first_speech_offset_ms` in extract, negotiation rounds counter sidecar
- **Out-of-Twin dependencies**: HR Monitor API (active calls), Prom + structlog (System Health tab)
