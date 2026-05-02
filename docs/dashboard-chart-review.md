# Dashboard Chart Review (read-only audit)

> Multi-agent-style review of every chart, KPI card, and table currently in the deployed Next.js dashboard at `dashboard/src/`. Anchors back to the FDE spec at `docs/FDE-TECHNICAL-CHALLENGE.md`. Stack constraints from ADR-006 / ADR-011 are respected — every recommendation stays inside Recharts + Radix-shadcn + Tailwind 4 + lucide and avoids re-introducing the five libraries cut by ADR-011 (`nuqs`, `@tremor/react`, `react-day-picker`, `date-fns`, `@radix-ui/react-popover`).
>
> Per memory note `project_dashboard_goliath_three_new_tabs.md` this is the "review every chart's design" deliverable — Tier-2 / deferred. Every recommendation is stated as a delta, not a rewrite.
>
> Effort key: **S** ≤ 30 min, **M** ≤ 2 hr, **L** ≥ half day.

---

## 0. Tab inventory

| Tab | Route | File |
|---|---|---|
| Overview ("Pulse") | `/dashboard` | `dashboard/src/app/dashboard/page.tsx` |
| Calls | `/dashboard/calls` | `dashboard/src/app/dashboard/calls/page.tsx` |
| Call detail | `/dashboard/calls/[call_id]` | `dashboard/src/app/dashboard/calls/[call_id]/page.tsx` |
| Carrier detail (drill-through only) | `/dashboard/carriers/[mc]` | `dashboard/src/app/dashboard/carriers/[mc]/page.tsx` |
| New Bookings | `/dashboard/sales` | `dashboard/src/app/dashboard/sales/page.tsx` |

Header nav (`dashboard/src/components/header.tsx`) exposes only **Overview · Calls · New Bookings**. There is no carriers list/index page; `[mc]` is reachable only by clicking an MC link in a table or card. See finding T-3 below.

---

## Overview tab — 6 spark KPI cards + hero chart + 4-tab subnav

File: `dashboard/src/app/dashboard/page.tsx`

### KPI strip (6 cards above the hero)

The strip composes `<KpiCard>` (`dashboard/src/components/kpi-card.tsx`) — Card chrome + 3xl tabular-nums value + optional `<DeltaPill>` (TrendingUp/TrendingDown/Minus icon + signed pct) + optional Recharts `<AreaChart>` sparkline.

#### KPI #1 — "Calls"
1. **Tab/file:** Overview · `page.tsx:65–71` via `KpiCard`.
2. **Currently shows:** `funnel.total_calls` count, vs-prior delta pill, daily sparkline. Source: `GET /v1/dashboard/funnel` (`api/app/routers/dashboard.py::funnel`, sparkline from `dashboard_aggregations.calls_sparkline`).
3. **GOOD:** Number is the right scale (3xl, tabular-nums); spark trend + delta pill together give a one-glance read; cheap aggregate.
4. **UX-WEAK:** Delta-pill thresholds (`>5` up, `<-5` down, else flat) aren't explained in tooltip; user can't tell if the comparison window is "previous 7 days" or "year-over-year". Sparkline has no axis labels, no hover tooltip, no x-domain hint.
5. **INFORMATION-WEAK:** "Calls" is a vanity metric without a denominator (capacity, per-rep, per-region). Counts that move 5–10 % within a 7-day window are noise.
6. **Improve:** add a subtitle line under the value reading "vs prior 7d" (or whatever window matched the filter) and a Recharts `<Tooltip>` on the spark with the date + count. **S**.
7. **Effort:** S.

#### KPI #2 — "Bookings"
1. Overview · `page.tsx:72–76`.
2. `economics.total_calls_with_rate` — count of bookings with a rate. No delta, no spark (despite the prop being available — `economics.sparkline` exists).
3. **GOOD:** Direct revenue-proxy KPI, plain integer, easy to scan.
4. **UX-WEAK:** Sparkline + delta omitted while the 4 surrounding cards have them. Visual asymmetry that reads as "data missing" even when it isn't.
5. **INFORMATION-WEAK:** Same as Calls — bookings without context (target, prior period, capacity) is decoration.
6. **Improve:** wire `deltaPct={economics.delta_pct_vs_prior}` and `sparkline={economics.sparkline}` (the API already returns them — see `dashboard.py:299–300`). **S**.
7. S.

#### KPI #3 — "Booked rate"
1. Overview · `page.tsx:77–81`.
2. `funnel.booking_rate_pct` — bookings / total_calls. Source: `funnel`.
3. **GOOD:** This is the headline conversion KPI a broker actually cares about (ties to spec Objective 1: "negotiate pricing automatically"). Honest decimal.
4. **UX-WEAK:** No delta pill, no spark, no benchmark line. "37 %" alone tells reviewer nothing about whether that's good.
5. **INFORMATION-WEAK:** This is the metric most worth context. Without a target band ("industry baseline 12–18 %") or a prior-period delta, it's unanchored.
6. **Improve:** add `deltaPct` from a `funnel.booking_rate_delta_pct_vs_prior` field (new `dashboard_aggregations` helper modelled after `_safe_pct_change`); render a target band on the spark via Recharts `<ReferenceLine>` once a target is chosen. **M** (because it requires a new aggregation + endpoint field).
7. M.

#### KPI #4 — "Listed rate avg"
1. Overview · `page.tsx:82–86`.
2. `economics.avg_loadboard_rate` — mean of `loads.loadboard_rate` for booked loads. Source: `economics`.
3. **GOOD:** Currency-formatted; pairs visually with KPI #5 (booked-rate avg) for a side-by-side read.
4. **UX-WEAK:** No delta, no spark. Without #5 right next to it, the value is meaningless.
5. **INFORMATION-WEAK:** Mean is fragile to a few outlier high-rate loads. p50 (median) is more robust for broker-ops storytelling.
6. **Improve:** add `(median)` chip below the value sourced from a new `dashboard_aggregations.median_loadboard_rate()` query. **M**.
7. M.

#### KPI #5 — "Booked rate avg"
1. Overview · `page.tsx:87–93`.
2. `economics.avg_agreed_rate` (= `bookings.apply_rate` mean) + delta + spark.
3. **GOOD:** This is the headline economics number; spark + delta lit up; amber accent matches the dark-ops palette.
4. **UX-WEAK:** Card-to-card contrast vs Listed-rate-avg is minimal; the broker has to look closely to see they're paired.
5. **INFORMATION-WEAK:** Without a per-card sub-label "vs Listed −$83 (3.2 %)" the spec's headline ("captured margin") is buried in the *next* tab.
6. **Improve:** show the live margin delta inline as a sub-line under the value (e.g., "−$83 vs list, 3.2 %"). The hero `<EffectiveDeltaChart>` already shows this over time; surfacing the scalar on the KPI card makes the strip self-contained. **S**.
7. S.

#### KPI #6 — "Quality score"
1. Overview · `page.tsx:94–104`.
2. `quality.avg_case_health_score` — mean of `calls_log.case_health_score`. Delta + violet spark.
3. **GOOD:** Single bounded scalar (0–100); violet accent differentiates it from money-coloured cards.
4. **UX-WEAK:** "Quality score" without a unit or pass/fail threshold reads as opaque; reviewer doesn't know 58 is failing and 70 is passing (per CHS deduction model).
5. **INFORMATION-WEAK:** Score by itself doesn't tell the reviewer *why* it's low. The Quality tab solves this with the sample-flags list, but the KPI card pretends it doesn't exist.
6. **Improve:** append "/100, ≥70 passing" as the `hint` prop; colour the value text red below 70. **S**.
7. S.

#### KPI strip — overall
- **Layout grid:** 2 cols / 6 cols at `lg`. At `md` (between sm and lg) it's still 2-wide which forces a 3-row tall stack — no breakpoint covers tablet width gracefully.
- **Asymmetric data wiring:** 3 of 6 cards have spark + delta, 3 don't. This is a polish gap, not an architecture gap (the API returns the data — see KPI #2).
- **Improve top-strip overall:** unify all 6 with delta + spark; add a `lg:grid-cols-3 xl:grid-cols-6` breakpoint to fix tablet. **S** wiring + **S** layout.

---

### Hero — "Margin captured (avg per booking)"
File: `dashboard/src/components/effective-delta-chart.tsx`
Endpoint: `GET /v1/dashboard/effective-delta` (`dashboard_aggregations.effective_delta_series`)

1. **Tab/file:** Overview hero, between strip and tabs · `page.tsx:110`, component `effective-delta-chart.tsx`.
2. **Shows:** Recharts `<ComposedChart>` — `<Area>` underlay (12 % opacity) + `<Line>` on top of daily mean of `(apply_rate − loadboard_rate)`. Parity reference line at y = 0. Tooltip shows formatted day + dollars + booking count for that day.
3. **GOOD:** This is the single best chart on the dashboard. Sign convention is principled (negative = below list = margin captured). `connectNulls={false}` is correct — no false continuity over silent days. Parity reference line is high-leverage. Tooltip surfaces the underlying `n` (sample size) so a one-booking spike is visibly distinguishable from a robust mean.
4. **UX-WEAK:** Title says "Margin captured" but Negative-y = capture; sign is counter-intuitive at first glance. The sub-title rescues it ("Negative = below list") but it's small. No annotation on the chart itself for spikes — a $300 outlier day is unlinkable to the call_id that caused it.
5. **INFORMATION-WEAK:** Aggregating to daily mean over a small dataset (the demo will likely have <30 bookings total) makes most days have n=1, which means the "trend" is basically a sequence of single bookings. Median+IQR ribbon would be more honest at this dataset size.
6. **Improve:** (a) flip the y-axis sign convention to "savings vs list" so positive = good (still keep tooltip honest about direction); (b) make each dot click-through to the relevant call's detail page when n=1 for that day. **M** for the click-through (needs API to expose the underlying call_id per-day).
7. M.

---

### Funnel tab — single chart
File: `dashboard/src/components/charts/funnel-chart.tsx`

1. **Tab/file:** Overview > Funnel · `funnel-chart.tsx`.
2. **Shows:** horizontal Recharts `<BarChart>` of `funnel.by_outcome`, ordered `load_booked → no_match → carrier_not_qualified → call_abandoned`. Custom colour per stage.
3. **GOOD:** Honest about not being a true funnel (the comment in the file calls this out; the API exposes a flat outcome distribution, not a per-stage subset). Horizontal bar is correctly chosen for a 4-category enum. Colours match the OUTCOME_COLORS map used in `quality-pies.tsx` — consistent.
4. **UX-WEAK:** The label literally says "Funnel" in the tab + chart title, but the visual is a bar chart of a flat enum. A reviewer who knows funnels will notice. No percentage labels on each bar — the eye has to zoom in on the axis to read counts.
5. **INFORMATION-WEAK:** This is duplicate information with the "Outcomes" pie in the Quality tab — same data, different visual. Pick one.
6. **Improve:** (a) rename the tab "Outcomes" or transform the visual into a real funnel by showing `inbound → eligible → matched → booked` once those upstream-stage counts are exposed by FastAPI (see master plan §3); (b) add `<LabelList>` with `count (pct%)` per bar to spare the user the axis math. **M** for the rename + delete-the-pie consolidation; **S** for the labels.
7. M.

---

### Economics tab — 4-card grid
File: `dashboard/src/components/economics-cards.tsx`

#### Card "Listed rate (avg)"
1. Overview > Economics · `economics-cards.tsx:73–77`.
2. `economics.avg_loadboard_rate`. Plain KpiCard, sky accent.
3. GOOD: Currency-formatted, paired left-right with Booked rate.
4. UX-WEAK: Same card appears in the Overview strip (KPI #4) — duplicated info between the strip and the tab. Reviewer wonders which one is canonical.
5. INFO-WEAK: Mean again; see KPI #4.
6. Improve: drop from the strip OR drop from this tab. The tab feels like the right home (more context-rich). **S**.
7. S.

#### Card "Booked rate (avg)"
- Same duplication with KPI #5 in the strip. Same comment.

#### Card "Margin captured" (the centerpiece of this tab)
1. Overview > Economics · `economics-cards.tsx:86–137`.
2. `economics.effective_delta_dollars` + `effective_delta_pct`. Custom card (not KpiCard) so it can render a coloured value + tone-coded badge + Info tooltip.
3. **GOOD:** Tone mapping (emerald = below list = margin captured; amber = above list = concession) is principled and matches the hero chart's sign convention. Info tooltip explains the sign convention. Ring-1 outline subtle but helpful.
4. **UX-WEAK:** Sign-convention surprise again — "−$83" is the *good* state. The tooltip makes it explicit but a reviewer scanning the dashboard for 5 seconds will pause. No spark version of this scalar.
5. **INFORMATION-WEAK:** Without context "is captured margin trending up or down vs prior period?" the reviewer can't tell. The hero already shows trend; the scalar should show the prior-period delta.
6. Improve: (a) flip display to "+$83 saved vs list" (positive = good in the user's read); (b) add a `delta_pct_vs_prior` field for this scalar specifically. **S** (a), **M** (b).
7. S–M.

#### Card "Revenue booked"
1. Economics · `economics-cards.tsx:139–146`.
2. `economics.total_revenue_booked`, with hint "Across N loads", delta + spark wired.
3. GOOD: Right metric (sum of `apply_rate`); hint includes denominator; full delta+spark.
4. UX-WEAK: When `total_calls_with_rate=0` the hint reads "Across 0 loads" — fine, but the value reads `$0.00` which is technically correct yet visually identical to "no data".
5. INFO-WEAK: None — this is the cleanest card on the dashboard.
6. Improve: when `total_calls_with_rate=0`, render `—` instead of `$0.00` to differentiate "no data" from "data and the answer is zero". **S**.
7. S.

---

### Operational tab — 3 KpiCards
File: `dashboard/src/components/operational-cards.tsx`

#### "Call duration (avg)"
1. Operational · `operational-cards.tsx:8–20`.
2. `operational.avg_duration_seconds` (rendered as `${n}s`); `deltaInverted` (lower-is-better).
3. GOOD: `deltaInverted` is correctly applied — shorter duration is generally better for inbound carrier-sales economics.
4. UX-WEAK: `120s` reads less naturally than `2:00`. Most ops dashboards format duration as `m:ss`.
5. INFO-WEAK: Mean duration with no histogram is a poor summary — a 15-min outlier moves the mean a lot. p50 / p90 buckets would be more honest.
6. Improve: (a) format duration via `fmtDuration` (already exists in `lib/format.ts`); (b) post-MVP — replace with a small distribution chart. **S** for (a).
7. S.

#### "Carriers turned away" (FMCSA decline %)
1. Operational · `operational-cards.tsx:21–25`.
2. `operational.fmcsa_decline_pct`. `deltaInverted`. No spark.
3. GOOD: Important metric for the spec ("verify they are eligible"); inverted delta is correct (high decline rate = bad).
4. UX-WEAK: Label "Carriers turned away" is friendlier than "FMCSA decline %"; good copy. No `hint` clarifying which check failed (authority, insurance, MC mismatch).
5. INFO-WEAK: Without breakdown by `fmcsa_eligibility_failure_reason`, the metric is undiagnostic — "we turned 12 % away" doesn't tell ops *why* and so they can't fix anything.
6. Improve: add a hint or click-through that drilldowns by failure-reason enum. The data exists in `calls_log.fmcsa_eligibility_failure_reason`. **M**.
7. M.

#### "Drop-offs" (abandon rate)
1. Operational · `operational-cards.tsx:26–30`.
2. `operational.abandon_rate_pct`. Inverted, no spark.
3. GOOD: Right inversion; "drop-offs" is plain English (better than "abandon rate %").
4. UX-WEAK: No spark. No definition tooltip — "drop-off" can mean different things.
5. INFO-WEAK: Lumped together: a carrier hanging up after FMCSA decline is an "abandon" and a carrier hanging up mid-negotiation is also an "abandon", but they have very different operational implications.
6. Improve: tooltip on the label saying "carrier hung up before booking", and sub-categorize when call-stage telemetry lands. **S** for tooltip.
7. S.

---

### Quality tab — KpiCard + 2 pies + remarks list
File: `dashboard/src/components/quality-pies.tsx` + page.tsx Quality TabsContent

#### Pie "Sentiment"
1. Quality · `quality-pies.tsx:52–65` via `<DistributionPie>` (`charts/distribution-pie.tsx`).
2. `quality.sentiment_distribution` (positive/neutral/negative). Coloured by `SENTIMENT_COLORS` (green/blue/red).
3. GOOD: Donut hole is wide enough that legend text isn't crowded; tooltip shows count + pct; right colour assignments.
4. UX-WEAK: Donut for 3 categories is overkill — a horizontal stacked bar uses screen real estate better and lets the eye compare proportions across periods (you'd put two stacked bars side-by-side: "this week vs last week"). Donut also makes "negative 8 %" hard to estimate at a glance because the slice angle is small.
5. INFO-WEAK: Stage at which sentiment was sampled isn't disclosed — `sentiment_end` (post-call extraction)? mid-call? Reviewer can't tell.
6. Improve: replace donut with horizontal stacked bar (single Recharts `<BarChart layout="vertical">` with 3 `<Bar stackId>`). Add tooltip clarifying the source. **S** swap-only, **M** with prior-period comparison.
7. S.

#### Pie "Outcomes"
1. Quality · `quality-pies.tsx:66–79`.
2. `quality.outcome_distribution` (with fallback to `funnel.by_outcome`).
3. GOOD: Same colours as the funnel-tab horizontal bar — visual consistency.
4. UX-WEAK: This is the same data as the Funnel tab, in a different visual. Either pick a winner or position one as a sub-set / drill-down of the other.
5. INFO-WEAK: Donut for 4 categories with one dominant slice (`load_booked` or `no_match`) makes the others look insignificant even when they matter.
6. Improve: remove this pie OR remove the funnel-tab bar — see Funnel-tab finding above. **S**.
7. S.

#### KpiCard "Quality score (avg)"
- Same metric as Overview KPI #6, displayed three times (strip + here + carrier drilldown). Acceptable for a tab that's literally about quality, but could be replaced here with a CHS *distribution* histogram (the API exposes `chs_distribution` 0–20 / 20–40 / .. / 80–100 buckets and **the Quality tab does not render this distribution**, which is wasteful).
6. Improve: drop the avg KPI from the Quality tab and replace with a Recharts `<BarChart>` of the `chs_distribution` buckets. The avg is already on Overview. **S**.
7. S.

#### "Quality flags from recent calls" list
1. Quality > below pies · `page.tsx:148–168`.
2. `quality.auditor_remarks_sample` — up to 5 most-recent non-null `audit_remarks`.
3. GOOD: Plain-text list with muted background — minimal cognitive load. Anchors the abstract scores in concrete operator-readable language.
4. UX-WEAK: Each remark is unattributed — no MC, no call_id, no link to the call detail. "fmcsa_card_unclear" without context is decoration.
5. INFO-WEAK: 5 most-recent ≠ 5 most-important. A frequency-ranked tag cluster (which the legacy `dashboard_aggregations.audit_remarks_clusters` exposes!) is more useful for broker-ops to fix patterns.
6. Improve: each row gets a "→ View call" link, and add a tag-frequency mini-bar above the list. **M**.
7. M.

---

## Calls tab — single sortable table
File: `dashboard/src/components/calls-table.tsx`, page wrapper `calls/page.tsx`

1. **Tab/file:** Calls · `calls-table.tsx`.
2. **Shows:** sortable, searchable table — When / MC / Carrier / Outcome / Sentiment / CHS / Rate / Duration. Source: `getCalls()` which probes `/v1/calls` first then falls back. Row click → `/dashboard/calls/[call_id]`. Sub-component: `<CallsSourceBadge>` warns when the API returned an empty fallback.
3. **GOOD:** Click-row-to-drill UX is right. Search across MC/carrier/transcript/audit_remarks is broad enough. Sort by every column. Outcome / Sentiment / CHS use shared coloured badges (`outcome-badge.tsx`, etc.) — visual language consistent with KPI cards. Empty state copy (`No calls in the selected window…`) is friendly.
4. **UX-WEAK:** No pagination — `limit=200` fetches whole list and renders all rows. At >500 rows the page will jank. No persisted sort/filter via URL (search query is React state only — can't share a link to "calls where outcome=load_booked").
5. **INFO-WEAK:** No row-level visualization (e.g., a sparkline of the call's negotiation rounds, or a small horizontal bar of margin captured per call) — the row is purely scalar data.
6. **Improve:** (a) URL-persist `sort` + `q` query params via `useDashboardFilters`; (b) virtualize the body with a small intersection-observer + slice (no library needed). **M**.
7. M.

---

## Call detail — `/dashboard/calls/[call_id]`
File: `dashboard/src/components/call-detail.tsx`

1. **Tab/file:** drill-through · `call-detail.tsx`.
2. **Shows:** breadcrumbs · big call_id heading · status badges row · "Telemetry" card (intermediate fires, p70 fired, p90 fired) · "Audit remarks" card · "Bookings on this call" card (full firehose: load lane, equipment, miles, weight, commodity, pieces, dimensions, pickup/delivery, notes, plus rate vs list delta) · transcript viewer with search + speaker parsing · "Related calls" link.
3. **GOOD:** This is the densest, most well-organized page. Breadcrumb pattern. Status badges grouped above the fold. Per-booking margin delta shown both in dollars and percent (the only place on the dashboard that does both). `<TranscriptViewer>` parses turns smartly, supports search highlight, collapses long content. Spec field coverage on the Bookings card hits every load field in the FDE spec table.
4. **UX-WEAK:** "Telemetry" card uses the labels "P70 fired" / "P90 fired" / "Intermediate fires" without any explanation — a broker reviewer who hasn't read the prompt design has no idea what these mean. "P70 fired" tooltip is critical. Also, `YesNo` colour mapping inverts for P90 (fired = bad) without telling the user which is which.
5. **INFO-WEAK:** "Related calls" is just a one-line link — could surface the count and last 3 dates inline. The transcript card has no waveform / timing / duration markers to anchor a phrase to where in the call it occurred.
6. **Improve:** (a) add tooltips on telemetry labels with one-sentence explanations ("P70 = filler-word fires after 700ms agent silence — proxy for snappy feel"); (b) "Related calls" preview-list with last 3 inline. **S** + **S**.
7. S.

---

## Carrier detail — `/dashboard/carriers/[mc]`
File: `dashboard/src/components/carrier-drilldown.tsx`

#### KPI strip (4 cards)
1. Carrier detail · `carrier-drilldown.tsx:76–101`.
2. Calls · Conversion · Avg CHS · Avg Agreed Rate. Sources: `/v1/carriers/{mc}` rollup + per-call list.
3. GOOD: Concise; 4-up grid; `hint` lines provide useful denominators ("3 of 8 booked"). `Avg CHS` slot embeds a `<ChsBadge>` instead of plain number — visual flair.
4. UX-WEAK: No sparklines/deltas — the carrier-detail strip feels static next to the Overview strip's lit-up cards.
5. INFO-WEAK: The "Est. revenue" hint on Avg Agreed Rate uses `avg_apply_rate × total_bookings` — that's an estimate of total, not the actual sum. If the API exposed `total_revenue_booked` per carrier this would be exact.
6. Improve: replace the est-revenue calc with a real summed field from the carriers rollup endpoint. **M** (API change).
7. M.

#### "Sentiment breakdown" stacked-bar list
1. Carrier detail · `carrier-drilldown.tsx:103–146`.
2. Three rows: positive / neutral / negative — each with a label, an inline horizontal bar, and `n · pct%`.
3. GOOD: This is actually the *best* sentiment visual in the dashboard — labelled, proportional, and you can directly compare three values. **It should replace the donut in the Quality tab.**
4. UX-WEAK: Bars are 2 px tall — easy to miss. Could be 8 px without burning real estate.
5. INFO-WEAK: None really; this is the right shape.
6. Improve: bump bar height to 8 px and copy the pattern up to the Quality tab. **S**.
7. S.

#### "Outcome breakdown" plain list
1. Carrier detail · `carrier-drilldown.tsx:148–174`.
2. 4-row "label — count" list. No bar.
3. GOOD: Concise; matches the spec's outcome enum exactly.
4. UX-WEAK: Visually inert next to the sentiment bars right above. Reads as "almost a chart but not quite".
5. INFO-WEAK: Same outcome data shown as bars + pies + funnel elsewhere — fourth representation.
6. Improve: same horizontal stacked bar treatment as the sentiment block. **S**.
7. S.

#### "Call history" — embedded `<CallsTable>`
- Same as the Calls-tab table, scoped to one MC. Search bar hidden via `showSearch={false}`. Same UX/info comments apply.

---

## New Bookings tab — `/dashboard/sales`
File: `dashboard/src/app/dashboard/sales/page.tsx`

#### KPI strip (3 cards)
1. New Bookings · `sales/page.tsx:69–90`.
2. Bookings · Revenue (booked) · Avg margin vs list. Computed locally from `getRecentBookings` payload.
3. GOOD: Computing client-side from the bookings payload keeps it self-consistent with the cards below (no risk of "the number says 5 but I see 4 cards"). Default rolling-24h window is the right persona ("what shipped today").
4. UX-WEAK: No sparkline/delta on any of the 3 cards (and no API field for them either since the page computes locally). Cards feel ornamental.
5. INFO-WEAK: "Avg margin vs list" hint reads `Across N priced bookings` — fine, but doesn't disclose that it's a *mean* (susceptible to outliers).
6. Improve: server-side endpoint computes the 24h window stats with prior-day delta + spark. **M**.
7. M.

#### `<SalesRepCard>` grid (left col, ~60 % width)
1. New Bookings · `sales-rep-card.tsx`.
2. Custom card per booking — accent bar (emerald/amber/primary based on margin), MC link, booked timestamp, big rate, list rate sub-line, dollar-delta-vs-list line, lane row with origin → destination, equipment + miles + commodity + sentiment chip, "View call" / "View carrier" footer links.
3. **GOOD:** This is the most *creative* component on the dashboard and does its job — the page reads as "shipped work" rather than "another KPI tile". Vertical accent bar carries emotional read; pulse animation for sub-5-min bookings is a delightful detail. Honest sign convention (positive dollar = above list = amber, vs. the `EconomicsCards` "negative = good" convention — they're consistent because here positive `+$50` is broker-favourable for an apply-rate sale, while in the negotiated-down framing the math flips).
4. **UX-WEAK:** Wait — the convention is *inconsistent* with the hero `<EffectiveDeltaChart>`. There, "negative = below list = green = margin captured". Here, "positive = above list = green = positive margin". A reviewer comparing the two will be confused. (This is finding D-NEW.)
5. **INFO-WEAK:** No call-quality signal beyond the sentiment chip (no CHS, no outcome). For a sales-rep view, "is this booking healthy?" matters.
6. Improve: (a) align sign convention with the hero — pick one and apply globally; (b) add a CHS pill in the footer next to the outcome chip. **S** for (b); **M** for (a) once you decide which way.
7. S–M.

#### `<ActiveCallsMini>` panel (right col)
1. New Bookings · `active-calls-mini.tsx`.
2. Live polling every 10 s of `/api/calls/active`. Pulsing dot, count, up-to-5 in-flight rows with MC + current_node + elapsed timer.
3. GOOD: 10 s polling without SWR/library is the right scale. Status states (idle/error/unconfigured) handled. Reduced-motion respected.
4. UX-WEAK: The pulsing dot competes with the booking-card pulse for attention; once a real call is in flight it's an A-A-B-B fight.
5. INFO-WEAK: `current_node` value (e.g. `negotiate_evaluate`) is inside-baseball jargon — broker reviewer doesn't know what node names mean.
6. Improve: map `current_node` to broker-friendly labels via a small lookup table ("Negotiating", "Searching loads", "Verifying carrier"). **S**.
7. S.

#### `<AvailableLoadsList>` panel (right col, below Active Calls)
1. New Bookings · `available-loads-list.tsx`.
2. Up to 6 unbooked loads — origin → destination, rate, equipment, miles, commodity, "Available now" chip.
3. GOOD: Quietly visualizes inventory; shorthand chip "Available now" is a nice operational signal.
4. UX-WEAK: List is hard-capped at 6 with no "show more" link — the reviewer is left wondering "is there nothing else?". The header *does* show the total count ("12 ready") which is the only hint.
5. INFO-WEAK: Loads aren't sorted by anything obvious from the UI — sorted by earliest pickup per the API comment, but the user can't tell.
6. Improve: small "View all" link to a (currently nonexistent) `/dashboard/loads` page; show pickup date on each row. **S** for the date, **M** for the loads index page.
7. S–M.

---

## Header — `<ActiveCallsIndicator>`
File: `dashboard/src/components/active-calls-indicator.tsx`

1. Header (every tab) · `active-calls-indicator.tsx`.
2. Pulsing dot + count, opens a slide-over panel with all live runs.
3. GOOD: Self-contained — no Sheet primitive needed. Escape-to-close. Reduced motion. The slide-over is visually correct.
4. UX-WEAK: Same pulse-everywhere problem as `ActiveCallsMini` (the *Sales* page renders both). Consider rendering one OR the other based on route.
5. INFO-WEAK: `current_node` jargon problem repeats here.
6. Improve: hide the header indicator on the Sales route to avoid duplication; share a hook so polling isn't doubled. **S**.
7. S.

---

## Date-range picker
File: `dashboard/src/components/date-range-picker.tsx`

1. Sub-header on every dashboard route · `date-range-picker.tsx`.
2. Trigger button labelled `from → to`, dropdown with 7 preset chips + native `<input type="date">` from/to + Apply button. Sanitization (swap, clamp future, drop pre-2000).
3. GOOD: ADR-011 compliance — vanilla, no `react-day-picker` / `@radix-ui/react-popover` / `date-fns`. Sanitize logic is principled and matches the edge-case table. Preset highlight via `matchPreset`.
4. UX-WEAK: Native `<input type="date">` is OS-themed — looks great in dark Chrome on Mac, dated in Windows Firefox. Apply-button-required model means presets *do* auto-apply but custom dates need an extra click. Empty-state behaviour when user types `20`-then-stops is unclear.
5. INFO-WEAK: No "Apply" doesn't show a confirmation; the picker just closes. A reviewer doing a fast click-through doesn't know if their range took effect (the URL changes but they're not looking at the URL bar).
6. Improve: add an inline "Filter active" badge with the resolved range to the sub-header strip when the range deviates from "Last 7d" (the implicit default). **S**.
7. S.

---

## Other observations

### T-1. Tab order
Header is **Overview → Calls → New Bookings**. Carriers is missing from the nav (only reachable by clicking an MC link). For a broker reviewer, "Carriers" and "Loads" are first-class entities and they expect a top-level tab for each. Adding **Carriers** as a 4th tab (with a list page that uses the existing `<CarrierRollupTable>`) is **M** because the rollup table component already exists; it just needs a page wrapper at `/dashboard/carriers/page.tsx`.

### T-2. Empty states
Every chart and table has a friendly empty state, which is excellent. The hero chart, both pies, both bars, the carriers rollup, the calls table, and the call-detail/carrier-detail wrappers all degrade to "No data" copy. The KPI strip at the top of Overview will render `0` / `—` / `$0.00` though, with no "No data yet — start taking calls" banner. **S** to add a banner above the strip when `funnel.total_calls === 0`.

### T-3. Hidden carriers route
`/dashboard/carriers/[mc]` exists but `/dashboard/carriers/` (the index) does not — the carriers rollup table has no home. The component (`carrier-rollup-table.tsx`) is built and unused in any page. **M** to wire it up.

### T-4. Loading states at 30 s revalidate
Pages use `revalidate=300` (5 min, ADR-009 with webhook+SSE for sub-second). `dashboard/src/app/loading.tsx` renders 1 heading skeleton + 4 card skeletons + 1 large skeleton — generic, not tab-shaped. After the first load, ISR keeps the page snappy because Next serves the cached HTML. Cold load on Vercel-equivalent is what matters and the skeletons are right-sized.

### T-5. Dark-mode legibility
The KPI sparkline uses `hsl(var(--chart-N))` tokens. The funnel + sentiment + outcome charts use *hardcoded* HSL colours (`hsl(142 71% 45%)` etc.) which are calibrated for a light background. On dark mode the green-on-dark-grey of `load_booked` works; the slate `call_abandoned` (`hsl(215 16% 60%)`) is barely visible against any dark muted background. **S** to migrate funnel-chart + distribution-pie to `hsl(var(--chart-N))` tokens for theme-awareness.

### T-6. Sign-convention conflict
`<EffectiveDeltaChart>`: negative = good (below list). `<EconomicsCards>` Margin captured: negative = good. `<SalesRepCard>` and `<CallDetail>` bookings: positive = good (above list = `+$50` shown green). The user has to context-switch between two opposite sign conventions. (See "Top 5" #1.)

### T-7. Duplicate metric instances
The same outcome-distribution data is rendered three times (Funnel-tab bar + Quality-tab pie + carrier-detail list) and the same booked-rate-vs-listed comparison appears four times (Overview KPI #4+#5, Economics tab, hero chart, every booking card). Not a bug, but a redundancy a reviewer will see as bloat.

---

## Top 5 highest-leverage changes (≤ 30 min each)

1. **Pick one sign convention and apply everywhere (T-6).** Decide whether "negative dollars vs list" or "positive dollars saved" is canonical, then propagate. Hero, Economics card, sales card all flip the same way. Loud win for trust. **S** if you don't change wording, **M** if you also rewrite copy.

2. **Wire missing spark + delta on KPIs #2 (Bookings), #3 (Booked rate), and the entire Operational tab.** API already returns `delta_pct_vs_prior` + `sparkline` on every endpoint that has them — plug them into the existing `KpiCard` props. Restores visual symmetry and reads as a polished v2 dashboard. **S**.

3. **Rename the "Funnel" tab to "Outcomes" and delete the Quality-tab outcome donut.** Two visuals showing identical data on adjacent tabs is the single biggest "looks unfinished" tell on the dashboard. Add `<LabelList>` to the bar so counts are inline. **S**.

4. **Surface the existing `chs_distribution` buckets as a histogram on the Quality tab.** The API already returns `{0-20, 20-40, 40-60, 60-80, 80-100}` — render as a 5-bar Recharts `<BarChart>`. The Quality tab currently has *zero* charts about CHS itself, which is the central quality scalar. Replace the redundant Avg CHS KpiCard at the top of the tab with this. **S**.

5. **Add the carriers index page (T-3).** `<CarrierRollupTable>` is already built and unused; just create `dashboard/src/app/dashboard/carriers/page.tsx` that fetches `getCarriers()` and renders the table, then add a `Carriers` link to `Header.NAV`. Closes the loop on the existing drill-through. **M** (~45 min including the nav link, but worth the slot — without it the rollup table is dead code).

---

## Closing notes
- Read-only audit; no files were modified.
- All recommendations stay inside the ADR-011-permitted stack (Recharts + Radix-shadcn + Tailwind 4 + lucide). No re-introduction of `nuqs`, `@tremor/react`, `react-day-picker`, `date-fns`, or `@radix-ui/react-popover`.
- Bigger Tier-2 items (real funnel with upstream stages, dynamic filtering, CloudWatch-style agent metrics) are out of scope for this review and tracked separately.
