# Dashboard UI Direction: Data-Density / BI-Tool Lens

**Audience:** Acme Logistics carrier-operations staff (live-call watchers + KPI hawks).
**Reference targets:** Tableau, Power BI, Looker, Mode, Sigma.
**Stack constraint:** Next.js 15 + Tailwind 4 + shadcn/ui + Recharts. No Tremor / nuqs / react-day-picker / date-fns / Popover-Calendar (per ADR-011).
**Tabs covered:** Overview / Calls / Carriers / New Bookings.
**Pain points being solved:** unreadable axes, low information density, AI-default chart styling, no actual-vs-target framing, missing global sticky filter, top-tab nav cramped.

The four directions below are mutually exclusive — pick one as the spine. Each is implementable in the locked stack and addresses the user's "actual / target" framing in at least two cases.

---

## Direction 1 — "Bloomberg Terminal"

> Maximum density. Every cell earns its pixels. Designed for an ops lead who keeps the dashboard open all day on a second monitor.

### Layout

```
+------------------------------------------------------------------+
| GLOBAL HEADER  [Acme logo] [date: 7d|30d|MTD|custom▾]  [⏱ live]  |
+----------+-------------------------------------------------------+
| LEFT NAV | CANVAS                                                |
|          |                                                       |
| Overview | KPI STRIP  (6 cols × 1 row, ~96px tall each cell)     |
| Calls    | ┌─────┬─────┬─────┬─────┬─────┬─────┐                 |
| Carriers | │KPI 1│KPI 2│KPI 3│KPI 4│KPI 5│KPI 6│                 |
| Bookings | └─────┴─────┴─────┴─────┴─────┴─────┘                 |
|          |                                                       |
| ─ filters| DATA GRID  (12-col × 4-row at default zoom)           |
| outcome  | dense panels: small-mult charts, sparkline tables    |
| sentmt   |                                                       |
| MC#      |                                                       |
| equip    |                                                       |
+----------+-------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **KPI strip = 6 cells × 1 row, 96 px tall.** Each cell shows: large numeric (28 px tabular-nums), `actual / target` chip below (e.g. `33.3% / 10%` green if ≥ target, amber within 20%, red below), 30-day embedded sparkline (no axes, no legend, 1 px stroke), tiny delta vs. previous period in top-right. Built from `<Card>` + a shadcn-styled `<svg>` sparkline (40 px tall) — no Recharts wrapper for KPI cells (overhead too high at this density).
2. **All chart axes opt out of Recharts defaults.** Custom `<XAxis tick={{fontSize: 10, fill: '#64748b'}} tickMargin={4}>` + `<YAxis width={28} tickCount={4}>`. No grid lines except faint horizontal at multiples of target. Tooltip is a single line: `Apr 28 · 12 calls · target 10`.
3. **Tabular-nums everywhere.** Tailwind class `tabular-nums` on every numeric cell — eliminates the dancing-decimals jitter that makes BI dashboards feel cheap.
4. **Targets are first-class data.** A `targets.ts` config exports `{ booked_rate_pct: 10, chs_avg: 70, latency_p90_ms: 800 }`. Every KPI cell + every chart Y-axis renders a dashed reference line at the target value. ChartReferenceLine is a Recharts primitive — zero new deps.
5. **Color is reserved for status, not decoration.** Slate-700 for all numbers, slate-400 for all axes. Green/amber/red appear ONLY in actual-vs-target chips and CHS distribution. Chart series use a 3-tone slate ramp.
6. **Left rail is permanent + collapsible to icons-only at 56 px.** Section 1 = tabs (Overview/Calls/Carriers/Bookings). Section 2 = active filter facets as toggleable pills (outcome, sentiment, MC#, equipment, has-booking). Filter changes apply globally and are URL-state via `useSearchParams`.
7. **Sticky date header with preset buttons** (`7d | 30d | MTD | custom`). Custom = two native `<input type="date">` fields side-by-side — no calendar popover (ADR-011). Header pins on scroll.

### Per-tab rendering

- **Overview:** 6-col KPI strip on top, 12-col × 3-row data grid below: revenue-booked time series (6 cols), CHS distribution histogram (3 cols), sentiment pie (3 cols), funnel calls→bookings (6 cols), operational latency p50/p70/p90 stacked area (6 cols).
- **Calls:** KPI strip (calls, booked-rate, avg duration, flagged count, p90 latency, CHS avg) + dense table beneath (12-col, 30 rows, expandable to drilldown panel right of the row — not a modal).
- **Carriers:** KPI strip (unique MCs, repeat-caller rate, top MC by bookings, FMCSA-fail rate, avg-CHS-per-MC, avg-bookings-per-MC) + sortable carrier table with embedded per-row sparkline (calls over 30d).
- **New Bookings:** KPI strip (bookings count, revenue, avg-discount-vs-listed, avg-time-to-book, top-lane, top-equipment) + booking-list table with origin→dest cell, agreed/listed delta, MC link.

### Rationale (freight-broker daily workflow)

Ops staff do not browse — they monitor. The Bloomberg-density layout puts every KPI a glance away with no clicks; targets are visible at all times so deviations are pre-attentive (red chip on "booked-rate 6.2% / 10%" jumps out immediately). Sparklines next to MCs let staff see "Carrier ABC123 called us 8 times this month" without leaving the table. This matches the Tableau / Power BI muscle memory the audience already has.

### Sacrifices

- Visually overwhelming on first load — new users will need a 30-second walkthrough.
- Mobile is unusable; must be explicitly desktop-first (≥ 1280 px).
- High implementation cost: every cell is custom-styled, custom sparkline component, target config, status-chip component.

---

## Direction 2 — "Pivot-First Inspector"

> Calls tab is the canonical surface; everything else is a derived view. Modeled on Mode + Sigma's pivot-as-default philosophy.

### Layout

```
+------------------------------------------------------------------+
| GLOBAL HEADER  [date filter] [export ⤓]                          |
+----------+-------------------------------------------------------+
| LEFT NAV | CANVAS = PIVOT MATRIX                                 |
|          |                                                       |
| Overview |   ┌──── columns: dates ────────────────────┐           |
| ▶ Calls  |   │ rows ↓     Apr 24  Apr 25  Apr 26  ... │           |
| Carriers |   │ booked        4       7       3        │           |
| Bookings |   │ no-rate       2       1       5        │           |
|          |   │ no-mc         1       0       2        │           |
| pivot:   |   │ flagged       1       2       0        │           |
| rows ▾   |   └─────────────────────────────────────────┘          |
| cols ▾   |                                                       |
| metric ▾ |   [click a cell → right-side drilldown drawer]        |
+----------+-------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **Calls tab = pivot table by default.** Rows-dimension dropdown (default `call_outcome`), columns-dimension dropdown (default `created_at::date`), metric dropdown (default `count(*)`; alternates: `avg(case_health_score)`, `sum(agreed_rate)`, `avg(duration_seconds)`). Built from a plain `<table>` with `tabular-nums` + `border-collapse` and a manual pivot transform in `lib/pivot.ts` — no library.
2. **Cell drilldown.** Click any cell → right-side `<Sheet>` (shadcn) opens with the underlying call rows; second click on a row opens the call's transcript + CHS breakdown beneath it. Browser history pushed via `useSearchParams` so the URL is shareable.
3. **Cell heatmap.** Cell background opacity = value / max(row). Single-hue (slate) so the data is legible at a glance without a key. Toggle off via header switch for users who prefer plain numbers.
4. **Targets shown as a "vs target" pivot mode.** Header toggle: `count` | `vs target`. In vs-target mode, cells render `actual / target` (e.g. `12 / 10`) with green/amber/red text. Targets pulled from `targets.ts` keyed by row dimension.
5. **Other tabs are pre-canned pivot views.** "Overview" = pivot frozen on `metric=count, rows=outcome, cols=date` plus a small KPI strip on top. "Carriers" = pivot frozen on `rows=mc_number, cols=outcome`. "Bookings" = pivot frozen on `rows=load_id, cols=date, metric=sum(agreed_rate)`. Same component, different frozen params.
6. **Charts are inspector-panel-only.** No hero charts on Overview. Right drawer renders a small Recharts line + sparklines for whatever cell or row the user has selected. Reduces "AI-default" chart overload.
7. **Saved views.** `?rows=outcome&cols=date&metric=count` → bookmarkable. Add a "Save view" button that writes a named entry to `localStorage` (no backend) and lists them on left rail.

### Per-tab rendering

- **Overview:** 6-cell KPI strip + frozen pivot (rows=outcome, cols=date, metric=count, vs-target on). One cell preview chart below.
- **Calls:** Full pivot interface — user picks rows/cols/metric. Drilldown drawer renders call list + per-call CHS + transcript on second click.
- **Carriers:** Pivot frozen on rows=mc_number. Sort cols by total. Click MC row → drawer shows that carrier's call history.
- **New Bookings:** Pivot frozen on rows=load_id, metric=sum(agreed_rate). Click load → drawer shows which calls booked it.

### Rationale (freight-broker daily workflow)

Ops staff routinely ask "how many no-mc calls last Tuesday vs. this Tuesday" — that's a pivot question. Today's tabbed dashboard forces them to context-switch between charts; a pivot lets them answer any question with two dropdowns. Power-user-friendly, BI-native, and the same component drives all four tabs (huge code-reuse win).

### Sacrifices

- Unfamiliar to non-analyst users — Excel-pivot-table fluency required; ops staff who prefer "show me the chart" will struggle.
- Less visually impressive on first impression (no hero charts on Overview).
- Drilldown drawer + cell-click pattern is more interaction-heavy than passive monitoring; not ideal for a wall-mounted second-monitor view.

---

## Direction 3 — "Small-Multiples Wall"

> Replace every hero chart with a 3 × 3 grid of small linked charts. Each tile is one slice; they share an X-axis and a brushed selection. Inspired by Edward Tufte + Looker dashboards.

### Layout

```
+------------------------------------------------------------------+
| GLOBAL HEADER  [date filter]  [brush selection ▶ Apr 24-28]     |
+----------+-------------------------------------------------------+
| LEFT NAV | CANVAS = 3×3 SMALL-MULT GRIDS                         |
|          |                                                       |
| Overview |  ┌────┬────┬────┐  ┌────┬────┬────┐                  |
| Calls    |  │Mon │Tue │Wed │  │book│no-r│no-m│                  |
| Carriers |  ├────┼────┼────┤  ├────┼────┼────┤                  |
| Bookings |  │Thu │Fri │Sat │  │tran│neg │flag│                  |
|          |  ├────┼────┼────┤  ├────┼────┼────┤                  |
|          |  │Sun │7d  │Avg │  │CHS │dur │SMS │                  |
|          |  └────┴────┴────┘  └────┴────┴────┘                  |
|          |   "calls by day"     "outcome split"                  |
+----------+-------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **Hero chart pattern is banned.** Every place a 600 × 300 chart would have gone, render a 3 × 3 grid of 180 × 120 small-multiples instead. Recharts handles this trivially with a `<ResponsiveContainer>` per tile in a CSS grid.
2. **Linked brushing across tiles.** Single brush (component: `<Brush>` from Recharts, mounted once at top of canvas) drives all small-mult tiles via React context. Hover on tile → highlights same X position across all tiles.
3. **Each tile has 1 metric, 1 series, no legend.** Tile title = small-caps 11 px label above. No axes labels — only tick values. Y-axis is 28 px wide with 3 ticks max. The shared X-axis lives at the bottom of the row and is only labeled once.
4. **KPI strip = 8 cards of 4 KPIs each.** Above the small-mult grids: a strip of denser KPI cards (8 across at 1280 px). Each shows actual/target + 7-day sparkline. Same primitive as Direction 1 but smaller (~72 px tall).
5. **"Compare" toggle.** Header switch: `single` | `vs prior period`. When `vs prior`, every tile draws two series (current = solid slate, prior = dashed gray). Listed-rate-vs-booked-rate shown the same way.
6. **Tab content scoped to one "wall" each.** Overview wall = funnel + revenue + sentiment + CHS. Calls wall = outcome × day. Carriers wall = top 9 MCs by call volume each as a tile. Bookings wall = top 9 lanes.
7. **No tables.** Carriers wall has 9 mini-tiles each labeled with the MC# — click a tile to drill to the carrier's full record in a `<Sheet>`.

### Per-tab rendering

- **Overview:** Two 3 × 3 grids stacked vertically — top grid = "calls split by outcome over 9 days", bottom grid = "9 KPIs over time" (calls, bookings, booked-rate, CHS, latency-p90, sentiment-positive, flagged, listed-rate, booked-rate).
- **Calls:** 3 × 3 grid of call counts, one tile per outcome enum value, each tile shows the daily series for that outcome. Brush at top scopes the date range.
- **Carriers:** 3 × 3 grid of top-9 carriers by call volume; each tile = sparkline of that carrier's calls over 30 days.
- **New Bookings:** 3 × 3 grid of top-9 lanes (origin→dest pairs); each tile = revenue over time for that lane.

### Rationale (freight-broker daily workflow)

Brokers think in pattern recognition — "did Tuesday spike again?" or "is the Atlanta lane trending up?". Small-multiples turn these into pre-attentive shape-comparisons (Tufte's "shoebox of stamps"). It also cures the "AI-default chart" feel: 9 small charts read as a deliberate composition, where one big chart reads as a default.

### Sacrifices

- Doesn't satisfy actual/target framing as cleanly — each tile is too small for a chip; targets become reference lines only (KPI strip carries the target chips).
- Doesn't suit ad-hoc questions ("count of calls where MC=ABC") — needs a separate Calls table view.
- 9 tiles × 4 tabs = 36 chart instances; needs careful Recharts memoization to stay performant.

---

## Direction 4 — "Filter-Manifold Canvas"

> One canvas. One pill bar of 8+ active facets. Selection cascades. Modeled on Sigma's filter-rail + Power BI's slicer-panel pattern.

### Layout

```
+------------------------------------------------------------------+
| GLOBAL HEADER  [Acme logo]                          [⏱ live]    |
+----------+-------------------------------------------------------+
| LEFT NAV | FACET PILL BAR (sticky, wraps to 2 rows on narrow)    |
|          | [date: 7d ▾] [outcome: all ▾] [sentiment ▾] [MC ▾]    |
| Overview | [equipment ▾] [CHS ≥ ▾] [flagged ▾] [has-book ▾] [×]  |
| Calls    +-------------------------------------------------------+
| Carriers | CANVAS — single dense composition driven by facets    |
| Bookings |                                                       |
|          | hero KPI row (4 cards w/ actual/target + sparkline)   |
|          | ── primary chart (revenue or pivot, tab-dependent)    |
|          | ── secondary 3-chart row (CHS, sentiment, latency)    |
|          | ── data table (calls / bookings / carriers)            |
+----------+-------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **Facet pill bar replaces all in-page filters.** Pills above canvas: date, outcome, sentiment, MC#, equipment, CHS-threshold, flagged, has-booking. Each is a shadcn `<Select>` (no Popover-Calendar). Pills with non-default values render in slate-900; defaults render in slate-400. "Clear all" × at the right.
2. **Cascade everywhere.** Every chart, KPI, and table on the canvas reads from a single zustand-style store driven by `useSearchParams`. URL is the source of truth. No chart has its own filter UI.
3. **Tab swaps the canvas template, not the filters.** Switching from Calls → Carriers preserves the pill state. The canvas re-renders with a different chart layout but the same facet selection. Reinforces the "filter manifold = the dashboard" mental model.
4. **Hero KPI cards = 4 cards × 1 row at 144 px tall.** Each card has: big number, `actual / target` chip with explicit target value, mini bar chart of the metric over the selected window, and a small "↗ +12% vs prior" delta chip. Bigger than Direction 1's strip — these are the load-bearing visual elements.
5. **Selection = cross-filter.** Click a bar in the primary chart → that value gets pushed onto the pill bar as a new facet. Right-click → exclude. This makes the dashboard feel like Sigma / PowerBI without writing a query language.
6. **Saved facet states.** Header has a "Save filter" button that writes the current pill set to `localStorage` with a name. Saved sets render as quick-access chips next to the date filter ("My queue", "Yesterday's flagged", "ABC123 last week").
7. **One sticky chart, one collapsible table.** Canvas always ends with a paginated `<Table>` (calls, carriers, or bookings depending on tab) at the bottom — same row count, same columns, but rows respond to facets. Table is collapsed-by-default on Overview, open-by-default on Calls/Carriers/Bookings.

### Per-tab rendering

- **Overview:** 4 KPI cards (calls, booked-rate, CHS-avg, revenue) → revenue-booked time series (primary) → CHS dist + sentiment dist + latency p90 (secondary 3-chart row) → collapsed calls table.
- **Calls:** Same KPI strip → outcome-by-day stacked bar (primary) → CHS dist + duration histogram + flagged count (secondary) → calls table (open).
- **Carriers:** 4 KPI cards (unique MCs, top MC, FMCSA-fail rate, avg-CHS) → MC-by-volume horizontal bar (primary) → repeat-rate + sentiment-by-MC + outcome-by-MC (secondary) → carrier table.
- **New Bookings:** 4 KPI cards (bookings, revenue, avg-discount, avg-time-to-book) → revenue-by-lane bar (primary) → equipment dist + agreed-vs-listed scatter + booking-time-of-day histogram (secondary) → bookings table.

### Rationale (freight-broker daily workflow)

A broker's day-to-day question is rarely "show me the dashboard" — it's "show me yesterday's flagged calls from Atlanta carriers on dry-van loads with CHS under 70". The filter-manifold model lets them assemble that question from pills in 5 seconds. Cross-filter on click means a chart insight ("Tuesday had a spike in no-mc") becomes a filter ("now show me only those calls") with one gesture. Saved filter sets become a personal worklist.

### Sacrifices

- Less "wow" first impression than Direction 1 or 3 — the canvas looks ordinary until you start clicking pills.
- Cross-filter requires careful chart-event wiring (Recharts onClick + URL state) — moderate engineering cost.
- The pill bar can become visually noisy when all 8 facets are non-default; needs strong typography discipline.

---

## How the four directions compare

| | Direction 1 (Bloomberg) | Direction 2 (Pivot) | Direction 3 (Small-mult) | Direction 4 (Manifold) |
|---|---|---|---|---|
| Information density | Highest | High | High | Medium-high |
| Actual / target framing | First-class everywhere | Toggle mode | KPI strip only | First-class on KPI cards |
| Interaction model | Passive monitoring | Pivot dropdowns + drilldown | Brush + sheet drill | Facet pills + cross-filter |
| Audience fit | All-day-monitor lead | Analyst / power user | Pattern-spotter | Question-asker / triage |
| Implementation cost | High (custom cells) | Medium (one pivot component drives everything) | Medium (Recharts grid heavy) | Medium-high (state + URL plumbing) |
| Risk if wrong | Overwhelming | Unfamiliar to non-analysts | Targets feel secondary | Looks plain on first load |

All four are implementable in the locked stack with no new dependencies. Direction 2 has the highest code-reuse upside (one pivot component for all four tabs); Direction 1 has the highest visual-impact upside; Direction 3 has the cleanest design provenance; Direction 4 has the best fit to ad-hoc operational questions.
