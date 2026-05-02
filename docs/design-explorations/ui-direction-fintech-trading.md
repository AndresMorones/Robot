# UI Direction Exploration — Fintech / Trading-Desk Lens

**Status:** Design exploration (non-binding)
**Date:** 2026-04-30
**Scope:** Reframe the Acme Logistics carrier-operations dashboard through a Bloomberg / Stripe Sigma / Mercury / Robinhood Pro / Carta visual vocabulary. Each booking is treated as a P&L event; the broker is the trader.
**Sign convention (all directions):** `margin = listed_rate − booked_rate`. Positive = broker won the negotiation. "Buy carriers DOWN from list."
**Stack constraints:** Next.js 15, Tailwind 4, shadcn/ui (Radix primitives only — no Calendar / Popover), Recharts, Lucide, vanilla `useSearchParams`. No Tremor, nuqs, react-day-picker, date-fns, or `@radix-ui/react-popover` (per ADR-011).

---

## Direction 1 — "The Pit" (Bloomberg 4-Pane Terminal)

**Elevator pitch:** Four fixed quadrants on a single pane of glass; keyboard-driven; dense numerics; everything important visible without scroll.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  ACME LOGISTICS │ CARRIER DESK │ 2026-04-30 14:32:11 ET │ ●live │ [F1] │  ← 28px header bar
├──────────────┬─────────────────────────────────────────────────────────┤
│              │  Q1: KPI MATRIX (8 tiles)   │  Q2: P&L TIMESERIES        │
│  LEFT RAIL   │  ─────────────────────────  │  ─────────────────────     │
│  [O]verview  │  calls 47  ▲12% / tgt 40    │  Cumulative margin today   │
│  [C]alls     │  book 12   ▲33% / tgt 10%   │  intraday step-line + vwap │
│  [Y] carrier │  margin $4.2k ▲ / tgt $3k   │  bands (P10/P50/P90)       │
│  [N]ew book  │  CHS  78   ▼3 / tgt 75      │                            │
│              │  ...                        │                            │
│  PRESETS     ├─────────────────────────────┼────────────────────────────┤
│  1H 4H 1D 5D │  Q3: ORDER BOOK (live)      │  Q4: BLOTTER (transactions)│
│  1M 3M 1Y    │  ─────────────────────────  │  ─────────────────────     │
│  ─────────── │  Active calls + open loads  │  Last 50 bookings, scroll  │
│  GLOBAL DATE │  side-by-side (bid/ask)     │  table w/ click-to-detail  │
│  [____] [__] │                             │                            │
└──────────────┴─────────────────────────────┴────────────────────────────┘
```

### 7 widget-pattern decisions

1. **Header strip (28px, monospace)** shows org name, desk name, server clock to the second, live/replay indicator, and a function-key hint. Fixed-height, non-scrolling, dark slate background.
2. **Left rail (160px)** uses single-letter hotkeys ([O], [C], [Y], [N]) shadcn-Tabs vertical; preset buttons 1H / 4H / 1D / 5D / 1M / 3M / 1Y stacked below in a 3×3 grid; global date inputs at the bottom (two `<input type="date">` per ADR-011).
3. **KPI Matrix (Q1)** is an 8-tile grid (4×2). Each tile: label uppercased 10px tracking-wide, primary value 28px tabular-nums, delta chip in green-400 / red-400 with arrow glyph, target line below ("tgt 10%") in 11px slate-500. No icons. No background imagery. Mono font on numerics.
4. **Time-series P&L (Q2)** is a Recharts `<ComposedChart>`: step-line for cumulative margin (positive = up), VWAP-style banded reference area (P10/P90 of historical same-time-of-day intraday distribution), zero baseline always shown. X-axis ticks every hour; Y-axis dollar-formatted on the right edge (Bloomberg convention).
5. **Order Book (Q3)** mirrors a depth-of-market view: left half = active calls (carrier MC, lane, time-on-call, agent state); right half = open loads (load_id, lane, listed_rate, age). Sort by best-fit lane match; row hover shades both sides.
6. **Blotter (Q4)** is a virtualized transaction table: timestamp (HH:MM:SS), call_id (last 6), MC, lane, listed → booked, margin (green/red), CHS pill, sentiment dot. Tabular-nums; alternating zebra rows in slate-900/slate-950; click row → side-drawer with transcript.
7. **Color discipline:** background stays slate-950; positives in green-400; negatives in red-400; warnings amber-400; flagged (CHS<70 OR negative sentiment) get a red-400 left-border flash that fades over 60s.

### Tab rendering

- **Overview** = the canonical 4-pane view above.
- **Calls** = Q4 (blotter) expands to fill 60% of canvas; Q3 collapses to a "live now" strip on the right; Q1 shrinks to a 4-tile horizontal ribbon.
- **Carriers** = Q4 reformats as a carrier-grouped pivot (MC → bookings count, win rate, avg margin, last seen); Q2 becomes per-carrier sparkline column.
- **New Bookings** = Q4 filters to today only; Q2 shows intraday cumulative; Q3 hides; Q1 shrinks to 2 tiles (today's bookings, today's margin).

### Replacement for "Margin Captured" central chart

**Intraday Cumulative Margin step-line with VWAP bands.** Single Recharts `ComposedChart`: cumulative `margin = listed − booked` plotted as a stepAfter line from 00:00 ET to now; behind it, a banded reference area shows the P10–P90 range of cumulative margin at the same time-of-day across the last 30 trading days. Broker reads this exactly like a P&L curve: am I above or below where I usually am by 14:32?

### Rationale (broker-as-trader)

A freight broker on a busy Tuesday is running parallel negotiations against expiring loads — the cognitive load is identical to a market-maker watching a book. The four-pane terminal collapses the loop "what's happening / what did I make / what's open / what just printed" into one screen with no tab-switching. Treating each booking as a printed trade in a blotter (Q4) and each open load as resting offer-side liquidity (Q3) gives the broker a mental model they can actually trade against. The intraday VWAP-banded P&L curve reframes a flat dashboard "today's margin" number as a relative-performance signal: *am I outperforming a normal Tuesday*?

### What this sacrifices vs current

- **Discoverability for new users.** Single-letter hotkeys + dense quadrants are intimidating without a 5-minute walkthrough; current dashboard is clickable-by-default.
- **Mobile / narrow-viewport rendering.** 4-pane fixed grid breaks below ~1280px; current dashboard reflows.
- **Storytelling / qualitative context.** No room for explanatory copy or sentiment-narrative widgets; the broker has to know how to read the screen.

---

## Direction 2 — "The Tape" (Ticker Bar + Tab Body)

**Elevator pitch:** A Bloomberg-style scrolling KPI ticker pinned to the top of every page; below it, traditional shadcn tab content. The ticker doubles as a live-event feed.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ ACME │ ◀ calls 47 ▲12% │ book 12 ▲33% │ margin +$4.2k ▲ │ flag 3 ▼ ▶ │  ← ticker (40px, scrolls)
├────────────────────────────────────────────────────────────────────────┤
│ LEFT RAIL  │  TAB CONTENT (Overview / Calls / Carriers / New Bookings) │
│ Overview   │  ────────────────────────────────────────────────────     │
│ Calls      │                                                            │
│ Carriers   │  Standard shadcn cards + tables + Recharts                │
│ Bookings   │                                                            │
│ ────────── │  Each tab is "normal" but inherits ticker context above   │
│ Date: ...  │                                                            │
│ Presets    │                                                            │
└────────────┴────────────────────────────────────────────────────────────┘
```

### 7 widget-pattern decisions

1. **Ticker bar (40px, sticky top, full-width)** scrolls horizontally via CSS `animation: marquee 60s linear infinite` (pauseable on hover). Items: `calls_today`, `bookings_today`, `margin_captured_today`, `booked_rate_pct`, `avg_listed_rate`, `avg_booked_rate`, `chs_avg`, `flagged_count`, `latency_p90` — each with delta-color and a 40-wide × 14-tall inline Recharts sparkline.
2. **Live-event interleaving:** every 10 seconds the ticker injects a one-line event ("BOOK · MC123456 · Dallas→Atlanta · +$340 margin · 14:32:08"). Events fade in green for wins, red for flagged. This makes the ticker a passive activity feed.
3. **Tab body** is conventional shadcn — Cards, Tables, Tabs. The visual departure is *only* the ticker. Below the fold the dashboard looks like Stripe.
4. **KPI cards (Overview tab)** use a "stat block" pattern: huge tabular-nums number, tiny target subscript ("/ tgt 10%"), 80×24 sparkline below, delta chip top-right. Identical layout as ticker items but at 5× size.
5. **Date filter** lives in the left rail, not inline in the page — global by design. Two `<input type="date">` and 6 preset buttons.
6. **Pause-on-hover with replay slider** — when the user hovers the ticker, scroll pauses and a 24h timeline appears above it; dragging the slider replays ticker state from any point in the day. Implementable with a controlled animation `state` and a vanilla `<input type="range">`.
7. **Color discipline:** ticker uses pure black background (`bg-black`) with green-400 / red-400 / slate-100 text — terminal aesthetic. Tab body stays the dashboard's existing slate-950 / slate-100 palette to keep visual grounding.

### Tab rendering

- **Overview** = ticker + 8 KPI stat-blocks in a 4×2 grid + the replacement central chart + a sentiment donut.
- **Calls** = ticker + filter bar + paginated calls table (existing) + drill-through drawer.
- **Carriers** = ticker + carrier leaderboard (table sorted by total margin captured) + carrier-detail drawer.
- **New Bookings** = ticker + a vertical timeline of today's bookings, newest-first, each as a card with margin pill + transcript-snippet preview.

### Replacement for "Margin Captured" central chart

**Stacked bar: listed vs booked, per-day.** Two bars per day: lighter slate for listed total, green-400 for booked total; the gap between them = margin captured. Broker reads "we listed $X, paid out $Y, kept $Z" at a glance. Recharts `<BarChart>` with two `<Bar>` series, dataKey grouped by day; tooltip shows margin delta and win-rate.

### Rationale (broker-as-trader)

The ticker mimics the always-on awareness of a CNBC chyron or a trading-desk wall display. A broker doesn't *open* the dashboard — they keep it open and glance. The ticker turns the dashboard from a destination into ambient peripheral vision: bookings tick by like trades on the tape, sparklines show short-term direction, flagged events flash. The traditional tab body below preserves discoverability and reuses the existing shadcn surface, so this is the lowest-disruption fintech reframe of the four directions.

### What this sacrifices vs current

- **Vertical real estate** — 40px ticker eats screen height permanently; on a 13" laptop that's 4% of viewport.
- **Scroll-jacking risk** — animated marquee can read as gimmicky if pause-on-hover is missed in implementation.
- **Performance budget** — sparkline-per-ticker-item × 9 items × re-render every 10s is non-trivial; Recharts will need memoization discipline.

---

## Direction 3 — "The Earnings Report" (P&L Summary Card)

**Elevator pitch:** A single hero number at the top of every page — today's margin captured, in 72px tabular-nums — with deltas vs MTD / YTD / Forecast. The rest of the page is breakdowns supporting that number.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  ACME LOGISTICS · CARRIER DESK                          [date filter]  │
├────────────┬───────────────────────────────────────────────────────────┤
│            │  ┌─────────────────────────────────────────────────────┐  │
│ LEFT RAIL  │  │  TODAY'S MARGIN CAPTURED                            │  │
│ Overview   │  │     +$4,217.50      ▲ 23% MTD  ▲ 18% YTD  ▼ vs fc   │  │
│ Calls      │  │  ▁▂▃▅▆▇▆▅▆▇▇▆▇▆ (60-min sparkline)                  │  │
│ Carriers   │  └─────────────────────────────────────────────────────┘  │
│ Bookings   │                                                            │
│            │  ┌─── 4-tile breakdown row ──────────────────────────┐    │
│ DATE       │  │ Calls │ Bookings │ Win-rate │ Avg margin/book   │    │
│ Presets    │  └────────────────────────────────────────────────────┘   │
│            │                                                            │
│            │  [Margin contribution waterfall by lane]                  │
│            │                                                            │
│            │  [Sentiment / quality narrative panel]                    │
└────────────┴────────────────────────────────────────────────────────────┘
```

### 7 widget-pattern decisions

1. **Hero card (full width, 200px tall, slate-900 bg, single border)** dominates the top half of the Overview tab. Primary number 72px, tabular-nums, font-bold; sign-colored (green if positive). Three delta chips in a row: vs MTD, vs YTD, vs forecast (forecast = trailing-30d average for same day-of-week).
2. **Inline 60-min sparkline** under the hero number is a Recharts `<AreaChart>` with `linearGradient` fill, no axes, no tooltip — pure shape. Reinforces "we are trending up/down right now."
3. **4-tile breakdown row** beneath: Calls / Bookings / Win-rate / Avg margin per booking. Each tile is the same hero pattern at 1/4 scale. Clicking a tile re-pivots the page beneath to that metric's breakdown.
4. **Margin contribution waterfall (Recharts BarChart with custom shapes)** breaks the hero number down by lane (top 8 lanes today + "other"). Each bar is positive (green) or negative (red, where booked > listed — broker lost). Visual answer to "where did today's margin come from?"
5. **Narrative panel** is text-heavy: a 2–3 sentence prose summary generated server-side ("Today you captured $4,217 across 12 bookings, 23% above this month's daily average. Atlanta lanes contributed 41% of margin; one flagged call on MC 123456 may need review."). Plain shadcn Card.
6. **Date filter is sticky top-right** rather than rail-bottom — because changing the date *redefines what "today" means* in the hero card, it deserves prominent placement. Two `<input type="date">` + presets in a horizontal strip.
7. **Color discipline:** the hero number is the *only* place a color this saturated appears on the page. Everything else stays muted slate. This forces the eye to the headline first.

### Tab rendering

- **Overview** = hero + breakdown row + waterfall + narrative.
- **Calls** = hero shows "CHS-weighted call quality score today"; breakdown row becomes Calls / Avg duration / Flagged / P90 latency; waterfall replaced by calls table.
- **Carriers** = hero shows "Top-carrier margin captured today"; breakdown row pivots to per-carrier leaderboard.
- **New Bookings** = hero shows "Bookings velocity (per hour)"; breakdown row shows hour-of-day distribution; waterfall shows lane breakdown of today's bookings only.

### Replacement for "Margin Captured" central chart

**Margin Contribution Waterfall.** A horizontal Recharts BarChart with custom positive/negative `<Bar>` shapes: one bar per lane (top 8 by absolute margin), starting from $0, stacking left-to-right cumulatively to today's total. Green bars push the cumulative line up; red bars push it down. Final bar is the hero number. Broker reads it as "Atlanta made me $1.4k, Dallas made me $900, Chicago lost me $200, …, total $4,217." This is exactly how an FP&A deck shows revenue contribution.

### Rationale (broker-as-trader)

Carta and Mercury both lead with a single hero number — your balance, your runway, your equity value — because in finance the *one* thing you want to know is "where do I stand right now." For an inbound-carrier-sales operation, the equivalent is "how much margin did I capture today." Anchoring every page to that number turns the dashboard into a P&L summary first and an analytics tool second, which is the right framing for an ops director or owner-broker who only checks in 3× per day. The waterfall is the financial-reporting standard for "explain a number" — it's the metaphor a CFO would draw on a whiteboard.

### What this sacrifices vs current

- **Multi-metric parity** — secondary metrics (latency, sentiment, CHS) get pushed below the fold; this dashboard is opinionated that *margin is the metric*.
- **Real-time feel** — no ticker, no live-event streaming visible on Overview; updates are reactive only when the user reloads or the date filter changes.
- **Discoverability of the calls/carriers tabs** — the Overview is so satisfying that users may never click into the other tabs.

---

## Direction 4 — "The Notebook" (Sigma SQL-Notebook / Query-First)

**Elevator pitch:** Every panel on the dashboard is a saved query rendered as a chart or table; users can fork, edit, and pin queries; the dashboard *is* a query catalog.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  ACME · CARRIER DESK              [+ New query] [Fork] [Pin] [date▾]  │
├──────────────┬─────────────────────────────────────────────────────────┤
│              │  Pinned panel grid (2-col masonry, drag-resizable)      │
│ LEFT RAIL    │  ┌──────────────────┐  ┌──────────────────┐            │
│ ─────────    │  │ q_margin_today   │  │ q_calls_funnel   │            │
│ ▼ My panels  │  │ [chart preview]  │  │ [table preview]  │            │
│   margin     │  │ ▷ inspect SQL    │  │ ▷ inspect SQL    │            │
│   funnel     │  └──────────────────┘  └──────────────────┘            │
│   flagged    │  ┌──────────────────┐  ┌──────────────────┐            │
│ ▼ Catalog    │  │ q_top_carriers   │  │ q_lane_margin    │            │
│   bookings   │  │ [chart preview]  │  │ [waterfall]      │            │
│   carriers   │  └──────────────────┘  └──────────────────┘            │
│ ▼ Recent     │                                                          │
│              │                                                          │
│ DATE / PRESET│                                                          │
└──────────────┴─────────────────────────────────────────────────────────┘
```

### 7 widget-pattern decisions

1. **Every panel is a "query card"** with a fixed header strip: query slug (`q_margin_today`), timestamp of last refresh, "▷ inspect" caret. Clicking the caret slides the card aside and reveals a read-only SQL pane below with the underlying query (since we use HR Twin via the `/twin/sql` proxy, the SQL is genuinely the source of truth).
2. **Left rail is a query catalog**, not a tab list. Three collapsible sections: My Pinned, Catalog (curated by Acme), Recent. Each query has a kebab menu: Fork / Pin / Open in inspector. Hotkey Cmd+K opens fuzzy search across all queries.
3. **"Fork" creates a copy** of the SQL with an editable text area (vanilla `<textarea>`, no Monaco — keeps the dependency footprint clean) and an inline "Run" button. Resulting rows render below as either a Recharts chart (auto-detected from result shape) or a shadcn Table.
4. **Tabs are virtual collections**, not hardcoded routes. "Overview" is a curated set of 6 pinned queries; "Calls" is a different set of 4; "Carriers" / "New Bookings" the same. Editable by an admin user.
5. **Inline param chips** — every query exposes its `:param` placeholders as small chips above the chart (e.g. `:start_date = 2026-04-23`, `:lane = ANY`). Clicking a chip opens a dropdown to change the value; query reruns. Like Sigma / Hex.
6. **Last-refresh badge** on every panel: green if <30s old, amber 30s–5m, red >5m. Reuses the existing `cachetools.TTLCache(30s)` boundary as the freshness signal.
7. **Color discipline:** treat the dashboard as a developer tool — slate-950 bg, monospace for SQL, Inter for chart labels; no decorative gradients; charts use a fixed 6-color categorical palette (one per top lane). Numbers are tabular-nums everywhere.

### Tab rendering

- **Overview** = 6 pinned queries (margin today, calls funnel, top carriers, lane margin, sentiment dist, CHS dist) in a 2-col masonry.
- **Calls** = 4 queries (calls table, calls per hour, flagged calls, duration histogram) — calls table query has full search/sort/filter as URL params.
- **Carriers** = 3 queries (carrier leaderboard, MC retention curve, lane × carrier matrix heatmap).
- **New Bookings** = 2 queries (today's bookings table, today's bookings hour-of-day) + a "fork to investigate" affordance pinned at top.

### Replacement for "Margin Captured" central chart

**Lane × Time-of-day Margin Heatmap.** A 2D Recharts-based grid (rendered as a custom `<BarChart>` matrix or via SVG primitives) — rows = top 10 lanes, columns = hours of the day, cell color = avg margin captured (green-scale positive, red-scale negative), cell label = booking count. The query behind it is exposed as `q_lane_hour_heatmap` and forkable. Brokers spot patterns: "Atlanta lanes margin best between 10am–2pm; Chicago lanes are negative-margin after 4pm — stop bidding."

### Rationale (broker-as-trader)

Quant desks and analytics-first finance shops (Stripe Sigma, Hex, Sigma Computing, the Bloomberg `<GO>` command surface) reject pre-baked dashboards because the question changes every day. Exposing every panel as a query makes the dashboard *a Bloomberg `<GO>` for freight* — the broker (or their analyst) can fork "show me margin" into "show me margin only on Atlanta-origin loads booked between 10am and 2pm" without filing a JIRA. For a 3-person ops team that already runs the negotiations themselves, the willingness to look at SQL is high; for them, this is the highest-ceiling design.

### What this sacrifices vs current

- **Aesthetic warmth** — looks like a developer tool, not a customer-facing product. Acme's executive sponsor may bounce off it on demo day.
- **Onboarding cost** — non-technical users who can't read SQL won't fork, which collapses the design back to "a dashboard with extra steps."
- **Implementation cost** — query-as-component requires a small framework (query registry + auto-chart-from-shape detector) that doesn't exist today; ~1 day of Claude-time before any panel renders.

---

## Comparison snapshot

| Direction | Hero metaphor | Density | Best for | Worst for |
|---|---|---|---|---|
| 1. The Pit | Bloomberg terminal | Highest | Power users running live calls | Demo / first-time viewers |
| 2. The Tape | Trading-floor ticker | Medium | Always-on ops dashboard | Mobile / narrow screens |
| 3. The Earnings Report | Mercury hero card | Lowest | Owner-broker checking in 3×/day | Multi-metric exploration |
| 4. The Notebook | Stripe Sigma / Hex | Medium-high | Analyst forking ad-hoc questions | Non-technical executives |

## Notes on implementability

All four directions are achievable inside the current stack (Next 15, Tailwind 4, shadcn/Radix-Tooltip-Tabs-Select-Separator-Slot, Recharts, Lucide, vanilla `useSearchParams`). None require Tremor, nuqs, react-day-picker, date-fns, or `@radix-ui/react-popover` to ship a v1 — date filters use two `<input type="date">` per ADR-011, sparklines use bare Recharts `<AreaChart>`, delta chips use `<span>` + Lucide `TrendingUp/Down`, dropdowns use `useState` + click-outside `useEffect`. The Notebook direction (D4) needs the most new infrastructure (query registry, SQL inspector pane, fork-to-textarea); the others are layout-and-styling exercises on top of the existing component library.

## Cross-direction shared elements

Regardless of which direction is picked, these primitives carry over:

- **Tabular-nums everywhere** (`font-variant-numeric: tabular-nums`) — non-negotiable for any fintech reframe.
- **Consistent margin sign convention** — `margin = listed − booked`, positive = broker won, green up / red down.
- **Target-vs-actual framing** on every KPI (`actual / tgt X`) — captures the user's stated requirement.
- **Sticky global date filter** with preset buttons (1D / 7D / 30D / MTD / QTD / YTD).
- **Left-rail navigation** (Overview / Calls / Carriers / New Bookings).
- **Two `<input type="date">`** for the date range (no calendar control, per ADR-011).
- **Lucide icons only** — `TrendingUp`, `TrendingDown`, `AlertTriangle`, `Activity`, `DollarSign`. No icon library swap.
- **Slate-950 background, slate-100 foreground**, green-400 / red-400 / amber-400 semantic accents.

## Recommendation for parent agent

If forced to pick one without further user input, **D2 (The Tape)** is the lowest-disruption / highest-fintech-aesthetic-payoff direction: the existing dashboard surface stays largely intact below the fold, the ticker is the only new component, and the broker-as-trader metaphor is delivered visibly within the first second of viewing the page. **D3 (The Earnings Report)** is the strongest demo-day choice — a single 72px green number is a screenshot that wins meetings. **D1 (The Pit)** is the most differentiated product and the best fit for a daily-driver power user, but loses on demo-day legibility. **D4 (The Notebook)** is the highest-ceiling but highest-cost; queue as Tier-3 if a future analyst persona is identified.
