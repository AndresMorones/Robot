# Dashboard Metric Catalog — Inbound Carrier Sales

Source of truth for the v2 dashboard build. Every metric below names an audience, a question, a formula, a surface, and a status. Metrics that don't earn their seat are listed in Section 6 with rationale.

Pairs with: `project_dashboard_v2_design_directives.md`, `project_dashboard_enterprise_framing.md`, `project_post_mvp_dashboard_metrics.md`, `data/twin_schema_calls_log.sql`, `docs/test-review-findings-2026-04-27.md`.

Rules in force:
- No latency metrics anywhere (per `project_post_mvp_remove_latency_metrics.md`).
- Friendly user-facing labels only — no schema column names in chart titles, axes, tooltips, alert chips, or drilldown headers.
- `call_outcome ∈ {load_booked, no_match, carrier_not_qualified, call_abandoned}`; `sentiment ∈ {positive, neutral, negative}` (Phase 3 enums locked).

---

## Section 0 — Reconciliation against shipping Pydantic shapes (post-v15 + Phase C)

The four `/v1/dashboard/*` endpoints now return the shapes below. This section is the canonical map from each catalog metric to the Pydantic field that surfaces it. Anything in Sections 3–7 that conflicts with this section loses — Section 0 is what's actually compiled into the API.

Pydantic models live in `api/app/models.py`; endpoints live in `api/app/routers/dashboard.py`; SQL helpers in `api/app/services/dashboard_aggregations.py`.

### `GET /v1/dashboard/funnel` → `FunnelMetrics`

| Field | Type | Catalog metric | Source |
|---|---|---|---|
| `total_calls` | `int` | M-001 Calls Today (window-filtered → "Total Calls") | `COUNT(*) FROM calls_log` |
| `by_outcome` | `dict[str, int]` | M-012 Outcome Mix | `GROUP BY call_outcome FROM calls_log`; falls back to `{load_booked, no_booking}` split when outcome enum is unpopulated |
| `booking_rate_pct` | `float` | M-011 Booking Rate | `(total - no_booking) / total * 100`, rounded to 2dp |

### `GET /v1/dashboard/economics` → `EconomicsMetrics`

| Field | Type | Catalog metric | Source |
|---|---|---|---|
| `total_calls_with_rate` | `int` | denominator for M-013/M-015 | `COUNT(*) FROM bookings` (i.e., booked rows) |
| `avg_loadboard_rate` | `float \| None` | M-014/M-072 reference rate | `AVG(loads.loadboard_rate)` over JOIN of `bookings → loads ON load_id` |
| `avg_agreed_rate` | `float \| None` | M-072 booked-rate KPI | `AVG(bookings.apply_rate)` |
| `effective_delta_dollars` | `float \| None` | M-013 Rate Lift (re-anchored) | `avg_agreed_rate − avg_loadboard_rate` (negative = broker upside) |
| `effective_delta_pct` | `float \| None` | M-015 Discount % (re-anchored) | `(avg_agreed − avg_loadboard) / avg_loadboard × 100` |
| `total_revenue_booked` | `float` | M-010 Revenue Booked | `SUM(bookings.apply_rate)` |

Reconciliation notes:
- The pre-v15 catalog assumed `pitched_loadboard_rate` and `agreed_rate` lived on `calls_log`. Post-ADR-005 they live on `bookings.apply_rate` (agreed) and `loads.loadboard_rate` (listed) and are joined server-side. M-013 Rate Lift and M-015 Discount % collapse into the single `effective_delta_*` pair.
- Three nullable fields (`avg_loadboard_rate`, `avg_agreed_rate`, the two delta fields) return `None` when there are zero bookings in the window. The dashboard renders "—" + caption "No bookings in window."
- M-072 Booked-Rate Scatter still requires per-row data; `/economics` only returns aggregates. The scatter is hydrated from `/v1/calls` (filtered to booked) for client-side plotting.

### `GET /v1/dashboard/operational` → `OperationalMetrics`

| Field | Type | Catalog metric | Source |
|---|---|---|---|
| `avg_duration_seconds` | `float \| None` | derived from M-071 Duration Distribution | `AVG(duration_seconds) FROM calls_log` |
| `fmcsa_decline_pct` | `float \| None` | M-060 Decline Rate | `COUNT(fmcsa_eligibility_failure_reason IS NOT NULL) / COUNT(*) × 100` |
| `abandon_rate_pct` | `float \| None` | M-073 Front-Door Drop Rate (broadened) | `COUNT(call_outcome='call_abandoned') / COUNT(*) × 100` |

Reconciliation notes:
- M-024 Negotiation Rounds Distribution is **dropped** from the operational endpoint per the v15 multi-load loop pivot — per-load detail moved to `bookings` and `num_negotiation_rounds` is no longer carried on `calls_log`.
- M-073 broadened to "abandon rate" (not gated on `duration_seconds < 30`); the original front-door-drop variant is now derivable client-side from `/v1/calls`.
- `avg_duration_seconds` replaces the M-071 histogram in the KPI tile; the histogram itself is plotted from row-mode `/v1/calls`.

### `GET /v1/dashboard/quality` → `QualityMetrics`

| Field | Type | Catalog metric | Source |
|---|---|---|---|
| `sentiment_distribution` | `dict[str, int]` | M-022 Sentiment Mix | `GROUP BY sentiment FROM calls_log` |
| `outcome_distribution` | `dict[str, int]` | M-012 Outcome Mix (mirrors funnel) | `GROUP BY call_outcome FROM calls_log` |
| `chs_distribution` | `dict[str, int]` | M-021 Call Quality Distribution | 5-bucket histogram of `case_health_score` (0-20, 20-40, 40-60, 60-80, 80-100) |
| `avg_case_health_score` | `float \| None` | M-020 Average Call Quality Score | `AVG(case_health_score) FROM calls_log` (string→float coerced) |
| `auditor_remarks_sample` | `list[str]` | M-025 Auditor Note Themes (sample) | `SELECT audit_remarks ORDER BY created_at DESC LIMIT 5` |

Reconciliation notes:
- M-023 Sentiment Inversion Rate is **deferred** — `sentiment_start` is no longer populated post-v15 cleanup (column dropped from the 12-col `CallRecord` model).
- M-025 surfaces a 5-row sample on the endpoint; full keyword clustering still runs in `dashboard_aggregations.audit_remarks_clusters()` and is exposed via the legacy `/v1/dashboard/observability` endpoint.

### Dropped from the v15 calls_log model (reflected in `CallRecord`)

`CallRecord` is now 12 columns: `id, call_id, mc_number, call_outcome, sentiment, case_health_score, audit_remarks, fmcsa_eligibility_failure_reason, callback_phone, duration_seconds, transcript, created_at`.

Removed since the catalog was first written:
- `pitched_loadboard_rate` / `agreed_rate` → moved to `bookings.apply_rate` + `loads.loadboard_rate` (joined server-side).
- `posted_price_increase` / `final_offer_position` / `num_negotiation_rounds` → derivable from `bookings` row sequence; not surfaced at MVP.
- `sentiment_start` / `sentiment_trajectory` → dropped (single `sentiment` column captures end-state).
- `carrier_name` → still selectable via `/v1/calls/{call_id}` JOIN; not on the dashboard endpoint contracts.

Catalog entries that referenced any of the above (M-013, M-014, M-015, M-023, M-024, M-032, M-050, M-051) keep their Phase 8/9 designation; they are intentionally NOT exposed on the four `/v1/dashboard/*` shapes today.

---

## Section 1 — Audience personas

Four personas drive the dashboard. Every metric in Section 3 cites at least one.

### P1 — Floor Lead (Maria, Sales Floor Supervisor)
- **Daily questions**: Is the agent up? What's going wrong right now? Which 3 calls do I need to listen to before lunch?
- **Cadence**: checks every 30-60 min during the shift; reacts to alert chips.
- **What she does when answers go bad**: pages the Engineer, manually pulls a transcript, opens an HR ticket, escalates a watchlist carrier to her director.

### P2 — Sales Director (Devon, VP Carrier Sales)
- **Daily questions**: How much revenue did the agent book this week vs last? Is booking rate trending up? Are we losing money in negotiation rounds?
- **Cadence**: morning coffee + Friday weekly report.
- **What he does when answers go bad**: requests prompt iteration, reallocates lanes, holds a Monday review with Maria.

### P3 — Workflow Engineer (Andres, Agent Owner)
- **Daily questions**: Did anything regress after my last prompt change? Are tools firing correctly? Which calls expose a prompt weakness?
- **Cadence**: pre-deploy + post-deploy checks; alert-driven during the day.
- **What he does when answers go bad**: forks a new HR version, edits the prompt, reruns adversarial suite, ships v(N+1).

### P4 — Carrier Relations (Priya, Carrier Account Manager)
- **Daily questions**: Which carriers called repeatedly? Who keeps getting declined by FMCSA? Who's a high-value repeat booker?
- **Cadence**: weekly carrier review + ad-hoc when a complaint arrives.
- **What she does when answers go bad**: calls the carrier, opens a watchlist case, flags the MC for human-only routing.

---

## Section 2 — Friendly label translation table

Mandatory translation. Use these exact strings in titles, axis labels, tooltips, alert chips, and table headers. **Never** show the left column to a user.

| Schema column | User-facing label |
|---|---|
| `mc_number` | Carrier ID |
| `carrier_name` | Carrier Name |
| `call_id` | Call ID |
| `created_at` | Call Time |
| `load_id` | Load Reference |
| `equipment_type` | Equipment |
| `pitched_loadboard_rate` | Listed Rate |
| `agreed_rate` | Agreed Rate |
| `posted_price_increase` | Rate Lift |
| `num_negotiation_rounds` | Negotiation Rounds |
| `call_outcome` | Outcome |
| `sentiment` | Final Sentiment |
| `sentiment_start` | Opening Sentiment |
| `sentiment_trajectory` | Sentiment Trend |
| `case_health_score` | Call Quality Score |
| `audit_remarks` | Auditor Notes |
| `final_offer_position` | Final Offer Position |
| `fmcsa_eligibility_failure_reason` | Decline Reason |
| `callback_phone` | Callback Number |
| `duration_seconds` | Call Duration |
| `transcript` | Transcript |
| `agent_version` (planned) | Agent Version |
| `lane` (derived: origin → destination) | Lane |
| `gap_pct` (derived) | Discount % |

Outcome enum display labels: `load_booked` → **Booked**, `no_match` → **No Match**, `carrier_not_qualified` → **FMCSA Decline**, `call_abandoned` → **Abandoned**.

Sentiment enum display labels: `positive` → **Positive**, `neutral` → **Neutral**, `negative` → **Negative**.

Decline reason enum (per `test-review-findings-2026-04-27.md` proposed lock): `INACTIVE` → **Inactive**, `NOT_AUTHORIZED` → **Not Authorized**, `NOT_FOUND` → **Not Found**, `OUT_OF_SERVICE` → **Out of Service**, `UNSAFE_RATING` → **Unsafe Rating**, `LIKELY_BROKER` → **Likely Broker**, `NOT_A_CARRIER` → **Not a Carrier**, `OTHER` → **Other**.

---

## Section 3 — Canonical metric catalog

29 metrics, grouped A–H. `Status` flags computability today; `Phase home` is 5.9 (build now), 8 (post-MVP polish), or 9 (deep enterprise).

### A. Operational health

```
ID: M-001
Friendly Name: Calls Today
Business Question: Is the agent picking up calls right now?
Audience: P1 Floor Lead, P2 Director
Formula: COUNT(*) WHERE created_at >= start_of_today_local
Source columns: created_at
Empty-state behavior: show "0" + caption "No calls yet today."
Alert threshold: if 0 calls between 09:00–17:00 local → alert "Inbound silent"
Surface placement: KPI strip tile #1
Status: computable-today
Phase home: 5.9
```

```
ID: M-002
Friendly Name: System Health Status
Business Question: Are any alert rules currently firing?
Audience: P1 Floor Lead, P3 Engineer
Formula: rollup of 7 alert rules from system_alerts(); status = max(severity of fired)
Source columns: derived (call_outcome, case_health_score, num_negotiation_rounds, sentiment_start, sentiment, fmcsa_eligibility_failure_reason, duration_seconds, audit_remarks)
Empty-state behavior: "Insufficient data — need 5+ recent calls" stoplight grey
Alert threshold: any "page" severity fires → red banner; "warn" → amber chip
Surface placement: System Health panel (sticky top-right) + KPI strip tile #2 stoplight
Status: computable-today
Phase home: 5.9
```

```
ID: M-003
Friendly Name: Inbound Volume Trend
Business Question: Is call volume up or down vs the trailing window?
Audience: P2 Director, P1 Floor Lead
Formula: bucketed COUNT(*) per day over selected window; compare to prior window of equal length
Source columns: created_at
Empty-state behavior: flat zero line + caption "No data in this window."
Alert threshold: none (informational)
Surface placement: trend chart (small line) below KPI strip
Status: computable-today
Phase home: 5.9
```

### B. Business impact

```
ID: M-010
Friendly Name: Revenue Booked
Business Question: How many dollars did the agent close in this window?
Audience: P2 Director
Formula: SUM(agreed_rate) WHERE call_outcome='load_booked' AND agreed_rate IS NOT NULL
Source columns: agreed_rate, call_outcome
Empty-state behavior: "$0" + caption "No bookings in window."
Alert threshold: window-over-window drop >40% → page (rolls into M-002)
Surface placement: KPI strip tile #3
Status: computable-today
Phase home: 5.9
```

```
ID: M-011
Friendly Name: Booking Rate
Business Question: What share of qualified calls turn into bookings?
Audience: P2 Director, P1 Floor Lead
Formula: COUNT(call_outcome='load_booked') / COUNT(*) * 100
Source columns: call_outcome
Empty-state behavior: "—%" with caption "Need 5+ calls."
Alert threshold: recent_window booking-rate drop >40% vs trailing → page (M-002)
Surface placement: KPI strip tile #4 + trend sparkline
Status: computable-today
Phase home: 5.9
```

```
ID: M-012
Friendly Name: Outcome Mix
Business Question: Where are calls leaking — no match, FMCSA, abandons?
Audience: P2 Director, P1 Floor Lead
Formula: COUNT(*) GROUP BY call_outcome (4 enum buckets, in fixed order)
Source columns: call_outcome
Empty-state behavior: empty bar with caption "No data."
Alert threshold: none
Surface placement: stacked horizontal bar (interactive: click bar → filter applied)
Status: computable-today
Phase home: 5.9
```

```
ID: M-013
Friendly Name: Rate Lift on Bookings
Business Question: Are we negotiating UP from listed rate, or eroding margin?
Audience: P2 Director, P3 Engineer
Formula: median(posted_price_increase) AND avg(posted_price_increase) WHERE call_outcome='load_booked'
Source columns: posted_price_increase, call_outcome
Empty-state behavior: "—" with caption "Field not yet populated by HR Auditor."
Alert threshold: median rate-lift trend < 0 over rolling 20 calls → warn (margin erosion)
Surface placement: small KPI inside Economics panel
Status: needs-binding-fix (column exists; HR Auditor not yet writing it on every row)
Phase home: 8
```

```
ID: M-014
Friendly Name: Top-Booking Lanes
Business Question: Which lanes are paying the bills?
Audience: P2 Director
Formula: GROUP BY (origin_state || ' → ' || destination_state) [from JOINed loads], COUNT(load_booked) DESC LIMIT 5
Source columns: load_id (FK to loads.origin_state + destination_state), call_outcome
Empty-state behavior: caption "Need bookings to rank lanes."
Alert threshold: none
Surface placement: top-5 list panel
Status: needs-new-column (lane derivation requires JOIN to loads or denormalized origin/destination_state on calls_log)
Phase home: 8
```

```
ID: M-015
Friendly Name: Discount % on Bookings
Business Question: How far below listed rate are we accepting?
Audience: P2 Director
Formula: median((pitched_loadboard_rate - agreed_rate) / pitched_loadboard_rate * 100) WHERE call_outcome='load_booked' AND both fields not null
Source columns: pitched_loadboard_rate, agreed_rate, call_outcome
Empty-state behavior: "—%" + caption "Listed Rate not yet captured — fix HR binding."
Alert threshold: median discount > 15% over rolling 20 → warn
Surface placement: Economics panel sub-tile
Status: needs-binding-fix (pitched_loadboard_rate=null on all 7 test rows; HR Workflow Dump binding broken — see test review)
Phase home: 5.8d (demo-blocking; if not fixed, hide tile entirely with "Listed Rate capture pending" caption)
```

### C. Agent quality

```
ID: M-020
Friendly Name: Average Call Quality Score
Business Question: How well is the agent doing on average?
Audience: P1 Floor Lead, P2 Director, P3 Engineer
Formula: avg(case_health_score) over filtered window
Source columns: case_health_score
Empty-state behavior: "—" + caption "Need 5+ scored calls."
Alert threshold: trailing-window avg drops ≥15 pts vs prior → warn (M-002)
Surface placement: Quality panel KPI tile
Status: computable-today (note: stored as string, must coerce — already handled in aggregations.py)
Phase home: 5.9
```

```
ID: M-021
Friendly Name: Call Quality Distribution
Business Question: Are scores clustering high, or is there a long low-score tail?
Audience: P1 Floor Lead, P3 Engineer
Formula: histogram of case_health_score in 5 buckets (0-20, 20-40, 40-60, 60-80, 80-100)
Source columns: case_health_score
Empty-state behavior: empty bars + caption "No scored calls in window."
Alert threshold: ≥30% of recent calls in 0-40 buckets → warn
Surface placement: Quality panel bar chart (interactive: click bucket → drilldown filtered to that range)
Status: computable-today
Phase home: 5.9
```

```
ID: M-022
Friendly Name: Sentiment Mix
Business Question: How do callers feel by the end of the call?
Audience: P1 Floor Lead, P2 Director
Formula: COUNT(*) GROUP BY sentiment (3 enum buckets)
Source columns: sentiment
Empty-state behavior: empty doughnut + caption "Sentiment data missing."
Alert threshold: negative share >25% recent vs trailing → warn
Surface placement: Quality panel doughnut (interactive: click segment → filter)
Status: computable-today (validate enum — current data has invalid "true" string)
Phase home: 5.9
```

```
ID: M-023
Friendly Name: Sentiment Inversion Rate
Business Question: How often do we start positive and end negative?
Audience: P1 Floor Lead, P3 Engineer
Formula: COUNT(sentiment_start='positive' AND sentiment='negative') / COUNT(both not null) * 100
Source columns: sentiment_start, sentiment
Empty-state behavior: "—%" + caption "Need both sentiment readings."
Alert threshold: >25% inversion → warn (M-002)
Surface placement: Quality panel small KPI + alert chip
Status: computable-today (column populated, but Auditor binding inconsistent — verify)
Phase home: 5.9
```

```
ID: M-024
Friendly Name: Negotiation Rounds Distribution
Business Question: Are we closing in one shot, or grinding through 3 rounds?
Audience: P3 Engineer, P2 Director
Formula: histogram of num_negotiation_rounds (0, 1, 2, 3+)
Source columns: num_negotiation_rounds
Empty-state behavior: caption "Negotiation tracking pending — see HR sidecar."
Alert threshold: ≥50% of recent calls at 3+ rounds → warn (negotiation_stuck rule, M-002)
Surface placement: Quality panel bar chart
Status: needs-binding-fix (num_negotiation_rounds=null on all 7 rows; negotiate_evaluate sidecar not yet shipped — post-MVP)
Phase home: 8
```

```
ID: M-025
Friendly Name: Auditor Note Themes
Business Question: What recurring issues do auditor notes flag?
Audience: P3 Engineer, P1 Floor Lead
Formula: keyword frequency over audit_remarks: {fmcsa, inactive, tool, fail, confus, hallucin, declined, unclear, abandoned}
Source columns: audit_remarks
Empty-state behavior: empty cluster + caption "No notes in window."
Alert threshold: ≥3 hits on alert keywords (tool|fail|confus|hallucin|inactive|fmcsa) in last 20 → warn (M-002)
Surface placement: Quality panel keyword cluster (chips, click → filter)
Status: computable-today
Phase home: 5.9
```

### D. Per-call review

```
ID: M-030
Friendly Name: Recent Calls Table
Business Question: Which call should I listen to next?
Audience: P1 Floor Lead, P3 Engineer, P4 Carrier Relations
Formula: SELECT * FROM calls_log ORDER BY created_at DESC LIMIT 25 (filtered by current filter bar)
Source columns: id, created_at, mc_number, carrier_name, call_outcome, sentiment, case_health_score, agreed_rate, duration_seconds
Empty-state behavior: empty rows + caption "No calls match current filters."
Alert threshold: none (table is the audit surface)
Surface placement: full-width sortable table; row click → drilldown panel
Status: computable-today
Phase home: 5.9
```

```
ID: M-031
Friendly Name: Call Drilldown
Business Question: What actually happened on this specific call?
Audience: P1 Floor Lead, P3 Engineer, P4 Carrier Relations
Formula: hydrate full row + parse transcript JSON → tabbed view (Summary | Transcript | FMCSA | Auditor)
Source columns: ALL columns of selected call_id
Empty-state behavior: blank canvas + "Select a call from the table."
Alert threshold: n/a
Surface placement: side panel or modal triggered by row click
Status: computable-today
Phase home: 5.9
```

```
ID: M-032
Friendly Name: Call Flag / Note (Ops Annotation)
Business Question: Has someone reviewed this call yet — and what did they say?
Audience: P1 Floor Lead
Formula: ops_annotations table (call_id, reviewer, status, note, created_at) — needs new persistence
Source columns: NEW TABLE
Empty-state behavior: "Unreviewed" badge + button "Mark reviewed"
Alert threshold: none
Surface placement: drilldown header chip + filter "Show only flagged"
Status: needs-new-instrumentation (Twin table + write endpoint)
Phase home: 8
```

### E. Carrier intelligence

```
ID: M-040
Friendly Name: Top Carriers by Call Volume
Business Question: Who's calling us repeatedly?
Audience: P4 Carrier Relations, P2 Director
Formula: GROUP BY mc_number, COUNT(*) DESC LIMIT 10 — include booked_count, booking_rate, avg quality, last_call_at
Source columns: mc_number, carrier_name, call_outcome, case_health_score, created_at
Empty-state behavior: empty list + caption "No repeat carriers yet."
Alert threshold: none
Surface placement: Carrier panel table (row click → filter dashboard to that MC)
Status: computable-today (note: skip rows with empty mc_number — already fixed in aggregations.py)
Phase home: 5.9
```

```
ID: M-041
Friendly Name: Repeat-Caller Rate
Business Question: How sticky is our carrier base?
Audience: P4 Carrier Relations
Formula: COUNT(DISTINCT mc_number with ≥2 calls) / COUNT(DISTINCT mc_number) * 100
Source columns: mc_number
Empty-state behavior: "—%" + caption "Need 10+ unique carriers."
Alert threshold: none
Surface placement: Carrier panel small KPI
Status: computable-today
Phase home: 5.9
```

```
ID: M-042
Friendly Name: Carrier Watchlist
Business Question: Who keeps getting declined or having bad calls?
Audience: P4 Carrier Relations
Formula: GROUP BY mc_number HAVING COUNT(call_outcome='carrier_not_qualified')>=2 OR avg(case_health_score)<50
Source columns: mc_number, call_outcome, case_health_score, fmcsa_eligibility_failure_reason
Empty-state behavior: caption "No watchlist matches yet."
Alert threshold: new entry → info chip
Surface placement: Carrier panel side list
Status: computable-today
Phase home: 8 (low MVP value at N=7; valuable at scale)
```

### F. Agent management

```
ID: M-050
Friendly Name: Agent Version In Use
Business Question: Which agent version handled these calls?
Audience: P3 Engineer, P2 Director
Formula: GROUP BY agent_version, show call_count + booking_rate + avg quality
Source columns: agent_version (NEW)
Empty-state behavior: single row "unknown" + caption "Version tagging pending."
Alert threshold: post-deploy: new version's booking-rate or avg-quality drops ≥10% vs prior → warn
Surface placement: Agent Mgmt panel small table
Status: needs-new-column (agent_version not in calls_log; needs HR workflow var bound at Write Twin)
Phase home: 8
```

```
ID: M-051
Friendly Name: Version A/B Comparison
Business Question: Did v(N+1) actually improve over v(N)?
Audience: P3 Engineer, P2 Director
Formula: side-by-side: booking_rate, avg quality, sentiment mix, avg duration, decline rate per version
Source columns: agent_version (NEW)
Empty-state behavior: "Need 2+ versions with 25+ calls each."
Alert threshold: significance-tested deltas → highlight green/red
Surface placement: Agent Mgmt panel
Status: needs-new-column (same as M-050)
Phase home: 9
```

### G. FMCSA / compliance

```
ID: M-060
Friendly Name: Decline Rate
Business Question: How often is FMCSA blocking us?
Audience: P1 Floor Lead, P3 Engineer
Formula: COUNT(fmcsa_eligibility_failure_reason IS NOT NULL) / COUNT(*) * 100
Source columns: fmcsa_eligibility_failure_reason
Empty-state behavior: "—%" + caption "No FMCSA data yet."
Alert threshold: >60% recent → page (M-002 fmcsa_failure_spike)
Surface placement: FMCSA panel KPI
Status: computable-today
Phase home: 5.9
```

```
ID: M-061
Friendly Name: Decline Reasons
Business Question: WHY are carriers being declined?
Audience: P3 Engineer, P4 Carrier Relations
Formula: COUNT(*) GROUP BY fmcsa_eligibility_failure_reason ORDER BY count DESC
Source columns: fmcsa_eligibility_failure_reason
Empty-state behavior: empty pie + caption "No declines in window."
Alert threshold: none (drilldown signal)
Surface placement: FMCSA panel pie/bar (interactive: click reason → filter)
Status: needs-enum-lock (currently free-text drift — "carrier inactive" vs "not authorized"; lock to 8-value enum per test review)
Phase home: 5.9 (uses normalized values where present; 8 for full enum lock + Classify Outcome refactor)
```

```
ID: M-062
Friendly Name: FMCSA AND-Gate Bypass Rate
Business Question: Did the agent book a load despite FMCSA decline? (regression check)
Audience: P3 Engineer
Formula: COUNT(call_outcome='load_booked' AND fmcsa_eligibility_failure_reason IS NOT NULL) / COUNT(call_outcome='load_booked') * 100
Source columns: call_outcome, fmcsa_eligibility_failure_reason
Empty-state behavior: "0% — clean" green
Alert threshold: ANY bypass → page (this is a known v13 bug from test review)
Surface placement: FMCSA panel red-line KPI + alert chip
Status: computable-today (critical: 2 of 7 test rows have this bypass)
Phase home: 5.9
```

### H. Operational patterns

```
ID: M-070
Friendly Name: Volume Heatmap (Hour × Day)
Business Question: When are carriers calling? When should we staff?
Audience: P1 Floor Lead, P2 Director
Formula: matrix [day_of_week (Mon-Sun)][hour 0-23] = COUNT(*)
Source columns: created_at
Empty-state behavior: all-grey grid + caption "Need 20+ calls for pattern."
Alert threshold: none
Surface placement: Patterns panel heatmap (cell click → filter to that hour-of-day)
Status: computable-today
Phase home: 5.9
```

```
ID: M-071
Friendly Name: Call Duration Distribution
Business Question: Are calls running too short (front-door drop) or too long (agent stuck)?
Audience: P1 Floor Lead, P3 Engineer
Formula: histogram of duration_seconds in 6 buckets: <30s, 30-60, 60-120, 120-240, 240-480, >480
Source columns: duration_seconds
Empty-state behavior: empty bars + caption "Need duration data."
Alert threshold: >20% of recent outside 15-480s window → info (duration_outlier_rate, M-002)
Surface placement: Patterns panel bar chart
Status: computable-today
Phase home: 5.9
```

```
ID: M-072
Friendly Name: Booked-Rate Scatter (replaces agreed-rate histogram)
Business Question: Is there a relationship between rate, quality, and outcome?
Audience: P3 Engineer, P2 Director
Formula: scatter (x=agreed_rate, y=case_health_score, color=sentiment, size=duration); only call_outcome='load_booked'
Source columns: agreed_rate, case_health_score, sentiment, duration_seconds, call_outcome
Empty-state behavior: empty plot + caption "No bookings in window."
Alert threshold: none (exploratory)
Surface placement: Economics panel — replaces M-013 placeholder if blocked
Status: computable-today (replaces broken low-N histogram)
Phase home: 5.9
```

```
ID: M-073
Friendly Name: Front-Door Drop Rate
Business Question: How often do callers hang up before MC capture?
Audience: P1 Floor Lead, P3 Engineer
Formula: COUNT(call_outcome='call_abandoned' AND duration_seconds<30) / COUNT(*) * 100
Source columns: call_outcome, duration_seconds
Empty-state behavior: "—%" + caption "Need 10+ calls."
Alert threshold: >10% → warn
Surface placement: Patterns panel small KPI
Status: computable-today
Phase home: 5.9
```

---

## Section 4 — Coverage matrix

Audience × surface. Each cell lists the metric IDs that surface there for that persona.

| Audience | KPI strip | System Health | Economics | Quality | Carriers | FMCSA | Patterns | Drilldown | Alerts |
|---|---|---|---|---|---|---|---|---|---|
| P1 Floor Lead | M-001, M-002, M-011 | M-002 | M-010, M-072 | M-020, M-021, M-022, M-025 | M-040 | M-060, M-062 | M-070, M-071, M-073 | M-030, M-031, M-032 | all of M-002 |
| P2 Director | M-001, M-010, M-011, M-012 | M-002 | M-010, M-013, M-014, M-015, M-072 | M-020, M-022 | M-040, M-041 | M-060 | M-070 | M-031 | M-002 booking_rate_cliff |
| P3 Engineer | M-002 | M-002 | M-013, M-072 | M-020, M-021, M-023, M-024, M-025 | M-042 | M-060, M-061, M-062 | M-071, M-073 | M-030, M-031 | all of M-002 |
| P4 Carrier Relations | — | — | — | — | M-040, M-041, M-042 | M-061 | — | M-031 | — |

Cells empty by design — Carrier Relations doesn't need KPI strip (has its own panel); a metric showing in zero cells should be cut.

---

## Section 5 — Schema gap report

Metrics blocked by missing/mis-bound columns. Effort = XS (≤30 min HR UI), S (≤2 hr HR + code), M (≤8 hr design + ship).

| Metric | Need | Source | Effort | Phase home |
|---|---|---|---|---|
| **M-015 Discount %** | `pitched_loadboard_rate` populated on every booked row | HR Workflow Dump binding fix — re-bind pitched rate to the loadboard_rate field of the load row passed to Write Twin | XS | **5.8d** (demo-blocking — Listed Rate empty kills the headline metric) |
| **M-013 Rate Lift** | `posted_price_increase` populated by Auditor on every row | HR Carrier Sales Auditor node — verify field is in extract schema and write-Twin column mapping | XS | 8 |
| **M-024 Negotiation Rounds Dist** | `num_negotiation_rounds` populated | Blocked on `negotiate_evaluate` Python sidecar (post-MVP). Until then, hide chart with caption "Negotiation tracking ships next release." | M | 8 |
| **M-014 Top Lanes** | `lane` derivable | Either denormalize `origin_state`, `destination_state`, `origin_city`, `destination_city` into calls_log (HR Workflow Dump binds from selected load), OR add API-side JOIN to loads.csv | S | 8 |
| **M-050 Agent Version** | `agent_version` column | New HR workflow variable bound at Write Twin (constant per workflow version, e.g. "v13", "v14") | XS | 8 |
| **M-032 Call Flags** | `ops_annotations` table + write endpoint | Twin DDL + `POST /v1/calls/{id}/annotate` API + write-back in dashboard | M | 8 |
| **M-061 Decline Reasons** | enum lock + Classify-Outcome enforcement | Lock to 8-value enum + Classify Outcome override rule (test-review §7) | S | 5.9 partial / 8 full |

Schema gap **anti-additions** (explicitly not adding): tool-call telemetry columns, p70 latency, assistant-cut-message-ratio, num_user_filler_messages — all in the post-MVP `project_post_mvp_field_design_research.md` backlog and not earning their seat at MVP.

---

## Section 6 — Anti-list (metrics deliberately NOT tracking)

| Metric | Why cut | Category |
|---|---|---|
| Latency p50/p90/p99 trend | Removed per `project_post_mvp_remove_latency_metrics.md` — orthogonal to HR-side LLM perf, not actionable on our side | Latency (banned) |
| Average call duration | Mean is meaningless at low N + skewed by 1 long call. M-071 distribution carries the real signal. | Collinear with M-071 |
| Avg agreed rate | A flat number that swings with lane mix; M-072 scatter + M-015 discount % are the actionable cuts. | Vanity / collinear |
| Total tool calls per call | Implementation artifact, not an ops decision lever. Belongs in engineering APM, not the ops dash. | Not actionable |
| Carrier phone number column in tables | PII; Carrier ID + Carrier Name are sufficient identifiers. Keep callback_phone in drilldown only. | Privacy-sensitive |
| Real-time active-call counter | At MVP volume there's never an active call; the placeholder would always read "0". | Noise at low N |
| Sentiment trajectory raw text | High variance free-text — signal is in inversion rate (M-023). | Noise |
| Audit remarks full-text wordcloud | Looks impressive, never drives an action; M-025 keyword cluster is the surgical cut. | Vanity |
| Carrier industry segment | Not in our schema and not derivable; FMCSA gives `legalName` only. | Not collectable |
| Floor coverage / agent capacity | We have one agent; not a meaningful metric until multi-version. | Not applicable at MVP |

---

## Section 7 — Phase 5.9 build manifest

Maps catalog metrics onto the 7 implementation steps in Agent B's Phase 5.9 spec.

| Step | What lands | Metric IDs | Notes |
|---|---|---|---|
| **Step 1 — Visual refresh** | Friendly labels everywhere; redact every schema name; drop "why this matters" subtitles; reduce palette to 5 colors | applies to ALL metrics on screen | Section 2 translation table is the contract; every chart title, axis, tooltip, table header must be re-checked |
| **Step 2 — Filter bar v2** | Preset chips (1d/1w/2w/1mo/6mo/1y/All) + outcome + sentiment + carrier search; HTML date inputs side-by-side for custom range | filterable: M-001, M-003, M-010, M-011, M-012, M-020, M-021, M-022, M-023, M-040, M-060, M-061, M-070, M-071, M-072, M-073, M-030 | All filters drive a single query-string-as-state model; server-rendered |
| **Step 3 — KPI strip + deltas** | 4 executive tiles, each with absolute value + arrow + delta % vs prior window | **M-001 Calls Today**, **M-011 Booking Rate**, **M-010 Revenue Booked**, **M-020 Avg Call Quality Score** (favorite) | Stoplight from M-002 sits adjacent as a system-health chip rather than 5th tile |
| **Step 4 — System Health (7 alerts)** | Alert chip rail from M-002 | rules: booking_rate_cliff (M-011), quality_drift (M-020), negotiation_stuck (M-024), sentiment_inversion (M-023), fmcsa_failure_spike (M-060), duration_outlier_rate (M-071), audit_keyword_cluster (M-025) | 7 rules already in `system_alerts()`; latency rule already removed |
| **Step 5 — Replace histogram** | Drop `agreed_rate_histogram` chart; replace with M-072 scatter; handle Listed Rate empty state explicitly | **M-072** booked-rate scatter; **M-015** Discount % tile gated on M-015 binding fix (gray-with-caption if blocked) | If M-015 binding lands by 5.8d, the tile shows a real %; else tile collapses |
| **Step 6 — Chart interactivity (intermediate scope)** | Click-to-filter on the highest-impact charts only | **M-012** Outcome Mix bar, **M-022** Sentiment doughnut, **M-040** Top Carriers row, **M-061** Decline Reasons | Defer click-to-filter on heatmap and quality histogram to Phase 8 |
| **Step 7 — Drilldown polish** | 4-tab panel inside M-031 Call Drilldown | Tabs: **Summary** (Carrier, Lane, Outcome, Quality, Agreed Rate, Discount %, Duration, Sentiment), **Transcript** (parsed roles, collapsible), **FMCSA** (legalName, status, decline reason if any), **Auditor** (notes + final_offer_position + sentiment_trajectory) | Drilldown is the human-audit surface; quality of this view is what makes Maria use the dash daily |

Out of 5.9 (deferred): M-013, M-014, M-024, M-032, M-042, M-050, M-051. M-062 stays in 5.9 as a small alert tile because the v13 FMCSA AND-gate bug is a known regression that must be visible.

---

## Section 8 — Open questions

Five design choices that need a decision before build:

1. **Which 4 metrics earn the executive KPI strip?** Recommended: **Calls Today (M-001), Booking Rate (M-011), Revenue Booked (M-010), Average Call Quality Score (M-020)**. Alternatives to consider: swap M-020 for **Decline Rate (M-060)** if compliance dominates Devon's Monday review.
2. **Quality Score rebrand.** Options: "Call Quality Score" / "Health Score" / "QA Score" / "Auditor Score". Recommended: **Call Quality Score** — most ops-natural; "Health Score" is too clinical, "QA Score" implies a separate QA team that doesn't exist.
3. **Carrier row click semantics in M-040.** Options: (a) filter dashboard to that MC, (b) open per-carrier drilldown panel, (c) navigate to `/dashboard/carrier/{mc}`. Recommended: **(a) filter** for 5.9 (one less surface to build); (b) post-MVP.
4. **Listed Rate empty UX.** Options: (a) hide the M-015 tile entirely until binding lands, (b) show grayed-out tile with caption "Listed Rate capture pending — fix in next agent version". Recommended: **(b)** — surfaces the data-quality gap to the Engineer who can fix it; honest about what's blocked.
5. **Calendar UX for custom range.** Options: (a) HTML5 `<input type=date>` side-by-side, (b) calendar popover (flatpickr or similar). Recommended: **(a)** for 5.9 (zero extra dependencies); upgrade to (b) only if a user complaint arrives.

====
**Catalog complete:** 29 metrics across 8 categories; 19 land in Phase 5.9, 9 deferred to Phase 8, 1 to Phase 9.
**Friendly-label table:** 23 schema columns mapped to user-facing strings; enum display labels locked for outcome, sentiment, decline reason.
**Schema gaps surfaced:** 7 blocked metrics — M-015 Discount % collapsed into `effective_delta_pct` post-v15; M-013 + M-015 now both anchor on the bookings ↔ loads join.
**Anti-list:** 10 explicit cuts spanning vanity, collinearity, privacy, latency, low-N noise.
**Phase 5.9 build manifest:** mapped onto Agent B's 7 steps; KPI strip locks to M-001/M-010/M-011/M-020.
**Reconciliation:** Section 0 maps every shipping `/v1/dashboard/*` Pydantic field to a catalog metric. Three nullable Economics fields stay null until bookings exist in the window. M-023 sentiment-inversion + M-024 negotiation-rounds explicitly dropped from MVP shapes.
**Open decisions:** 5 questions surfaced for user input before implementation begins.
====
