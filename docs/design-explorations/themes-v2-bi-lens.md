# Themes V2 — BI / Analytics Design Languages

Design exploration drafted 2026-04-30. Deliverable for the Acme Logistics carrier-ops dashboard (Next.js 15 + Tailwind 4 + shadcn/ui + Recharts; no Tremor / nuqs / react-day-picker / date-fns / Popover-Calendar per ADR-011).

**What this round fixes.** The previous nine dark themes (`themes-9-dark.md`) varied only `--bg`, `--primary`, and `--chart-N` hex values. Same KPI-tile geometry, same chart cards, same ticker. Reviewer correctly read it as one theme in nine outfits. This round produces **structurally different design languages** — different typography stacks, density, radius philosophy, motion, grid system, and table treatment — each anchored to a recognizable BI/analytics tool's visual signature.

**Lens.** Each theme is a deliberate borrow from a specific BI tool's design language: Tableau (Tufte-light, dense small-multiples), Hex (analyst notebook), Power BI (Office-ribbon formal), Sigma Computing (notebook-pro spreadsheet hybrid). Free associations into Apache Superset, Looker, Metabase appear where they sharpen the contrast.

**Critical reading rule.** When you compare KPI tiles across the four themes below, the `calls`, `bookings`, `booked-rate %`, `avg booked rate`, `CHS`, and `latency p70/p90` numbers are identical — the *visual geometry of how those numbers are presented* is what changes. That is the deliverable.

---

## 1. Tufte Console

**Inspiration.** Tableau on a stripped-back default workbook + Edward Tufte's *Visual Display of Quantitative Information* — small multiples, sparkline-native, axis-respecting, almost no chrome. Looker Studio's data-density at its most disciplined. The mental model is **"the data IS the UI"** — the screen is mostly axes and numbers, not cards and gradients.

**Why this fits a freight-broker ops desk.** Dispatchers reading rate sheets for hours don't need card chrome — they need 60–120 numbers on screen at once with hierarchical typography doing the structural work. A Tufte language gives ops staff Bloomberg-equivalent density without the eye fatigue of a CRT terminal palette.

### Typography
- **Family stack.** Body: `"Source Serif 4", "Charter", Georgia, serif`. Numeric: `"IBM Plex Mono", "JetBrains Mono", monospace`. UI labels: `"Inter Tight", system-ui, sans-serif`.
- **Why mixed.** Serif body is the Tufte signature — it makes prose-scale labels (carrier name, lane description, booking note) read like a financial report, not a SaaS app. Mono for *every* number locks columns to the grid pixel-for-pixel. Sans for nav/buttons keeps interactive elements legible at small sizes.
- **Type scale.** 11 / 12 / 13 / 15 / 18 / 24 / 32 / 48 px. Body default 13px. Numerics in tables 12px mono. KPI hero number 32px mono. Chart axis labels 11px.
- **Weights.** 400 body serif, 600 serif headings, 500 mono numerics, 700 mono for emphasis (e.g. negative variance). No 800/900 — Tufte never shouts.
- **Letter-spacing.** Headings −0.01em (slightly tightened serif). Mono numerics 0. UI caps labels +0.06em.
- **Line-height.** Body 1.55, headings 1.2, table rows 1.35.

### Color tokens (light mode primary; dark is a literal inversion)
```css
:root {
  --bg: #FBFAF7;             /* warm paper, not white */
  --surface: #FBFAF7;        /* surfaces ARE the page — no card lift */
  --surface-elevated: #F4F1EA;
  --border: #DDD7CB;         /* hairline only */
  --border-strong: #1F1B16;  /* axis rules */
  --fg: #1F1B16;
  --fg-muted: #6F6A60;
  --primary: #1F1B16;        /* ink-black is the primary, not a hue */
  --primary-fg: #FBFAF7;
  --accent: #C2410C;         /* burnt orange — used SPARINGLY for callouts */
  --success: #15803D;
  --warning: #A16207;
  --danger: #B91C1C;
  --chart-1: #1F1B16;        /* ink */
  --chart-2: #6F6A60;        /* graphite */
  --chart-3: #C2410C;        /* burnt orange */
  --chart-4: #15803D;        /* moss */
  --chart-5: #1E40AF;        /* navy */
}
```
**Color philosophy.** Greyscale-first. Hue is a signal, not decoration. A bar chart of seven lanes is mostly graphite; the one lane carrying the eye is burnt orange. This is the opposite of a generic SaaS palette where every chart series gets its own carnival color.

### Spacing scale
`2 / 4 / 8 / 12 / 16 / 24 / 32 / 48 px`. **Density: compact.**
- Table rows: 28px tall (8px vertical padding around 12px line-height).
- KPI block internal padding: 12px.
- Section gap (between KPI strip and chart strip): 24px.
- Chart card internal padding: 16px.

### Radius scale
`0 / 0 / 2 / 2 px`. Effectively **sharp**. Buttons 2px. Inputs 0px. Cards 0px (no card boundary at all — see component patterns).

### Shadow scale
**None.** Zero shadows anywhere. Hierarchy is created by hairline rules (`--border`) and typographic weight only. This is the Tufte non-negotiable.

### Motion
- **Hover on data row:** background shifts to `--surface-elevated` over 80ms `ease-out`. No transform.
- **Sort/filter recompute:** numbers crossfade in place over 120ms `linear`. No bounce.
- **Drill-down panel:** slides up from page bottom over 180ms `cubic-bezier(0.2, 0, 0, 1)`. Page does not dim.
- Total motion budget: <200ms anywhere. Nothing pulses, nothing breathes.

### Grid system
**12-column strict, 1280px content max-width, 16px gutter.** No masonry, no auto-fit. Tables can break the grid and span full bleed. Charts respect column boundaries.

### Component patterns (the load-bearing differentiator)

**KPI tile — "the strip".** Tiles are *not cards*. They are vertical slices of a single horizontal strip separated by 1px hairlines (`--border`). No background fill, no shadow, no radius. Layout per slice:
```
LABEL (11px caps, --fg-muted, +0.06em)
HERO NUMBER (32px mono, --fg, weight 500)
DELTA (12px mono, --success or --danger, with arrow glyph ↑↓)
SPARKLINE (full width of slice, 28px tall, ink-on-paper, no axis)
```
Six KPIs sit in one strip. Reading order is left-to-right, eye lands on hero number first because it's the only large element. No icons. No gradient. The strip itself has a 1px top + bottom rule and that's it.

**Chart card.** Same approach: a 1px hairline above and below the chart, full-bleed within its grid columns. Chart title is 13px serif italic, left-aligned, hanging in the margin to the *left* of the chart canvas — Tufte-style marginalia, not a header bar. Y-axis labels are 11px mono right-aligned with 4px right padding. X-axis is a single hairline. Series lines are 1.5px ink with one optional accent series in burnt orange.

**Table row.** Borderless. No zebra. Row height 28px. Hover-only treatment: row background shifts to `--surface-elevated`. Numeric columns are right-aligned mono. Text columns are left-aligned serif. Sortable headers underline on hover. Row separator is **whitespace**, not a rule — except every 5th row gets a hairline tick in the leftmost gutter (a Tufte five-row index marker).

**Button.** Text-only by default — looks like a hyperlink in `--accent`. Primary action gets a 1px solid `--fg` outline with no fill. Secondary is plain underlined text. Disabled is `--fg-muted` italic.

**Ticker bar.** Single hairline-bordered horizontal strip at the top of Overview. Marquee scrolls *slowly* (300px / 8s, linear). Each ticker item is `LANE → RATE (DELTA)` in mono. No icons, no separator characters except a single `·` between items. No background fill — sits directly on `--bg`.

**Drill-down panel.** Slides from the bottom 60% of the viewport. Page content above does **not** dim — it stays fully readable, because in Tufte logic context is sacred. Panel has a 1px top rule, no shadow, no rounded corners. Close affordance is a hairline `×` in the top-right.

### Diff vs other themes in this file
- **Vs Hex Notebook:** Tufte uses serif body + ink-black primary; Hex uses sans humanist + a single saturated indigo. Tufte has zero shadows; Hex has soft inner shadows on cells. Tufte tables are borderless; Hex tables are zebra'd with a left-side cell-status gutter. Tufte uses a strict 12-col grid; Hex uses a notebook-vertical-stack flow.
- **Vs Power BI Boardroom:** Tufte is paper-warm `#FBFAF7` and ink; Power BI is corporate-cool `#F8F9FA` with a navy ribbon. Tufte has 0px radius; Power BI has 4px radius and dramatic 8/16/24 elevation shadows. Tufte KPIs are a hairline-divided strip; Power BI KPIs are bordered cards in a 4-up grid with category icons.
- **Vs Sigma Spreadsheet:** Tufte's primary visual is a chart with hairlines; Sigma's primary visual is a *spreadsheet grid* with frozen-pane borders and cell-level conditional formatting. Tufte has burnt-orange single-accent; Sigma uses Excel-green for positives and Excel-red for negatives across data bars inside cells.

---

## 2. Hex Notebook

**Inspiration.** Hex.tech's analyst notebook UI, with hat-tips to Sigma Computing's cell hierarchy and Apache Superset's slice metadata. The mental model is **"every chart is a cell with provenance"** — every visualization shows its query, its last-refreshed time, and its owner inline. The page reads top-to-bottom like a Jupyter notebook, not left-to-right like a dashboard.

**Why this fits a freight-broker ops desk.** Carrier-ops decisions are auditable — when a CHS dropped or a margin compressed, the manager wants to know *which call, which extraction, which load*. A notebook layout exposes that lineage natively. Each KPI links to the underlying SQL/aggregation that produced it, which is exactly the auditability story that wins enterprise demos.

### Typography
- **Family stack.** UI + body: `"Inter", "Inter Variable", system-ui, sans-serif`. Code/numerics: `"JetBrains Mono Variable", "Fira Code", monospace`. **No serif anywhere** (deliberate contrast vs Tufte).
- **Type scale.** 12 / 13 / 14 / 16 / 20 / 24 / 30 px. Body default 14px. KPI hero number 30px sans (NOT mono — Hex uses sans for big numbers). Code inline 12px mono.
- **Weights.** 400 body, 500 emphasized, 600 headings, 700 KPI hero. Variable axis tuned to 410 for body to soften the Inter cut.
- **Letter-spacing.** Headings −0.02em (Inter-tight default). Body 0. Mono 0. Caps labels +0.04em.
- **Line-height.** Body 1.5, headings 1.3, code blocks 1.45.

### Color tokens
```css
:root {
  --bg: #FFFFFF;
  --surface: #FFFFFF;            /* notebook page is bright white */
  --surface-elevated: #F7F7FB;   /* cell hover and selected state */
  --border: #E4E4EC;
  --border-strong: #C4C4CF;
  --fg: #18181B;
  --fg-muted: #71717A;
  --primary: #4F46E5;            /* indigo — Hex's signature */
  --primary-fg: #FFFFFF;
  --accent: #EC4899;             /* magenta for in-cell run-button */
  --success: #16A34A;
  --warning: #D97706;
  --danger: #DC2626;
  --chart-1: #4F46E5;
  --chart-2: #06B6D4;
  --chart-3: #16A34A;
  --chart-4: #F59E0B;
  --chart-5: #EC4899;
}
```
**Color philosophy.** Five-hue chart palette — every series gets a distinct hue because notebooks are exploratory and analysts want to discriminate series at a glance. Primary indigo carries identity; magenta accent is reserved for "runnable" affordances (run query, refresh cell, re-extract).

### Spacing scale
`4 / 8 / 12 / 16 / 20 / 32 / 48 / 64 px`. **Density: comfortable.**
- Cell internal padding: 16px (top/bottom) × 20px (left/right).
- Cell-to-cell vertical gap: 12px.
- Notebook left gutter (for cell-number labels): 48px.
- KPI cell internal padding: 20px.

### Radius scale
`4 / 6 / 8 / 12 px`. Inputs/buttons 6px. Cells 8px. Modal sheets 12px. Tooltips 4px.

### Shadow scale
- `--shadow-1`: `0 1px 2px rgba(24,24,27,0.04)` — cell default.
- `--shadow-2`: `inset 0 0 0 1px var(--border)` — selected cell (inner ring, not outer drop).
- `--shadow-3`: `0 4px 12px rgba(24,24,27,0.06)` — drill-down panel.
- `--shadow-4`: `0 8px 24px rgba(24,24,27,0.08)` — modal.

**Shadow philosophy.** Cells get a *subtle outer 1px shadow at rest* and an *inner ring on selection* — direct lift from Hex's cell focus model. No dramatic elevation; everything sits close to the page.

### Motion
- **Cell hover:** border-strong fades in over 120ms `ease-out`. No transform.
- **Cell run / refresh:** an inline 2px progress bar at the top edge of the cell crawls left-to-right over the actual fetch time, then fades out over 200ms.
- **Drill-down:** opens as a *new cell appended below* the source cell with a 240ms `cubic-bezier(0.16, 1, 0.3, 1)` height-and-opacity reveal. The page scrolls to keep the new cell in view.
- **Number tween:** numeric updates count up/down over 400ms `ease-out` (a Hex-specific delight pattern).

### Grid system
**No fixed grid.** Vertical stack of full-width "cells" up to a `max-width: 1100px` centered column. Each cell can split horizontally into 2 or 3 sub-cells (KPI strip, chart + table side-by-side) but the *container* flow is top-to-bottom notebook style. **This is a structural difference from Tufte's strict 12-col.**

### Component patterns

**KPI tile — "the cell".** Each KPI is its own bordered cell with a distinct two-row header strip:
```
[ROW 1 — meta strip, 11px mono, --fg-muted]
  cell #03  •  source: calls_log  •  refreshed 2m ago  •  ⓘ ▶
[ROW 2 — content, 20px padding]
  Label (12px sans, --fg-muted, +0.04em caps)
  HERO NUMBER (30px sans, --fg, weight 700) ← left-aligned
  Delta pill (rounded 12px, --success-bg / --danger-bg fill, 11px)
  Sparkline below (full-cell-width, 36px tall, smoothed line + dot at latest)
```
KPIs sit in a 3-up or 4-up *grid inside one cell* (responsive — collapses to 2-up on mid-width). The cell gets a 1px outer border, 8px radius, and the subtle outer drop shadow. **Critical structural difference from Tufte:** Tufte KPIs are slices of a continuous strip with no card boundary; Hex KPIs are bounded cells with metadata headers and a "▶ run" affordance.

**Chart card — "the chart cell".** Same cell chrome as KPIs (meta strip + content), but content is a single chart canvas with a soft `--surface-elevated` background tint to distinguish chart-cell from KPI-cell. Chart title is 14px sans semibold inside the meta strip, *not* hanging in margin. Below the chart, a collapsed `▼ View query` chevron expands a code block showing the underlying SQL/aggregation pseudocode — provenance is the differentiator.

**Table row.** Zebra'd: every odd row gets `--surface-elevated`. 36px row height (taller than Tufte). Each row has a 4px-wide leftmost cell-status gutter that shows green/amber/red dot for outcome (booked / negotiating / lost). Hover lifts the entire row to `--surface-elevated` on both stripes uniformly. Sortable headers show a chevron on hover. Selected row gets a 2px left border in `--primary`.

**Button.** Filled `--primary` with white text and 6px radius for primary actions. Secondary is `--surface-elevated` background with 1px border. Tertiary is text-only with chevron. Magenta `--accent` only on "Run", "Refresh", "Re-extract".

**Ticker bar.** Not a marquee. A horizontal scrollable cell with hard left/right edge fade (`mask-image` gradient). Each ticker item is a *mini-card* with rounded 6px corners, lane code badge, rate, and direction chevron. User can click-drag or arrow-key through them. Updated lanes flash `--accent` for 300ms.

**Drill-down panel.** Opens *inline* as a new cell below the row that triggered it (notebook pattern). Not a modal, not a side sheet. The page reflows. Cell has a "← back" link in its meta strip that scrolls the user back to the source row.

### Diff vs other themes in this file
- **Vs Tufte Console:** Hex uses sans-only typography vs Tufte's serif-mono mix; Hex is a vertical notebook flow vs Tufte's strict 12-col; Hex KPIs are bounded cells with provenance metadata vs Tufte's hairline-divided strip; Hex zebra-stripes tables vs Tufte's borderless whitespace separator.
- **Vs Power BI Boardroom:** Hex's bright white `#FFFFFF` vs Power BI's cool `#F8F9FA` with a colored ribbon header; Hex has 8px radius and subtle 1px shadows vs Power BI's 4px radius with dramatic 8/16/24px elevations; Hex appends drill-downs as inline cells vs Power BI's full-page modal navigation; Hex uses indigo/magenta as primary signals vs Power BI's corporate navy/teal.
- **Vs Sigma Spreadsheet:** Hex's notebook-cell flow vs Sigma's spreadsheet-grid-first layout; Hex prioritizes chart cells with provenance vs Sigma's data-bars-inside-cells philosophy; Hex uses a 5-hue chart palette vs Sigma's two-hue (green/red) conditional formatting; Hex's row height is 36px vs Sigma's 22px (Excel-tight).

---

## 3. Power BI Boardroom

**Inspiration.** Microsoft Power BI's "Modern" theme + Office 365 ribbon discipline + Looker Studio's enterprise reporting feel. The mental model is **"executive review document"** — formal, high-elevation card stack, ribbon header for actions, 4-up KPI grids, modal drill-downs. Looks like something a CFO would screenshot into a Monday board pack.

**Why this fits a freight-broker ops desk.** When the demo lands in front of a brokerage VP or a Carlos-Becker-tier prospect, this language signals *enterprise-grade, ready-to-ship*. Ops staff can use it daily, but the *recognition tax* for non-technical viewers is zero — the chrome is familiar from PowerPoint, Excel, Power BI Desktop. It also photographs/Loom-records well because the high contrast + dramatic shadows survive video compression.

### Typography
- **Family stack.** UI + headings: `"Segoe UI Variable", "Segoe UI", system-ui, sans-serif`. Body: same. Numeric: `"Cascadia Mono", "Consolas", monospace` — but only used in tables, NOT in KPI hero numbers.
- **Why Segoe.** Direct Microsoft borrow. Reads as "enterprise software" instantly; pairs with Office-family chrome in mixed-tool environments.
- **Type scale.** 12 / 13 / 14 / 16 / 20 / 28 / 36 / 44 px. Body 14px. KPI hero 36px sans semibold. Table numerics 13px mono.
- **Weights.** 400 body, 600 semibold for headings AND KPI heroes, 700 for "this is the headline" callouts. Segoe Variable wght axis tuned to 380 body for slight softening.
- **Letter-spacing.** All standard 0 except caps labels at +0.05em. No tightened headings — Segoe is already optically tight.
- **Line-height.** Body 1.5, headings 1.25, table rows 1.4.

### Color tokens
```css
:root {
  --bg: #F3F4F8;                 /* Office cool-grey background */
  --surface: #FFFFFF;            /* white cards lifted off cool-grey bg */
  --surface-elevated: #FFFFFF;
  --border: #E1E4EC;
  --border-strong: #B8BCC8;
  --fg: #1B1F2A;
  --fg-muted: #5F6573;
  --primary: #1B3F73;            /* Microsoft-navy enterprise blue */
  --primary-fg: #FFFFFF;
  --accent: #0E8C7A;             /* corporate teal — KPI delta, callouts */
  --success: #107C10;            /* Office green */
  --warning: #B7791F;            /* Office amber */
  --danger: #C42B1C;             /* Office red */
  --chart-1: #1B3F73;
  --chart-2: #0E8C7A;
  --chart-3: #B7791F;
  --chart-4: #C42B1C;
  --chart-5: #6B5B95;
}
```
**Color philosophy.** Cool grey body separates white cards as figure-from-ground (the opposite of Tufte and Hex which use white-on-white). Navy primary = enterprise authority. Teal accent = the "good number" hue in finance contexts.

### Spacing scale
`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 px`. **Density: spacious.**
- Card internal padding: 24px.
- Card-to-card gap: 16px (4-up KPI grid) / 24px (chart row).
- Ribbon height: 56px.
- Drill-down modal padding: 32px.

### Radius scale
`4 / 6 / 8 / 12 px`. Inputs 4px. Buttons 4px (Office-flat-square heritage). Cards 6px. Modals 8px. Tooltips 4px.

### Shadow scale
- `--shadow-1`: `0 1px 2px rgba(27,31,42,0.06), 0 1px 3px rgba(27,31,42,0.04)` — card resting.
- `--shadow-2`: `0 4px 8px rgba(27,31,42,0.08)` — card hover.
- `--shadow-3`: `0 8px 16px rgba(27,31,42,0.12)` — popover / dropdown.
- `--shadow-4`: `0 16px 32px rgba(27,31,42,0.18)` — drill-down modal.

**Shadow philosophy.** Dramatic. Multi-layer Material-style elevation. This is the most card-lifty of all four themes — and it's deliberate. Boardroom decks read by elevation hierarchy.

### Motion
- **Card hover:** elevates from `--shadow-1` to `--shadow-2` over 200ms `cubic-bezier(0.4, 0, 0.2, 1)`. Translate Y by −1px.
- **Tab switch:** content cross-fades over 240ms with a 4px upward slide-in.
- **Modal open:** scrim fades in over 160ms, modal scales from 0.96 → 1.0 with `--shadow-4` over 240ms `cubic-bezier(0, 0, 0.2, 1)`.
- **Number update:** highlight pulse — background flashes `--accent` at 8% opacity for 600ms then fades.

### Grid system
**12-column with explicit gutter rules and breakpoints.** Most layouts are 4-up KPI grid → 2-up chart row → 1-up wide table. Strict alignment, no masonry, no asymmetry.

### Component patterns

**KPI tile — "the lifted card".** A 4-up grid of *bordered, shadowed white cards* on the cool-grey background. Each card:
```
[TOP-LEFT — icon block, 32×32px, --primary fill, white glyph]
[TOP-RIGHT — 3-dot menu (export, drill, copy)]
[ROW — 12px gap]
LABEL (13px sans, --fg-muted, no caps)
HERO NUMBER (36px sans semibold, --fg)
[ROW — 4px gap]
DELTA TEXT (14px sans, --success/--danger, "↑ 12.4% vs last week")
[ROW — 16px gap]
SPARKLINE (full card width, 48px tall, filled area chart with gradient)
```
Card has 24px internal padding, 6px radius, `--shadow-1` resting / `--shadow-2` hover. **Structural difference from Tufte:** Tufte has no card at all and no icon; Power BI has a colored icon block, a 3-dot overflow menu, and a filled-area sparkline (Tufte's is a 1px line). **Structural difference from Hex:** Power BI has no provenance meta-strip and no run-button; the card is for *consuming*, not *running*.

**Chart card.** Same lifted-white-card chrome as KPIs but wider. Header strip with chart title (16px sans semibold), date-range pill on the right, and a "⋯ More options" overflow menu. Chart canvas has a 24px internal pad. Legend sits at the *top-right* of the chart canvas, horizontal pills. Y-axis gridlines are 1px dashed `--border` (Office signature). X-axis is a solid `--border-strong` line. Tooltip on hover is a card with `--shadow-3`.

**Table row.** Heavy borders. Every row has a 1px `--border` bottom. Row height 44px (spacious — up from Hex's 36 and Tufte's 28). Header row has a 2px `--border-strong` bottom and a `--surface-elevated` background that's actually `#FAFBFD`. Numeric columns right-aligned mono, text columns left-aligned sans. Sort affordance is a chevron in the header on hover. Selected row has a `--primary` 4px left border AND a `--primary` 4% tint background. No zebra (heavy borders make zebra redundant and noisy in this language).

**Button.** Primary: filled `--primary` navy, white text, 4px radius, 36px tall, 16px horizontal padding, weight 600. Secondary: white background, 1px `--border` outline, `--fg` text. Tertiary: text-only `--primary` with no underline (underline appears on hover). Office-style. Disabled: `#E1E4EC` background, `#9CA3AF` text.

**Ribbon bar.** A *full-width 56px-tall ribbon* at the top of the page (NOT a marquee ticker). Left: tab buttons for Overview / Calls / Carriers / New Bookings. Right: date-range selector, refresh button, export button, user avatar. White background, `--shadow-1` bottom. **This replaces the ticker concept entirely** — Boardroom doesn't do tickers, it does Office ribbons. The "what changed recently" data goes into a dedicated "Recent activity" card on Overview.

**Drill-down panel.** A **full-screen modal** with a 32px-padded card on a `--shadow-4` scrim. Modal has its own ribbon-like header with breadcrumbs, close button, and "Open in new tab". Clicking outside the modal closes it; pressing Escape closes it. Inside, the same KPI/chart/table chrome repeats one level deeper.

### Diff vs other themes in this file
- **Vs Tufte Console:** Power BI uses dramatic multi-layer shadows (4 elevation steps); Tufte uses zero shadows. Power BI has a 56px ribbon header; Tufte has no chrome bar at all. Power BI KPIs are bordered cards with icons + overflow menus; Tufte KPIs are hairline-divided text-only slices. Power BI is spacious (24px card padding); Tufte is compact (12px).
- **Vs Hex Notebook:** Power BI drill-down is a full-screen modal on a scrim; Hex drill-down is an inline appended cell with no scrim. Power BI uses Segoe UI sans + Cascadia Mono; Hex uses Inter + JetBrains Mono. Power BI has a 4-up KPI grid layout; Hex has a vertical-stack notebook flow. Power BI has no provenance/SQL metadata in cards; Hex shows it inline.
- **Vs Sigma Spreadsheet:** Power BI's primary visual is a chart card; Sigma's primary visual is a frozen-pane spreadsheet grid. Power BI table row is 44px tall with heavy borders; Sigma row is 22px tall with cell-level data bars. Power BI uses Office-navy/teal/red; Sigma uses Excel-green/Excel-red almost exclusively.

---

## 4. Sigma Spreadsheet

**Inspiration.** Sigma Computing's spreadsheet-grid-first analytical UI + Excel's frozen panes + Metabase's question-first ergonomics. The mental model is **"the dashboard IS a workbook"** — primary surface is a dense grid with frozen header rows, in-cell data bars, conditional formatting, and KPIs that look like merged-cell summary blocks at the top of a sheet.

**Why this fits a freight-broker ops desk.** Brokerage rate desks live in Excel. Dispatchers will drop straight into a dashboard that mimics their existing tool. CHS, lane rates, and call lists all reduce naturally to spreadsheet rows; in-cell visualizations (data bars, sparkline-in-cell, color scales) are the densest form of analytical UI ever invented. This theme leans into that and embraces it.

### Typography
- **Family stack.** UI: `"Inter", system-ui, sans-serif`. **Numerics + most body cells: `"Aptos Narrow", "Aptos", "Calibri", sans-serif` (proportional, NOT monospace)** — Excel uses Aptos as default since 2024 and humans read proportional faster in tabular contexts than mono.
- **Why proportional numerics.** Excel/Sheets/Sigma all default to proportional — mono is only used for code blocks. Tabular alignment is achieved with `font-feature-settings: "tnum" 1` (tabular-numerals enabled inside a proportional face).
- **Type scale.** 11 / 12 / 13 / 14 / 18 / 22 / 28 px. Cell text 12px. KPI hero 28px sans bold. Header row 11px sans semibold caps.
- **Weights.** 400 cell text, 500 totals row, 600 column headers, 700 KPI hero. No 800/900.
- **Letter-spacing.** Header caps +0.08em (the Excel signature). All other text 0.
- **Line-height.** Cells 1.25 (Excel-tight). Body prose 1.45.

### Color tokens
```css
:root {
  --bg: #FFFFFF;
  --surface: #FFFFFF;
  --surface-elevated: #F2F4F7;   /* frozen-pane / header background */
  --border: #D0D5DD;             /* cell gridlines — visible by default */
  --border-strong: #344054;      /* frozen-pane separator */
  --fg: #101828;
  --fg-muted: #667085;
  --primary: #217346;            /* Excel-green — the canonical association */
  --primary-fg: #FFFFFF;
  --accent: #1F77B4;             /* Tableau-blue for hyperlinks */
  --success: #12B76A;            /* in-cell positive data bar */
  --warning: #F79009;
  --danger: #D92D20;             /* in-cell negative data bar */
  --chart-1: #217346;
  --chart-2: #D92D20;
  --chart-3: #1F77B4;
  --chart-4: #F79009;
  --chart-5: #6941C6;
}
```
**Color philosophy.** Two-hue dominant — Excel-green for positive, Excel-red for negative. Every other color is restrained. Conditional formatting carries 70% of the visual signal; charts are secondary citizens.

### Spacing scale
`2 / 4 / 6 / 8 / 12 / 16 / 24 / 32 px`. **Density: ultra-compact (Excel-tight).**
- Cell padding: 4px vertical × 8px horizontal.
- Row height: 22px (the actual Excel default).
- Column header height: 28px.
- KPI summary block padding: 12px.
- Sheet edge gutter: 16px.

### Radius scale
`0 / 0 / 2 / 4 px`. Cells 0px. Inputs 2px. Buttons 2px. Modals 4px. **Almost as sharp as Tufte but for a different reason — Tufte is editorial restraint, Sigma is spreadsheet authenticity.**

### Shadow scale
- `--shadow-1`: none on cells.
- `--shadow-2`: `inset -1px 0 0 var(--border-strong)` — frozen-pane right edge.
- `--shadow-3`: `inset 0 -1px 0 var(--border-strong)` — frozen-row bottom edge.
- `--shadow-4`: `0 2px 8px rgba(16,24,40,0.08)` — popover only.

**Shadow philosophy.** Inner shadows for frozen-pane separators. Outer shadows banned everywhere except popovers. Distinct from Power BI's elevation-heavy stack and Hex's subtle outer card lift.

### Motion
- **Cell selection:** 1px `--primary` outline draws in over 80ms `linear`. Direct Excel-cell-select borrow.
- **Sort animation:** rows reorder with FLIP technique over 300ms `cubic-bezier(0.4, 0, 0.2, 1)` — visible reflow so the user can track which row went where.
- **Filter:** non-matching rows collapse height to 0 over 180ms; remaining rows snap up.
- **Drill-down:** opens as a *split-pane below the grid* (50/50 vertical split) with a draggable divider. Pane slides up over 200ms. No modal.

### Grid system
**Spreadsheet grid IS the layout.** No 12-col container. The page is a single full-width sheet with frozen header rows (KPI summary block at top + column headers), then scrollable data rows below. Tabs across the top switch sheets — Overview is one sheet, Calls is another sheet, etc. Each sheet has its own frozen-row KPI strip.

### Component patterns

**KPI tile — "the merged-cell summary block".** KPIs sit in a *frozen header band* above the data grid, styled to look like merged cells at the top of an Excel sheet. Six KPIs in one horizontal band:
```
[CELL — 1px --border on all sides, --surface-elevated background]
  Label (11px sans semibold caps, --fg-muted, +0.08em) — 4px top padding
  HERO NUMBER (28px sans bold, --fg, tabular-nums) — center-aligned
  DELTA (12px sans, --success/--danger fg) with TINY ARROW ▲▼
  IN-CELL DATA BAR (full-cell-width 4px-tall horizontal bar; fill = % of target;
                    color = --success if ≥ target else --warning)
```
**Critical structural difference from the other themes:** there is no card lift, no shadow, no rounded corner. The KPI block looks *exactly like a frozen merged-cell row in Excel*, complete with cell gridlines and a conditional-formatting data bar inside each cell. The data bar is the differentiator — Tufte uses a sparkline, Hex uses a sparkline, Power BI uses a filled-area sparkline; Sigma uses an in-cell horizontal bar at the bottom of the cell, exactly as Excel's "Conditional Formatting → Data Bars" produces.

**Chart card.** Charts are *secondary citizens* in this theme. They appear as a thin row of 3 small-multiples *below* the data grid, each 280px wide × 160px tall, no card chrome — just a 1px border and a 11px caption. Charts use Tableau-style design: 1.5px line, no fill, axis labels in `--fg-muted`. The grid is the hero, not the chart.

**Table row.** This is the heart of the theme. Visible 1px `--border` cell gridlines on every cell (Excel default). Row height 22px. Alternating row background is *off* by default (Excel default — gridlines do the separation work). Hover highlights the entire row to `--surface-elevated`. Cells with conditional formatting render an in-cell data bar, color scale, or icon set:
- *Rate columns:* horizontal data bar with green/red based on whether rate ≥ listed.
- *CHS columns:* color scale 0-100 (red → yellow → green gradient as cell background).
- *Outcome columns:* icon set (✓ booked, ⋯ negotiating, ✗ lost) as a 16×16 glyph at the cell's left.
Selected row: 2px `--primary` outline (the Excel name-box-select look). No left-border accent like Power BI.

**Button.** Two variants only. Primary: filled `--primary` Excel-green, white text, 2px radius, 28px tall (matches column header height). Secondary: 1px `--border` outline, `--fg` text. Buttons sit in a 36px-tall toolbar that runs across the top of the data grid (sort / filter / freeze / export). No tertiary text-buttons — Sigma forces explicit affordances.

**Ticker bar.** Replaced with a **"Recent activity" frozen sub-row** at the top of the grid, between the KPI strip and the column headers. It shows the 5 most recent calls/bookings as condensed cells with a `>>` chevron link to the full Calls tab. No animation, no marquee — the row updates on refresh.

**Drill-down panel.** **Bottom split-pane** (50/50 vertical split) with a draggable horizontal divider. Top half stays on the grid; bottom half loads the drill-down content (full call detail, full carrier history, etc.). The user can drag the divider up/down. Closing the pane snaps the divider to the bottom edge. **This is a structurally distinct affordance from the other three themes** — Tufte slides up from the bottom over the page, Hex appends as a new cell inline, Power BI opens a full-screen modal, Sigma uses split-pane.

### Diff vs other themes in this file
- **Vs Tufte Console:** Sigma uses proportional Aptos with tabular-nums vs Tufte's serif body + mono numerics; Sigma row height is 22px Excel-tight vs Tufte's 28px; Sigma's primary surface is a spreadsheet grid with visible gridlines vs Tufte's borderless prose-tables; Sigma KPIs include in-cell data bars vs Tufte's hairline sparklines; Sigma uses tabbed sheets as the layout primitive vs Tufte's 12-col grid.
- **Vs Hex Notebook:** Sigma's grid-first layout vs Hex's vertical notebook flow; Sigma's row height 22px vs Hex's 36px; Sigma drops chart cells to small-multiples below the grid vs Hex's chart-cells-as-equal-citizens; Sigma uses Excel-green primary vs Hex's indigo; Sigma drill-down is split-pane vs Hex's inline-appended-cell.
- **Vs Power BI Boardroom:** Sigma is ultra-compact (22px rows, 4px cell padding) vs Power BI spacious (44px rows, 24px card padding); Sigma has zero card chrome / zero outer shadows vs Power BI's 4-step elevation stack; Sigma KPIs are styled as merged-cell summary rows vs Power BI's 4-up grid of lifted icon-cards; Sigma drill-down is split-pane vs Power BI full-screen modal; Sigma uses Aptos Narrow vs Power BI uses Segoe UI.

---

## Side-by-side summary

| # | Theme | BI tool inspiration | KPI tile geometry | Chart card | Table row | Drill-down |
|---|---|---|---|---|---|---|
| 1 | Tufte Console | Tableau / Looker Studio (stripped) | Hairline-divided horizontal strip; serif label + mono number + 1px sparkline; no card | Marginalia title in left margin; 1.5px line; no fill | Borderless 28px row, 5-row tick marker, hover-only | Slides up from bottom, no scrim |
| 2 | Hex Notebook | Hex.tech notebook | Bounded cell with provenance meta-strip + ▶ run button; sans hero number; smoothed sparkline | Cell with collapsible "View query" SQL block | Zebra'd 36px rows; 4px left status-dot gutter | Inline appended cell below source row |
| 3 | Power BI Boardroom | Power BI / Looker / Office | Lifted white card with colored icon block + 3-dot menu; semibold sans hero; filled-area gradient sparkline | Title + date-range pill + overflow menu; dashed gridlines; legend top-right | Heavy-bordered 44px rows; selected row gets 4px primary left border | Full-screen modal on shadow-4 scrim |
| 4 | Sigma Spreadsheet | Sigma / Excel / Metabase | Frozen-merged-cell summary band; tabular Aptos hero + in-cell horizontal data bar | Small-multiples row of 3 charts below the grid; no card chrome | 22px Excel-tight rows, visible gridlines, in-cell data bars + color scales + icon sets | Bottom split-pane with draggable divider |

| # | Theme | Typography | Density | Radius | Shadow | Motion budget | Grid |
|---|---|---|---|---|---|---|---|
| 1 | Tufte Console | Serif body + mono numeric + sans UI | Compact (28px row) | 0–2px | None | <200ms | 12-col strict |
| 2 | Hex Notebook | Inter sans + JetBrains Mono code | Comfortable (36px row) | 4–12px | Subtle outer + inner ring on select | <400ms (number tween) | Vertical notebook flow, 1100px max |
| 3 | Power BI Boardroom | Segoe UI + Cascadia Mono in tables | Spacious (44px row) | 4–12px | Dramatic 4-step elevation | <240ms | 12-col strict |
| 4 | Sigma Spreadsheet | Aptos Narrow proportional w/ tabular-nums | Ultra-compact (22px row) | 0–4px | Inner only (frozen-pane edges) | <300ms (FLIP sort) | Spreadsheet-grid-as-layout |

---

## Adoption notes

- Each theme would land as a separate `:root` token block in `dashboard/src/app/globals.css` plus theme-specific component overrides in a `dashboard/src/styles/themes/` folder. The four themes cannot be a pure-CSS-vars swap — KPI tile structure, ticker → ribbon → activity-row substitution, drill-down panel mechanism, and table row padding all require component-level changes.
- shadcn/ui consumes `--background`, `--foreground`, `--primary`, `--secondary`, `--accent`, `--muted`, `--muted-foreground`, `--border`, `--destructive`. All four themes alias these to the listed tokens (with `--destructive: var(--danger)`).
- Recharts: pull `var(--chart-N)` through a small helper. Tufte and Sigma override the default Recharts series stroke from 2px to 1.5px and 1px respectively. Power BI keeps Recharts defaults. Hex bumps to 2.5px with a 6px end-dot.
- Recommended demo path: build out one theme end-to-end before A/B-ing. Power BI Boardroom is the safest demo win (lowest recognition tax, photographs/Looms well). Sigma Spreadsheet is the most differentiated for a freight-rate-desk audience. Tufte Console is the data-density flex. Hex Notebook is the auditability-as-a-feature flex.
- Light-mode primary in this round (vs the rejected 9 dark themes) is deliberate — BI tools are predominantly light-mode in their canonical signature. Dark inversions for each theme are a follow-up if needed.

---

## What was rejected from the previous round (for the record)

The 9 dark themes in `themes-9-dark.md` shared:
- One identical KPI-tile geometry (label · hero number · delta · 1-line sparkline, all in a fixed-aspect rounded-rectangle card with `--surface` fill and a soft shadow).
- One identical chart-card chrome (16px header, padded canvas, generic Recharts defaults).
- One identical horizontal-marquee ticker.
- One identical table treatment (zebra'd rows, 36px height, no special row treatments).
- The only thing that varied: hex values for `--bg`, `--primary`, `--accent`, `--chart-1..5`.

This round explicitly rejects all five of those structural defaults and produces four DIFFERENT structural defaults — one per theme — borrowed from a recognizable BI tool's grammar.
