# Dashboard v2 — Animation Polish + Acme Operational Scenarios

**Note:** Empty-state copy is in `05-branding-design-tokens.md` §8-9. Animation primitives are in `06-interaction-patterns.md` §5. This doc focuses on the deltas: 30 micro-interactions catalog, 5 Acme scenarios, Loom magic moments, "first 5 seconds" sequence.

## 1. The 30 micro-interactions

| # | Interaction | Library | Complexity | Demo-impact |
|---|---|---|---|---|
| 1 | KPI number animates from previous to new | Framer `useMotionValue` / Tremor `Metric` | XS | 5 |
| 2 | Pie slice expands slightly on hover with soft shadow | Recharts `onMouseEnter` + transform | XS | 4 |
| 3 | Tab change has 150ms fade between contents | Framer `AnimatePresence mode="wait"` | XS | 3 |
| 4 | Filter pill removal: scale 0.8 + fade + slide out | Framer variants | XS | 4 |
| 5 | Chart axis ticks animate when range changes | Recharts default + `isAnimationActive` | XS | 3 |
| 6 | Sortable column header arrow rotates on click | TanStack Table + Tailwind transition | XS | 4 |
| 7 | Row click → side drawer slides in | vaul or shadcn Sheet | S | 5 |
| 8 | Skeleton shimmer matches final layout | shadcn Skeleton | XS | 3 |
| 9 | Hover on bar chart shows vertical guide line | Recharts CartesianGrid + ReferenceLine | XS | 3 |
| 10 | Time-series brush has drag-handle affordance | Recharts Brush + custom thumb | S | 4 |
| 11 | Empty state with illustration + helpful action | undraw.co SVGs | S | 3 |
| 12 | Toast on action: top-right slide-in 4s | sonner | XS | 3 |
| 13 | Save bookmark: success toast with "View saved" link | sonner | XS | 4 |
| 14 | Click-to-copy URL: button morphs to checkmark | Tailwind transition + state | XS | 4 |
| 15 | Date range preset chip click: bounce + highlight | Framer spring | XS | 3 |
| 16 | Live indicator: gentle pulse synced with breath rhythm | CSS keyframes | XS | 5 |
| 17 | Chart legend hover: corresponding series brightens | Recharts onMouseEnter + opacity | XS | 4 |
| 18 | Keyboard nav: focus ring with high contrast + depth | Tailwind focus-visible:ring | XS | 3 |
| 19 | Drilldown: breadcrumb appears, parent animates left | Framer AnimatePresence | S | 4 |
| 20 | Resize: charts redraw smoothly (debounced 300ms) | Recharts ResponsiveContainer | XS | 2 |
| 21 | Initial load: header → KPIs cascade 100ms apart | Framer stagger children | S | 5 |
| 22 | Error: shake animation + clear error message | Framer + variants | XS | 3 |
| 23 | Refresh data: subtle "refreshing" indicator near logo | Framer pulse | XS | 3 |
| 24 | Filter combobox open: flips up if not enough room | Floating UI auto-placement | XS | 3 |
| 25 | Range slider thumb: micro-shadow on drag | Tailwind active: + shadow-md | XS | 2 |
| 26 | Column drag (TanStack): ghost preview follows cursor | @dnd-kit/core | M | 4 |
| 27 | Form submit: button fills with progress | Framer scale + Tailwind | S | 3 |
| 28 | Mobile: pull-to-refresh on overview | Framer drag + threshold | M | 3 |
| 29 | Theme toggle: smooth color transition | Tailwind transition-colors | XS | 4 |
| 30 | Idle state: ambient fade-in/out of "Last synced X ago" | Framer infinite repeat | XS | 4 |

**Top 5 ranked by demo-impact:**
1. KPI number count-up animation (#1)
2. Side drawer slide-in on row click (#7)
3. Live indicator breath-pulse (#16)
4. Initial load KPI cascade (#21)
5. Theme toggle smooth transition (#29)

## 2. Acme Logistics scenarios

### Scenario 1: Monday morning standup (broker owner)

Sarah opens dashboard at 8:30 AM Monday. Lands on Pulse. KPI strip shows: **47 bookings last week, +18% vs prior week** with green delta arrow. Hero chart shows effective rate delta time series. She clicks the bookings sparkline → drills into time series with brush slider; brushes to "last 7 days" → sees Wednesday spike. Hovers Wednesday bar → tooltip: "14 bookings, mostly Dallas-Atlanta corridor". Clicks bar → drills to lane detail page (`/dashboard/lanes/TX-GA-Reefer?from=2026-04-22&to=2026-04-29`). Sees 3 repeat carriers drove the spike. Closes dashboard, walks into standup, says: "Wednesday's Dallas-Atlanta spike was driven by our preferred carriers — let's keep that lane warm."

**Features exercised:** date filter, time-series brush, drill-through, lane detail page, repeat-carrier identification.

### Scenario 2: Live call coverage (dispatch lead)

Mike sees the live indicator pulse green — `● Live · 2 active`. Clicks it. Slide-over panel shows two in-progress calls: MC 999384 in Lane TX→GA, 02:14 elapsed; MC 444112 still under 1 min, just verified MC. He stays on the page; 30 seconds later the first call ends — webhook fires, dashboard auto-refreshes. The Last 5 calls tile updates: a new "BOOKED" entry appears at top with green outcome badge, fade-in animation. Mike notices CHS=85, sentiment=positive — knows it was a clean call. Goes back to whatever he was doing.

**Features exercised:** active-call detection, SSE auto-refresh, last-5-calls rolling tile, outcome badge, CHS display.

### Scenario 3: Quality regression triage (FDE)

After production push of v15 prompt, Jamie checks Quality tab on Friday afternoon. Sees CHS distribution histogram has shifted — bucket "60-80" grew, "80-100" shrunk vs last week. Alert banner at top: "CHS Decay: avg dropped from 82 to 74 over last 7 days". Clicks alert → filtered to low-CHS calls (CHS < 70) in transcript review queue. Opens 3 calls in sequence. Each shows a transcript section where agent stalled on FMCSA decline. Pattern recognized — file an issue + revert prompt.

**Features exercised:** CHS distribution, week-over-week comparison, alert banner, transcript-review queue, transcript drilldown.

### Scenario 4: Carrier follow-up (sales rep)

Tuesday morning, Anna pulls up Carriers tab. Filters by "stale" (Repeat Carriers gone quiet >21d). Sees 4 MCs flagged. Clicks the top one — MC 222019 — drills to carrier detail. Their history shows 8 prior bookings, last call 28 days ago, average rate $2,150 (above-market). She copies their callback phone, dials, says "Hey, we miss you — got a load you'd love." Books one before lunch.

**Features exercised:** stale-carrier filter, carrier detail page, history table, callback contact info.

### Scenario 5: Revenue review (finance)

End of month, Carlos opens Economics tab. Time horizon toggle → "1m". Effective rate delta time series shows mostly green (we held the line). Clicks Top 10 Carriers ranked-by-revenue. Sees MC 148373 = $47,200 booked across 14 calls. Clicks them → carrier detail → exports CSV of their bookings → drops in monthly review deck.

**Features exercised:** time-horizon toggle, effective rate delta, top-N ranking, drill-through, CSV export.

## 3. Demo "magic moments" for the Loom

5 specific moments that on camera will make a reviewer say "this is production-ready":

1. **Live call ends mid-recording, dashboard auto-updates without F5.** Live indicator was at 1; webhook fires; the count drops, last-5-calls table animates in a new row at top, KPI cards recompute with count-up animation. Carlos watches it happen passively — proves SSE + webhook + cache invalidation work end-to-end.

2. **Click an outcome slice → all charts on the page filter in sub-100ms.** Pie slice highlights with cyan ring; line chart fades + redraws filtered; KPI cards show new numbers; URL bar updates with `?outcome=load_booked`. The cross-filter is the single most "Power BI" moment.

3. **Hover a US state on the lane heatmap → tooltip with mini origin→destination flow + sparkline; loads-table rows for that state highlight.** Linked highlighting between geo viz and tabular data sells the "production analytics tool" story.

4. **Click a row in calls table → side drawer slides in from right with full transcript, CHS gauge, sentiment timeline, "Open call page →" link.** Dismissible Esc/click-out/drag-down (vaul). Tells the "drilldown is rich" story without leaving the page.

5. **Copy bookmark URL → paste in second browser → dashboard reproduces exactly.** Filters, drill state, view configuration all encoded in URL. URL-as-bookmark is something Power BI Embedded doesn't even do as well.

## 4. Empty/loading/error state copy library

Already covered in `05-branding-design-tokens.md` §8-9 — refer there.

Tone summary: short, factual, never apologetic. Suggest action only when one exists. Never mention `Twin`, `calls_log`, `webhook`, `FastAPI`. Never "We have not received any data" (passive). Always operational voice.

## 5. Acme persona ribbon

| Surface | Copy |
|---|---|
| Header | `Acme Logistics · Carrier Operations` |
| Sub-header (Pulse) | `Inbound desk · today` |
| Sub-header (Conversion) | `Funnel · last 7 days` |
| Sub-header (Economics) | `Revenue · last 7 days` |
| Sub-header (Lanes) | `Lane analytics · last 30 days` |
| Sub-header (Carriers) | `Carrier directory · ranked by value` |
| Sub-header (Quality) | `Quality · last 7 days` |
| Sub-header (System) | `System health` |
| Footer | `● Online · Last sync 12s ago · v0.4.2 · Powered by HappyRobot` |
| Browser title | `${tab} — Acme Logistics` |
| 404 | `Lane not found · go back to overview` |
| 500 | `Operations briefly unavailable · refresh in a moment` |
| Maintenance | `Scheduled maintenance · back at 14:00 UTC` |

## 6. Mobile + tablet polish

| Behavior | Details |
|---|---|
| Bottom-tab nav (<md) | Replaces side nav; icons + labels; active tab has top accent bar |
| Swipe between tabs | Framer `drag="x"` with snap thresholds |
| Pull-to-refresh on overview | Custom Framer drag + threshold + ResponsiveContainer redraw |
| Long-press for row actions | `onPointerDown` + 500ms timer → context menu |
| Haptic feedback | `navigator.vibrate(10)` on filter apply (where supported) |
| Larger touch targets | All buttons ≥ 44×44px on mobile |
| Stacked KPI cards in single column (xs) | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` |
| Chart simplifications | Sankey → stacked horizontal bar; calendar heatmap → bar of "calls per hour today"; histograms reduced to 10 bins |

## 7. The "first 5 seconds" sequence

| Time | What happens |
|---|---|
| 0ms | Blank canvas (avoid jarring white flash) |
| 50ms | Header + nav appear (instant, server-rendered) |
| 100ms | Skeleton KPIs render with shimmer |
| 300-800ms | First data arrives, KPIs animate in via Framer count-up |
| 800-1200ms | Charts render with subtle 100ms stagger between cards |
| 1500ms | Live indicator activates if active call detected |
| 2000ms | "Last sync" timestamp starts auto-updating |

**Default landing tab:** Pulse (broker owner / dispatch glance).
**Initial filter:** last 7 days (per locked answer #2).
**No flash of wrong data:** Server Components render with URL filter applied → no client-side fetch waterfall.

## 8. The 3 things to demo first

If you only have 30 seconds:

1. **Live call ending → dashboard auto-updates.** Sells the "real-time + production-grade" story. Webhook + SSE + cache invalidation in one moment.

2. **Cross-filter on a pie slice click.** Sells the "Power BI / Salesforce-grade interactivity" story. Sub-100ms response, multiple charts respond, URL updates.

3. **Drill-through to carrier detail with breadcrumb + filter persistence.** Sells the "deep, navigable analytics" story. Real Next.js routes, real bookmarks, back button works.

These three together cover: real-time, interactive filtering, deep drilldown. The complete production-grade analytics promise in 30 seconds.

## Final summary

- **Top 5 micro-interactions ranked by demo-impact:** KPI count-up (#1), side drawer slide-in (#7), live indicator pulse (#16), initial load KPI cascade (#21), theme toggle (#29).
- **Top 3 magic moments for Loom:** live call auto-update, cross-filter on pie click, drill-through with breadcrumb + filter persistence.
- **Recommended copy palette tone (1 sentence):** Terse + operational + impersonal + never-apologetic; active voice, no internals, two-word KPI labels max.
- **Total polish-implementation estimate:** ~12-15 Claude hours across all 30 micro-interactions + 5 scenario flows + framer/sonner/vaul integration.
