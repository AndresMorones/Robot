# Dashboard v2 — Interaction Patterns (Power BI / Salesforce / Tableau grade)

## 1. The Power BI / Tableau / Salesforce interaction inventory

| Pattern | Description |
|---|---|
| **Cross-filter** | Click slice in chart A → every other visual on page filters to that subset |
| **Drill-down** | Click bar (month) → expand into next-level breakdown (week/day/hour) in same chart |
| **Drill-through** | Right-click row → navigate to fully separate page already filtered to that entity |
| **Linked highlighting** | Hover scatter point → corresponding rows in sibling table glow |
| **Slicers** | Persistent filter widgets at page top; affect every visual on page |
| **Conditional formatting** | Cells in table tinted by value (heat / RAG / data bars) |
| **Bookmarks** | Save filter+selection+sort state, reload it. URL state IS the bookmark |
| **Pivot/unpivot** | Switch row-grouping in tables without re-querying |
| **Rich tooltips** | Mini panel with multiple metrics, sparkline, sometimes linked button |
| **Sort/filter/pin/group/freeze columns** | Native to all three. Pin column = freeze leftmost |
| **Export** | CSV / PDF / PNG / image |
| **Synchronous updates** | Every visual on page redraws together |
| **Tab/page-level filter scope** | Power BI: report-level / page-level / visual-level |

## 2. Pattern → Next.js implementation map

### 2.1 Cross-filter
**State:** Zustand store + URL sync via `nuqs`. Zustand owns runtime; nuqs reflects to `?from=…&outcome=…`.
**Charts subscribe** via `useFilterStore((s) => s.compositeFilter)`. Selectors prevent re-renders.
**Race conditions:** atomic Zustand mutations; `useTransition` for batching; `AbortController` keyed by filter hash.
**Library:** `npm i zustand nuqs` (~3 KB + ~5 KB gz).
**Complexity:** **M** for wire-up; XS thereafter.

### 2.2 Drill-down
**In-place expansion** for same-shape (month → weeks). **Route navigation** for different-grain (call → transcript).
**Library:** TanStack Table v8 (`getExpandedRowModel` + `row.getCanExpand()`).
**Complexity:** **S** for table; **M** for chart.

### 2.3 Drill-through
**Routes:** `app/dashboard/calls/[call_id]/page.tsx`, `carriers/[mc]/page.tsx`, `loads/[load_id]/page.tsx`.
**Pre-fetch:** `<Link prefetch>`.
**Complexity:** **S** per detail page.

### 2.4 Linked highlighting
**Approach:** lift "active id" to Zustand slice (`hoveredId: string | null`).
**Performance with 1000+ rows:** `React.memo` keyed on `(row.id, hoveredId === row.id)`; `@tanstack/react-virtual` mounts only ~30 visible rows.
**Complexity:** **S**.

### 2.5 Slicers
**Components:** shadcn `Select`, `Combobox`, `Calendar`, `MultiSelect`.
**Where:** sticky header bar.
**Persistence:** `nuqs` writes to URL.
**Complexity:** **M** for global bar; **S** per per-chart override.

### 2.6 Conditional formatting
**TanStack Table** `cell` render function returns `<div>` with style derived from value.
**Color scales:** `culori` (modern, OKLCH support, tree-shakable) over chroma-js.
**A11y:** never colour-only; add icon + sign.
**Library:** `npm i culori` (~12 KB tree-shaken).
**Complexity:** **S**.

### 2.7 Bookmarks
**URL state IS the bookmark.** Every filter + sort + drill state via `nuqs`.
**"Copy view" button:** `navigator.clipboard.writeText(window.location.href)` + toast.
**Saved named views:** localStorage map `name → URL`.
**Complexity:** **XS**.

### 2.8 Rich tooltips
**Recharts custom Tooltip:** `<Tooltip content={<MyTooltip />} />` renders any JSX.
**Mini sparklines via Recharts** inside tooltip.
**Floating UI** only if needed beyond Recharts.
**Complexity:** **S** first; **XS** thereafter.

### 2.9 Pivot / sortable / groupable tables
**TanStack Table v8** with row models opt-in:
- `getCoreRowModel`, `getSortedRowModel`, `getFilteredRowModel`, `getGroupedRowModel`, `getExpandedRowModel`, `getPaginationRowModel`
- Headless: integrates with shadcn `<Table>` primitives
- Pivot via `getGroupedRowModel` + `groupingState`; combine with `@dnd-kit/core` for "drag column to group"

**Comparison:** MUI X DataGrid Premium (~$15/dev/mo, MUI clash with Tailwind) — Reject. ag-Grid Enterprise (commercial) — Reject. **TanStack** is free + Tailwind-pure.
**Complexity:** **M** first; **S** thereafter.

### 2.10 Export
- **CSV:** `papaparse` — `Papa.unparse(rows)` then Blob + `<a download>`.
- **PDF:** `@react-pdf/renderer` (slow, ~250KB) or `html-to-image` → canvas → jsPDF.
- **PNG:** `html-to-image` directly.
**MVP:** ship CSV + PNG; defer PDF.
**Complexity:** **XS** each.

## 3. Component library deep-dive

| Library | Strengths | Weaknesses | License | Recommendation |
|---|---|---|---|---|
| **shadcn/ui** | Radix primitives, Tailwind-native | No data grid, no chart system | MIT | **Keep as foundation** |
| **Recharts** | Declarative, React-friendly | Limited types; brush basic; large datasets jank >3k pts | MIT | **Keep for simple charts** |
| **Tremor** | Built on Recharts, dashboard primitives, Tailwind-native | Overlap with shadcn | Apache 2.0 | **Adopt** (KPI cards, sparklines) |
| **TanStack Table v8** | Headless, every feature flagged | DIY rendering | MIT | **Adopt** for every table |
| **Apache ECharts** | 30+ chart types, brush-zoom built-in | ~150 KB per chart tree-shaken; imperative API | Apache 2.0 | **Lazy-load** for advanced viz only |
| **Visx** | D3 power | More code per chart | MIT | Skip unless ceiling |
| **MUI X DataGrid Free** | Solid table | MUI runtime + Tailwind clash | MIT | Reject |
| **ag-Grid Community** | Best-in-class table | Pivot is Enterprise | LGPL | Reject |
| **Framer Motion** | First-class React animation | ~60 KB | MIT | **Adopt** for transitions |

### Final stack recommendation

| Library | Bundle gz |
|---|---|
| Tremor | +25 KB |
| TanStack Table v8 | +14 KB |
| Zustand | +3 KB |
| nuqs | +5 KB |
| Framer Motion | +60 KB |
| culori | +6 KB |
| papaparse | +12 KB |
| html-to-image | +9 KB |
| ECharts (lazy) | 0 first paint, ~150 KB on demand |

**Total first-paint add: ~134 KB gz.**

## 4. State management for cross-filtering

### 4.1 Why Zustand
- Selector subscriptions (only rerenders subscribers whose slice changed).
- No provider boilerplate.
- Middleware (`subscribeWithSelector`, `persist`) for Tier-2 saved views.
- React 19 compatible.

### 4.2 Why not Context only
Every consumer rerenders on any change.

### 4.3 Why not URL-only
Verbose, no place for hover state, browser URL limits.

### 4.4 Cross-filter pattern
1. Chart A's `onClick(slice)` → `setOutcome(slice.outcome)`.
2. Zustand fires; subscribers re-read composite filter.
3. Each subscriber: Client Component wrapping Server-rendered child via `<ServerChart filter={filter} />`.
4. Server Action hits FastAPI with `nuqs`-encoded filter; FastAPI hits TTL cache.
5. While in flight, `useTransition` keeps old chart at 50% opacity (Framer `AnimatePresence`).

### 4.5 Server Components composition
Charts must be Client (Recharts uses refs). Surround with thin Server Components owning **default** filter from URL on first render. Client store **rehydrates from URL** on mount via `nuqs`.

### 4.6 nuqs syncing
Each filter key has parser (`parseAsString`, `parseAsIsoDate`, `parseAsArrayOf(parseAsString)`).
Date pickers debounced (`shallow: false, throttleMs: 300`).
Back-button: replace, not push, on intermediate keystrokes.

### 4.7 Conflict resolution
- Different dimensions: AND.
- Multiple values within same dimension: OR.
- Encode on FastAPI side as `(outcome = ? OR outcome = ?)` (since `IN` is WAF-blocked).

### 4.8 Code sketch
```tsx
type FilterState = {
  dateRange: { from: Date; to: Date };
  outcome: Outcome[] | null;
  sentiment: Sentiment[] | null;
  mc: string | null;
  hoveredId: string | null;
  // …setters…
};
const filterStore = create<FilterState>((set) => ({ /*…defaults + actions…*/ }));
const useDateRange = () => filterStore((s) => s.dateRange);
```

## 5. Layered animation + polish

| Polish | Library |
|---|---|
| Chart transition on filter change | Framer Motion `AnimatePresence` |
| Animated number counters | Framer `useMotionValue` + `useTransform` (or Tremor `<Metric>`) |
| Skeleton states | shadcn `<Skeleton>` |
| Hover lifts on cards | Tailwind: `transition-shadow hover:shadow-lg hover:-translate-y-0.5` |
| Side drawer on row click | `vaul` (drag-to-dismiss) or shadcn `<Sheet>` |
| Top loading bar | `@bprogress/next` or 30-line custom hook |
| Toast notifications | `sonner` |
| Tab switch transitions | Framer `LayoutGroup` + `motion.div` with `layoutId` |
| Empty/error states | Hand-drawn SVGs from undraw.co |

**Net library adds:** `framer-motion`, `sonner`, `vaul` (~5 KB each). All MIT.

## 6. Performance for interactive dashboards

| Trap | Mitigation |
|---|---|
| Recharts re-render on >1k points | Sample/bucket on API side; `isAnimationActive={false}`; memoise data |
| TanStack Table on 10k+ rows | `@tanstack/react-virtual` |
| Server fetches on every keystroke | Debounce 300ms; URL writes throttled |
| Re-render cascades | Zustand selectors with shallow equality |
| Server fetches racing | `AbortController` per-chart |
| Tab switch refetches | Parallel route segments + their own `loading.tsx` |
| Hydration mismatch on dates | `Intl.DateTimeFormat` with explicit `timeZone` |

**React 19 levers:** `useDeferredValue`, `use(promise)`, React Compiler auto-memoization.

**Server-side:** TTLCache keyed by canonical filter hash (ordering-insensitive); pre-warm "default filter" (last 7 days) in background.

## 7. Five demo-able interactions

If reviewer watches 2-min walkthrough:

1. **Click slice on Outcome pie → all KPI cards, line chart, table, sentiment pie filter to that outcome in <100ms.** Cyan ring animates around clicked slice.
2. **Drag date-range brush on calls-per-hour line → KPI strip updates live; URL updates to `?from=…&to=…`.** Release → "Bookmark this view" button glows.
3. **Click row in Calls table → side drawer slides in from right with full transcript, CHS gauge, sentiment timeline, "Open call page →" link.** Dismissible Esc/click-out/drag-down.
4. **Hover state on US lane heatmap → tooltip with mini origin→dest flow + sparkline; loads-table rows for that state highlight cyan, others soften 40%.**
5. **Click carrier in carrier rollup → drill-through to `/dashboard/carriers/[mc]` with global filter preserved; breadcrumb; back button restores prior scroll.**

These hit cross-filter, brushing, drill-down, drill-through, rich tooltip, URL state, drawer micro-interaction, breadcrumb.

## 8. Implementation effort matrix

| Pattern | Time | MVP/Tier-2 |
|---|---|---|
| Cross-filter (Zustand+nuqs) | M | **MVP** |
| Drill-down (in-place chart) | M | **MVP** for tabs; Tier-2 for chart drill |
| Drill-through (route nav) | M | **MVP** for calls+carriers; Tier-2 for loads |
| Linked highlighting | S | **MVP** for table↔chart pair |
| Slicers (global filter bar) | M | **MVP** |
| Conditional formatting | S | **MVP** (CHS, deltas) |
| Bookmarks (URL state) | XS | **MVP** |
| Saved named views (localStorage) | S | **Tier-2** |
| Rich tooltips | S each | **MVP** for top 3; Tier-2 for rest |
| Pivot table | L | **Tier-2** |
| Sortable/filterable/pinnable columns | M (first) + S each | **MVP** |
| CSV export | XS each | **MVP** |
| PNG export | XS each | **MVP** |
| PDF export | M | **Tier-2** |
| Animated number counters | XS | **MVP** |
| Side drawer for row details | S | **MVP** |
| Top-bar route loading | XS | **MVP** |
| Tab pill slide animation | XS | **MVP** |
| US lane heatmap (ECharts) | M | **Tier-2** |
| Sankey of call flow | M | **Tier-2** |
| Pre-fetch on hover | XS | **MVP** |
| Active-call live indicator | M | **MVP** |

## Final report

### Top 5 demo-able interactions to ship first
1. Cross-filter on Outcome pie click.
2. Date-range brush on calls-per-hour with live KPI update.
3. Side drawer with call transcript on row click.
4. Linked highlighting between US heatmap and loads table.
5. Drill-through to `/dashboard/carriers/[mc]` with breadcrumb + filter persistence.

### Three patterns to defer to Tier-2
1. **Pivot table with column drag-to-group** — high cost, low daily-driver value.
2. **PDF export with branded templates** — `@react-pdf/renderer` is 250KB liability.
3. **Saved named views** — URL-as-bookmark already gives shareable.

### One thing the user might think they want but shouldn't ship
**A "Pin to home" / customisable widget grid layout** (Salesforce / Power BI "Pin to dashboard"). Looks impressive in screenshot, requires `react-grid-layout` + per-user persistence + widget registry. Build well-curated tabs per persona instead.
