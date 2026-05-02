# Dashboard design philosophy — locked 2026-04-27

How to think about dashboards in this project. Not specific titles or layouts (those are illustrative examples that change over time) — the principles that should hold across MVP, Tier 2, and Tier 3 iterations.

## Principle 1 — Customer experience over agent compliance

Health metrics measure how the carrier (the customer) experienced the call. Legitimate business outcomes — FMCSA decline, no-match, polite walkaways — don't penalize health scores. Dissatisfaction signals (negative sentiment trajectory, hangups, escalation language, agent role-breaks) DO penalize.

This means: an FMCSA-decline call handled politely on both sides scores 100. A successfully-booked call where the carrier was hostile scores below the polite-decline call. Customer experience is the lens.

## Principle 2 — Multi-load is a positive signal, not a partial failure

When a call books 2 of 5 pitched loads, dashboards must reflect "2 bookings ✓" and avoid the "5 attempts → 2 success → 40% conversion" anti-pattern. Conversion ratios at the call-grain punish multi-load wins.

Headline metrics count BOOKINGS at booking-grain. Per-call multi-load celebration shows up as `bookings ÷ booked_calls > 1.0` ("1.3× per call" — the carrier got more value out of one conversation).

## Principle 3 — Null-resilient calculations always

Source data has nulls. Twin returns rows with NULL fields. Classifier outputs may be NULL on edge cases. Dashboards must NEVER:
- Render `$NaN` or `NaN%`
- Throw `ZeroDivisionError`
- Break on `sentiment="true"`-style coercion bombs
- Show empty rows that crash chart libraries

Use a `_safe_*` helper layer:
- `safe_avg(values)` returns None if all null
- `safe_pct(num, den)` returns None on zero/null den, never NaN
- `safe_count(rows, predicate)` traps exceptions in predicates
- `safe_bool(v)` accepts True/False/"true"/"false"/"1"/"0"; anything else routes to None

UI fallback: render "—" or "Pending" when underlying data is null.

## Principle 4 — Filter ergonomics: preset pills + persistence

Time filters use preset pills (1d / 1w / 2w / 1m / 6m / 1y) over date pickers. Default to 1w. URL state persists filter selection so refreshes don't reset.

Sentiment, outcome, and MC filters are chips — multi-select with active-filter tray. Clear visual when a filter is engaged.

## Principle 5 — Goal mimicking creates demo gravity

Add fake / aspirational goal targets to KPI tiles. "12 / 15 goal" is a more compelling demo signal than "12". Progress bar visual: green at/above goal, amber below. Even when the goal is illustrative for the demo, it signals "this is a real ops tool" not "this is a static report."

Goals can live as workflow variables (configurable post-deploy) or hardcoded in the dashboard config. Document that they're aspirational targets, not contractual SLAs.

## Principle 6 — Interactive over static

Click any KPI tile → drilldown modal showing time series + recent rows. Click any chart segment → filter the dashboard to that segment (e.g., click "FMCSA decline" slice → all panels filter to declines).

Sparklines under every KPI tile show trend over the filter window. Tiny visual, high cognitive payoff.

Recent calls table → click row → opens call drilldown (transcript + per-load bookings + audit remarks).

## Principle 7 — Tier 1 / Tier 2 / Tier 3 progressive disclosure

Default view is MVP-essential (4-5 KPI tiles, 1-2 supporting charts). Advanced query flag `?advanced=1` reveals Tier 2 (lane mix, FMCSA decline breakdown, sentiment trajectory). Tier 3 (recursive self-improvement loops, A/B test reads, OTel traces) lives elsewhere — a separate route or app.

Don't pack everything into one screen. Carlos sees Tier 1; Andres can drill via the advanced flag.

## Principle 8 — Never expose raw variable names in chart labels

Charts label "Listed Rate" not `pitched_loadboard_rate`. "Discount %" not `agreed_rate / loadboard_rate`. The dashboard speaks broker-language, not engineer-language. Internal column names are an implementation detail.

Tooltips can include the calculation in plain English ("Discount % = (asking − final) / asking × 100") but never the SQL.

## Principle 9 — Avoid donuts when grain doesn't compose

A donut implies parts of a whole at the same grain. If you're plotting call-grain (M-001) alongside booking-grain (M-080), they don't sum to a meaningful whole. Use stacked bars or paired KPI tiles instead. Donuts are reserved for true compositional metrics (sentiment mix where each call has exactly one sentiment).

## Principle 10 — No "why this matters" verbose sections

Don't pad the UI with explanatory paragraphs. Charts speak for themselves. Tooltips on hover for the rare "what's this?" moment. Documentation lives in `docs/dashboard-metric-catalog.md` for the engineer; the dashboard surface is for the operator.

## Principle 11 — Empty states matter

Zero data is a normal state, especially in early demo days. Show graceful empties:
- "Pending data pipeline" caption when a metric is gated on a binding fix
- "No calls yet today" with a small icon when the filter window is empty
- Sparklines render flat baselines instead of disappearing

Never show a broken chart, a console error, or a 500 page.

## Principle 12 — Consistency: palette, typography, spacing

One palette across all panels. One typography scale. One spacing rhythm. Dashboard reads as a single tool, not a collection of widgets.

Brand: muted, professional, trust-conveying. Not gamified. Not consumer-app colorful. Think "Bloomberg Terminal" minimal, not "Mixpanel" friendly.

## Practical guidance for new metric proposals

Before adding any metric, answer:

1. **Persona**: who reads this? (Maria the floor lead / Devon the director / Andres the engineer / Priya carrier relations)
2. **Decision**: what action does it inform? (If none — drop it.)
3. **Grain**: per-call, per-booking, per-carrier, per-time-bucket?
4. **Source**: which Twin column or computed field? Any joins needed?
5. **Empty state**: what shows when no data? When all-null? When filter excludes everything?
6. **Tier**: MVP must-have, Phase 5.9 polish, or post-MVP roadmap?

If a metric can't justify each of these, it doesn't ship.

## Pairs with

- `docs/dashboard-metric-catalog.md` — current 29-metric catalog with persona/grain/source mapping
- `docs/v14-classifier-design-2026-04-27.md` — sentiment, outcome, CHS schemas these metrics consume
- Memory: `project_dashboard_v2_design_directives.md`, `feedback_analytical_foundation_before_dashboard.md`
