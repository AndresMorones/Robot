# Dashboard v2 — Visualization & Design Language

Sub-agent: Visualization specialist. Output for parent synthesis.

## 1. Design language for freight ops

A freight operations console is not a SaaS marketing dashboard. It runs in a physical office with a noisy radio in the background, on a 27-inch monitor from 9 a.m. to 6 p.m., and the dispatcher next to the broker glances at it sideways while on a call. The visual job-to-be-done is "tell me at a glance whether things are normal or off, and let me drill in three clicks."

Reference points: McLeod LoadMaster's dense form-and-grid layout, Trimble TMS's color-coded load board, DispatchTrack's stop-by-stop card timeline, SONAR / FreightWaves dashboards. NOT chasing: Stripe / Linear marketing-page polish, gradient hero cards, full-bleed photography.

### Color palette options

**Option A — "Dark ops console" (recommended).** Reads like a TMS / NOC. Tokens:

| Token | Role | Hex |
|---|---|---|
| `--bg-canvas` | Page background | `#0B1220` |
| `--bg-surface` | Card surface | `#111827` |
| `--bg-surface-2` | Nested / table row hover | `#1F2937` |
| `--border-subtle` | Card + divider borders | `#1F2A3D` |
| `--text-primary` | Primary copy + numerics | `#E5E7EB` |
| `--text-secondary` | Labels, axis ticks | `#94A3B8` |
| `--text-muted` | Legend, hints | `#64748B` |
| `--accent-primary` | Acme brand, KPIs at rest | `#3B82F6` |
| `--success` | Booked, rate accepted | `#22C55E` |
| `--warning` | At-risk, pending | `#F59E0B` |
| `--danger` | FMCSA decline, regression | `#EF4444` |
| `--info` | Sentiment-positive | `#06B6D4` |
| `--live` | Active call pulse | `#10B981` |

**Option B — "Light editorial" (alt).** Background `#F8FAFC`, surface `#FFFFFF`, border `#E2E8F0`, primary text `#0F172A`, accent `#2563EB`, status colors one shade darker.

**Recommendation:** Option A default; Option B as toggle.

### Typography

- **Numerals:** monospace, tabular (`JetBrains Mono` or `Geist Mono` + `font-feature-settings: "tnum"`). Apply to every number including axis ticks.
- **Labels + body:** `Geist` or `Inter`.
- **Sizing scale (1.25 modular):** xs 11, sm 12, base 14, md 16, lg 20, xl 24, 2xl 32, 3xl 44, 4xl 60.
- **Weights:** 400 body, 500 labels, 600 numerics + headers. No 700+.

### Spacing — 8px ops density

8px grid. Card padding 16px mobile / 24px desktop / 16px on dense tables. Card gap 16px. Table row 36px default, 32px dense. Numeric columns right-aligned.

### Iconography (lucide-react)

| Icon | Use |
|---|---|
| `Truck` | Carrier-side |
| `Package` | Loads |
| `Route` / `MapPin` | Lane |
| `PhoneCall` | Calls |
| `BadgeCheck` | FMCSA passed |
| `ShieldAlert` | FMCSA declined |
| `TrendingUp/Down` | Comparison delta |
| `Activity` | Live indicator |

One icon per card max, top-right at 16×16, color `--text-muted`.

## 2. Comparison indicator patterns

### Pattern A — Inline delta (default)

```
12,847 calls            ▲ 4.3%   vs yesterday
                        ◯ 92%    of target (14k)
```

Two stacked one-line comparisons. Arrow encodes direction; color encodes good/bad. Target as ring percentage.

### Pattern B — Sparkline with target line

30-period sparkline with horizontal dashed target line. Current point colored by status.

### Pattern C — Bullet chart (Stephen Few)

Horizontal track with target tick, performance bar, gray "poor/OK/good" bands.

**Default: Pattern A everywhere; Pattern B on 4 hero metrics; Pattern C on Quality tab.**

### Edge cases

- Null target: suppress the target row.
- Zero baseline: render "▲ new" not "▲ ∞%".
- Inverted-direction metrics: arrow stays directional, color carries the moral.
- First-period: "—" with tooltip "Insufficient history."
- Tiny absolute, big percent (1→3=+200%): show raw delta in parentheses `▲ 200% (+2)`.

## 3. Chart-type recommendations per metric category

### 3.1 Single scalar with comparison
**Recommended:** Custom `KpiCard` extending `dashboard/src/components/kpi-card.tsx` — number + Pattern A inline delta + target ring.
**Alternatives:** Big number with sparkline (Pattern B); Radial progress (`<RadialBarChart>`); Bullet chart (Pattern C).

### 3.2 Time series
**Recommended:** `<LineChart>` with optional `<Area>` underlay at 12% opacity. Add `<ReferenceLine>` for target, `<Brush>` for >12 weeks, `<ReferenceDot>` for annotations.
**Alternatives:** Stacked area; Bar chart for daily/weekly buckets; Horizon chart (novel for ops).

### 3.3 Distribution
**Recommended:** `<BarChart>` as histogram with fixed buckets. CHS gets named buckets (poor/pass/good/excellent), each colored by band.
**Alternatives:** Strip plot for small-N; Box plot (skip for MVP).

### 3.4 Categorical breakdown
**Recommended:** Horizontal bar chart, sorted descending. Generalize existing `FunnelChart` and rename `CategoryBars`.
**Alternatives:** Donut/pie (≤4 slices); Treemap (2-level breakdown); Stacked horizontal bar (single-row composition).

### 3.5 Geographic
**Recommended:** Origin × destination state matrix heatmap. Hand-rolled HTML grid (cleaner than Recharts).
**Alternatives:** Sankey (`react-d3-sankey`); Choropleth (`react-simple-maps` — Tier-2); Bar chart fallback.

### 3.6 Relational
**Recommended:** Scatter plot (`<ScatterChart>`) with optional trend `<ReferenceLine>`, dot color encoding third dimension.
**Alternatives:** Heatmap for two-categorical-axis cases; Small-multiples.

### 3.7 Ranking
**Recommended:** Sortable horizontal bar chart, sorted descending.
**Alternatives:** Lollipop chart; Ranked table with embedded sparklines (single most novel ranking pattern — high wow).

### 3.8 Funnel
**Recommended:** Vertical funnel with conversion-rate annotations between stages. Use Recharts `<FunnelChart>`.
**Alternatives:** Stacked horizontal bar; Step chart with drop-off labels (better than vanilla funnel).

### 3.9 Sequence / lifecycle
**Recommended:** Horizontal event timeline (HTML/CSS or `<ScatterChart>` styled as timeline).
**Alternatives:** Vertical event log (commit-log look); Gantt-style row.

### 3.10 Alert / boolean
**Recommended:** Status banner / alert pill at top of relevant tab. No chart.
**Alternatives:** Status grid (3×3 RAG tiles); "What's wrong today" curated card.

## 4. Interactive patterns

- **Default tooltip:** bold metric name + value + comparison row + dimmed timestamp. `--bg-surface-2` 95% opacity, 1px border, 8px radius.
- **Expanded tooltip:** Shift-hover or 800ms hover-hold for richer content.
- **Sticky tooltip:** click anchors until clicked elsewhere.
- **Crosshair:** time-series gets vertical guide line, synchronizes across charts in same row.
- **Click-through:** chart click → tab+filter; row click → detail page; detail → related entity.
- **Brush + zoom:** `<Brush>` at bottom of charts >30 periods. Drag handles only — no pinch/mousewheel.
- **Hover-highlight:** legend hover dims others to 25%; stack-segment hover highlights only that segment.
- **Crossfilter:** ONE tab for v2 (Overview or Calls). Charts on same tab share filter context. Filter chip appears at top.

## 5. Empty / loading / error states

### KPI card
- **Loading:** shimmer skeleton matching final layout. Don't flash if response <300ms.
- **Empty:** `—` (em-dash), comparison rows hidden, single-line hint.
- **Error:** `—` muted + `AlertCircle` + clickable "Retry."

### Time series chart
- **Loading:** skeleton with chart frame visible.
- **Empty:** empty axes drawn, centered "No activity in this window."
- **Error:** "Chart failed to load." + retry button.

### Table
- **Loading:** 6 skeleton rows.
- **Empty:** context-specific copy, never "Insufficient data."
- **Error:** "Couldn't fetch results. Retry."

### Drilldown detail page
- **Loading:** full-page shimmer, breadcrumbs stay clickable.
- **Empty/not-found:** "We couldn't find that call. It may have been deleted."
- **Error:** "Something went wrong." + retry + back buttons.

### Style discipline
- No "We have not received any data" (passive).
- No exposed implementation language ("Twin," "API," "row," "record").
- Active voice; user-perspective; one sentence; one CTA when actionable.
- Empty states **teach** what should appear.

## 6. Three layout options for the overview tab

### Option A — KPI strip + 4-quadrant chart grid (classic)
Familiar = trustworthy. Doesn't celebrate any one metric.

### Option B — Hero metric + sidebar + main canvas (focus mode) — RECOMMENDED
Big number sells the story in 0.5s. Activity feed makes it live. Mobile-friendly.

### Option C — Split-pane operations console (live left, history right)
Most freight-native; mirrors dispatch boards. Mobile breaks down.

**Recommendation:** Option B as default + Option C as `?layout=ops` URL toggle.

## 7. Active-call live indicator

- **Location:** header right rail, immediately left of user avatar.
- **Resting (zero active):** small grey dot.
- **Active (≥1):** small green dot (`#10B981`) with 2-second pulse.
- **Hover:** tooltip lists active calls.
- **Click:** opens slide-over panel.
- **Cadence:** poll `/v1/calls/active` every 10s.
- **A11y:** respect `prefers-reduced-motion`; static green dot fallback.

## 8. Anti-patterns

- Pies with >4 slices.
- 3D charts of any kind.
- Donut charts where lines belong.
- Gradients that imply value.
- Decorative-not-informative icons.
- Low-density bars (600px chart with 3 bars).
- Pie chart of binary outcomes.
- Stacked area where lines belong.
- Y-axis not starting at 0 on bar chart.
- Truncated x-axis on time series.
- Magic numbers in axis labels (no unit).
- Animated-on-load entry >400ms.
- Tooltips that obscure the data.
- Color as the only encoding.
- More than 3 unique chart types per tab.
- Mixing dollars and percentages on same axis without dual y-axes.

## 9. Branding integration

1. **Wordmark, not logo.** Acme name as typeset wordmark (Geist 600, 18px, primary color).
2. **Logo placement: header-left.** 24px height max.
3. **Brand color used sparingly:** as the active accent.
4. **No tagline anywhere on chrome.**
5. **Customer (broker) logo placeholder: bottom-left of sidebar at 60% opacity.**

## Final summary

- **Default palette:** Option A — Dark ops console.
- **Three most novel viz ideas:**
  1. Origin × destination state matrix heatmap.
  2. Sparkline-in-table for carrier ranking.
  3. Per-call horizontal event timeline on call detail page.
- **Three demo-WOW charts:**
  1. Effective delta over time as hero area chart.
  2. Active calls live indicator with click-to-slide-over panel.
  3. Outcome funnel with drop-off shading.
- **Tradeoff vs Grafana:** Information density ↓, legibility ↑. Real-time refresh ↓, cognitive simplicity ↑. Customizability ↓, opinionated layout ↑. This is **DispatchTrack-meets-Linear** in a freight workflow.
