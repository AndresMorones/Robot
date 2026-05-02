# Dashboard Final Production Register

> Single comprehensive audit of every captured dashboard improvement, polish item, design recommendation, theme spec, ADR consequence, and post-MVP queued task that touches the Next.js dashboard at `dashboard/`. Compiled 2026-04-30 from a full memory + repo audit. Source-cited; no invention.

> **Status snapshot (verbatim from `project_resume_2026_04_30_post_compact.md`)**: API + dashboard both deployed (`robot-api-andres-morones.fly.dev`, `robot-dashboard-andres-morones.fly.dev`). Calls drilldown WAF fix landed in code, NOT yet redeployed. Logo sub-agent ran, 7 concepts written to `dashboard/src/components/branding/LOGO_OPTIONS.md`. Goliath chart review at `docs/dashboard-chart-review.md`. **The dashboard is live and functional; this register catalogs everything still queued to land on top.**

---

## Table of contents

1. Locked theme (verbatim)
2. Locked telemetry widgets
3. Locked Call Logs tab spec
4. Outstanding dashboard polish — categorized by area
5. New dashboard tabs queued (post-MVP)
6. Drift findings (D1-D18) from Phase B audit
7. Items that look like dashboard work but actually need HR/Twin first
8. Logo decision (locked-theme-derived recommendation)
9. Anything not on radar (surprises + conflicts)
10. Implementation order recommendation

---

## 1. Locked theme — verbatim

Source: `project_dashboard_theme_composite_locked.md` (LOCKED 2026-04-30 night, supersedes Pine Ledger v3 and D2 The Tape ticker).

### 1.1 Composition name + structure
- **Composition name**: `freight-terminal-composite`
- **Primary design language**: Freight Terminal (Vercel × Apple Developer)
- **Telemetry / Observability surface**: Bloomberg Pit (Bloomberg × Plaid)
- **Dense data tables**: Sigma Spreadsheet pattern, ported to Freight Terminal dark palette
- **Global Cmd-K palette**: Loadboard Live (Raycast × Arc Browser)
- **Retired**: Pine Ledger v3 lock + D2 The Tape ticker — both replaced by this composite. v1 9-dark themes (`themes-9-dark.md` + `themes-preview.html`) also rejected.

### 1.2 Freight Terminal tokens (PRIMARY) — verbatim from `themes-v2-modern-saas-lens.md` §3
```
--bg:               #060607   /* darker than Theme 1 */
--surface:          #0E0E10
--surface-elevated: #16161A
--border:           #232328
--border-strong:    #3A3A42
--fg:               #FAFAFA
--fg-muted:         #9A9AA3
--primary:          #FFFFFF   /* Vercel's signature: white IS the primary */
--primary-fg:       #060607
--accent:           #00DC82   /* electric green — only for "live"/"healthy" */
--success:          #00DC82
--warning:          #F5A524
--danger:           #FF5C5C
--chart-1:          #FFFFFF
--chart-2:          #00DC82
--chart-3:          #F5A524
--chart-4:          #7DD3FC
--chart-5:          #C084FC
```

- **Type families**: UI = `Geist Variable`, `Geist`, `Inter` (Vercel). All numerics = `Geist Mono Variable` — every number on screen is mono-tabular. Scale: 11/16 axis-label, 12/18 caption, 13/20 body, 14/22 body-lg, 18/26 section-title, 24/30 page-title, 36/40 KPI hero, 56/60 hero-XL.
- **Weights**: 400 body · 500 emphasis · 600 KPI hero. **No 700.** Mono is always 500.
- **Letter-spacing**: -0.011em on KPI hero (Vercel signature). +0.04em on uppercase 11px labels. Otherwise 0.
- **Spacing**: 4 / 8 / 12 / 16 / 24 / 32 / 48. Tile padding 20. Table row 32. Section gutter 32. Page gutter 32.
- **Radius**: 8 on all surfaces, 4 on inputs, 0 on table cells. Pills are 6px-radius rectangles (chiclets, not rounded pills).
- **Shadow**: `--shadow-1: 0 1px 0 #FFFFFF06 inset, 0 0 0 1px var(--border)`. The 1px inner-top-highlight is the Vercel hallmark. Drilldown: `0 24px 48px -12px #00000080`.
- **Density**: 32px table rows, 20px tile padding.
- **Ticker**: kubectl-logs aesthetic — fixed-height (240px) scrolling pane with mono 12px lines: `[12:43:07] MC-453221  BOOKED  Atlanta→Dallas  $2,840  CHS=84`.

### 1.3 Bloomberg Pit (TELEMETRY tab + drilldown panel) — verbatim from `themes-v2-fintech-lens.md` §B
```
--bg:               #0A0A0A
--surface:          #0F0F0F
--surface-elevated: #161616
--border:           #2A2A2A
--border-strong:    #3D3D3D
--fg:               #E6E6E6
--fg-muted:         #7A7A7A
--primary:          #FFB800   /* Bloomberg amber */
--primary-fg:       #0A0A0A
--accent:           #FFB800
--success:          #00D26A
--warning:          #FFB800
--danger:           #FF3838
--chart-1:          #FFB800
--chart-2:          #00D26A
--chart-3:          #FF3838
--chart-4:          #5BC0EB
--chart-5:          #E6E6E6
```

- **Single mono family for everything**: `IBM Plex Mono`, `Berkeley Mono`, `JetBrains Mono`, ui-monospace — weights 400 and 600 only. No serif, no proportional sans anywhere.
- **Scale**: 10 / 11 / 12 / 13 / 14 / 18 / 24. **No size above 24px.** Hero numerics are 24px mono / 600.
- **All-caps for ALL labels and headings**.
- **Spacing**: 2 / 4 / 8 / 12 / 16. Cap is 16px. Quadrant gutter 1px. KPI row gap 4px.
- **Radius**: 0. Everything square.
- **Shadow**: none, ever. Border-only.
- **Pit amber stays** — deliberate "instrumentation area" signal. Does NOT rebrand to Freight Terminal accent-green (per locked sub-question 7).
- **24px row tables, 11px mono.** Alternating row backgrounds. Numerics colored by sign (no neutral state).
- **Status pill**: single uppercase letter in 16px square (`B`/`N`/`F` with green/amber/red bg).
- **Continuous ticker bar** (28px-tall band) — the theme's signature. `transform: translateX` over 90s.

### 1.4 Sigma Spreadsheet pattern (CALLS + CARRIERS tabs) — verbatim from `themes-v2-bi-lens.md` §4
- **Footprint**: Calls tab + Carriers tab.
- **Calls tab top**: frozen merged-cell KPI band, 6 equal-rank with in-cell horizontal data bars.
- **Overview tab**: does NOT use Sigma's KPI band — keeps Freight Terminal's asymmetric KPI strip (1 headline 56px tile + 3 smaller).
- **Adaptations**: cell gridlines `#232328` on `--surface`; in-cell data bars in `#00DC82` (positive) and `#FF5C5C` (negative); CHS color scale (red→amber→green) at 14% opacity backgrounds.
- **Row height**: 22px (Excel-tight). Cell padding 4px vertical × 8px horizontal.
- **Typography**: `Aptos Narrow`, `Aptos`, `Calibri` (proportional with `font-feature-settings: "tnum" 1`). Cell text 12px. KPI hero 28px sans bold. Header 11px sans semibold caps with +0.08em letter-spacing.
- **Cell formatting**: in-cell data bars on rate columns; CHS color-scale 0-100 cell-background (red → yellow → green); outcome icon-set (✓ / ⋯ / ✗) at cell left.
- **Drill-down**: bottom split-pane with draggable horizontal divider (50/50 vertical split).

### 1.5 Loadboard Live Cmd-K palette (GLOBAL) — verbatim from `themes-v2-modern-saas-lens.md` §4
- 640px floating panel, 12px radius, primary-color glow shadow.
- Fuzzy-matched results: tabs, carriers (by MC or name), calls (by call_id or timestamp), lanes.
- `⌘K` opens, arrow keys navigate, Enter executes.
- Mounted at root; doesn't replace nav bar.

### 1.6 Overview central widget (LOCKED 2x2 chart grid)
Replaces the Margin Captured chart per `project_dashboard_design_v3_locked.md` (still valid per the composite).
- **TL**: Booked-rate position-on-distribution (violin/box of listed rates, booked-rate dots overlaid)
- **TR**: Outcome funnel with $ overlay (calls → verified → searched → quoted → negotiated → booked)
- **BL**: Negotiation-effectiveness scatter (rounds × delta-from-floor, dots = bookings)
- **BR**: Lane-margin heatmap (origin region × dest region grid)
- **DROPPED**: time-of-day rate elasticity (least MVP-actionable)
- Render style: Vercel — 1.5px white series lines on `--surface`, Geist Mono axis labels at 11px, no fill, single-color series with accent-green only for the "good" series.

### 1.7 Telemetry tab content (Pit quadrants) — locked by sub-question 2
- Token-spend trend (input + output separately)
- Token-cost-per-booking
- Dead-air gap distribution histogram
- Time-to-first-carrier-utterance histogram
- Tool-call sequence + per-tool latency histogram (p50/p70/p90)
- Per-turn sentiment trajectory
- Transcript search box (CloudWatch-style: single search + chip filters `MC=`, `outcome=`, `date>=`, free-text → Pit-style result rows)

### 1.8 Build composition rules — verbatim from memory
- ONE base `globals.css` carries Freight Terminal tokens
- Pit tab gets a `.pit-surface { ... }` scope swap (IBM Plex Mono, amber, 0 radius)
- Sigma table gets a `.sigma-grid` component with own row height, gridline borders, in-cell data-bar primitives — slots into Freight Terminal pages
- Cmd-K is mounted-at-root portal triggered globally

Pit `.pit-surface` swap shape per `docs/design/dashboard-widget-integration-plan.md`:
```css
.pit-surface {
  --background: 0 0% 4%;
  --foreground: 0 0% 90%;
  --card: 0 0% 6%;
  --primary: 41 100% 50%;     /* amber, Pit signature */
  --chart-1: 41 100% 50%;
  --chart-2: 142 100% 41%;
  --chart-3: 0 100% 61%;
  --chart-4: 200 70% 64%;
}
```

### 1.9 8 sub-question defaults LOCKED (verbatim)
1. Pit lives BOTH in a Telemetry tab (cross-call) AND in Calls drilldown (single-call panel).
2. Telemetry tab = all 7 quadrants enumerated above.
3. Transcript search = CloudWatch-style single box + chip filters → Pit-style result rows.
4. Sigma footprint = Calls + Carriers (not everywhere).
5. KPI band: Sigma frozen-merged-cell on Calls top; Freight Terminal asymmetric strip on Overview.
6. 2x2 charts = Vercel-style (white series, accent-green on "good").
7. Pit amber stays as instrumentation signal (does NOT rebrand to FT accent-green).
8. Cmd-K palette in.

### 1.10 Files that exist on disk for this theme round
- `docs/design-explorations/themes-v2-bi-lens.md` (rich Sigma spec)
- `docs/design-explorations/themes-v2-fintech-lens.md` (rich Pit spec)
- `docs/design-explorations/themes-v2-modern-saas-lens.md` (rich Freight Terminal + Cmd-K spec)
- `docs/design-explorations/themes-v2-preview.html` — clickable preview HTML showing the composite live (referenced by memory; not opened in this audit pass — described as the visual A/B that drove the lock)
- v1 rejected (kept for record): `docs/design-explorations/themes-9-dark.md` + `docs/design-explorations/themes-preview.html`

### 1.11 Current dashboard tokens vs locked theme — REALITY CHECK
Source: `dashboard/src/app/globals.css` lines 68-118 (`.dark` block, currently shipping).
- Currently shipping **"Dark Ops Console"** palette (per `docs/dashboard-v2-research/05-branding-design-tokens.md` §2.1) — `--background: 222 24% 8%` (#0F141C), `--primary: 36 95% 56%` (amber), `--chart-1: 36 95% 56%`. NOT Freight Terminal.
- Currently shipping **Freightline** brand mark per `dashboard/src/components/branding/AcmeMark.tsx` — three stacked freight bars in safety-orange + slate. Locked 2026-04-30 morning per `project_dashboard_improvements_plan.md`. Predates the night theme-composite lock.
- **Conflict**: Freight Terminal's primary is white (`#FFFFFF`); current `--primary` is amber; current header brand is "ACME LOGISTICS" with safety-orange Freightline mark. The composite locked at night supersedes the Dark Ops Console palette wired in code. **No code changes have landed for the composite yet.**

---

## 2. Locked telemetry widgets

Source: `project_telemetry_widgets_locked.md` (LOCKED 2026-04-30 night). Quoted verbatim where possible.

### 2.1 Three telemetry widgets on the Pit Telemetry tab
1. **Voice Agent (BIG, primary)** — full conversation tokens (computed Python-side on transcript), RPM/TPM over time, latency percentiles (p50/p70/p90/p99). User-editable: pick which series + which percentiles to render.
2. **Extract Call Details (secondary, editable)** — bound exact tokens from HR @ picker (input/output/reasoning/cached/uncached); RPM/TPM derivable from call volume × per-call totals; latency from HR run details. Field picker: choose which fields to chart, filter range.
3. **Case Health Score (secondary, editable)** — same shape as Extract. Independent picker so user can compare extracts side-by-side.

### 2.2 Universal widget controls
- Filterable by date range (sticky global filter)
- Percentile selectors (multi-select: p50, p70, p90, p99)
- Time bucket: 1m / 5m / 15m / 1h / 1d (RPM and TPM are bucket-dependent)
- Field picker dropdown per widget (which token columns to plot)

### 2.3 Calculation rules
- **RPM**: `count(calls_log) GROUP BY date_trunc('minute', created_at)`. Bucketable to 1m/5m/15m/1h/1d.
- **TPM**: `sum(extract_input + extract_output + chs_input + chs_output + agent_input_estimate + agent_output_estimate) GROUP BY date_trunc(bucket, created_at)`.
- **Latency percentiles**: quantile() over the latency column for the filtered window. Done in Python per existing `dashboard_aggregations.py` `_percentile()` helper.
- **Voice agent token estimate** (Python on transcript):
  - Iterate transcript turns
  - For each turn with role=='assistant' or role=='user': tiktoken count → add to input_tokens (system + user) and output_tokens (assistant) appropriately
  - For role=='tool': count separately as `tool_input_tokens` and `tool_output_tokens`
  - Total: `agent_total = agent_input + agent_output + tool_input + tool_output`

### 2.4 AWS-CloudWatch-style chrome (per-panel)
Verbatim:
- Title bar at top (mono uppercase 11px, amber). Top-right: statistic chiclet (Sum/Avg/Min/Max/p50/p70/p90/p99 — segmented), period chiclet (1m/5m/15m/1h/6h/1d), overflow-menu for "View source / Add to dashboard / Edit math".
- No card shadow. 1px hairline border on `--border` (Pit `#2A2A2A`).
- Bottom-right: timestamp of last update + "live" green dot when auto-refresh is on.
- Legend at panel bottom: colored 8px square + metric name + current value (mono, tabular). Multiple metrics overlay → multiple legend rows.

### 2.5 Multi-line overlay + crosshair sync
- Each panel can host MULTIPLE metrics overlaid on a shared time axis.
- Different colors per metric: amber (`#FFB800`), green (`#00D26A`), red (`#FF3838`), cyan (`#5BC0EB`), purple (`#A855F7`).
- 1.5px lines, no fill on overlays.
- **Crosshair sync (CloudWatch UX win)**: hovering ANY panel draws a vertical hairline at that timestamp on EVERY panel simultaneously. Tooltip on each panel shows the value at that timestamp. Legend "current value" cells flash to that hovered value for the hover duration. Implemented via shared cursor state in a parent context provider.

### 2.6 Page-level controls (top of Telemetry tab)
- Auto-refresh toggle: off / 10s / 30s / 1m / 2m / 5m. Default off; "live" mode opt-in.
- Time range: relative (last 1h / 3h / 12h / 1d / 3d / 1w / custom). Inherits from sticky global filter; per-page override allowed here.
- Period: global default (5m), each panel can override.
- Refresh button (manual, with spinning icon when fetching).

### 2.7 Y-axis annotations
- Threshold lines: 1px dashed `--warning` / `--danger` horizontal lines.
- Examples: RPM > 100 → warning band; latency p99 > 3s → danger band.
- Annotations are static config for MVP; dynamic-from-Twin in Tier-2.

### 2.8 Panel grid
- 2-column on desktop, 1-column on tablet/mobile.
- Voice Agent BIG widget = 2 cols wide (full-row), height ~360px.
- Extract + CHS = 1 col each, side-by-side, height ~280px.
- Latency percentile panel = 2 cols wide below (RPM | TPM stacked, latency overlay underneath).

### 2.9 Numeric rendering rules
- All numbers on Telemetry tab = IBM Plex Mono (Pit primary face).
- Tabular numerals (`font-feature-settings: "tnum" 1`).
- Right-aligned in tables; left-aligned in tooltips with "label: value" pairs.
- Sign coloring: positive deltas in `--success`, negative in `--danger`. Zero in `--fg-muted`.

### 2.10 Empty / loading states
- Loading: animated 1px hairline scanning left-to-right across panel — quiet, no spinner.
- No data: "—" centered in panel body, mono. No "no data available" prose.
- Error: red `[ERR]` chip in title bar + last-known value with stale timestamp; the panel doesn't go blank.

### 2.11 Data source matrix
| Metric | Source | Status |
|---|---|---|
| Extract input/output/reasoning/cached tokens | HR @ picker → calls_log columns (10 added per token_usage_capture) | DDL queued |
| CHS input/output/reasoning/cached tokens | HR @ picker → calls_log columns | DDL queued |
| Voice agent token estimate (input + output per turn) | Python on `calls_log.transcript` (tiktoken `o200k_base`); separate agent-role and tool-role turn totals | Python script TBD |
| Per-call latency (p70 + p90) | HR Voice Agent var → calls_log column (existing, currently broken — F8) | Blocked on F8 fix |
| Per-call latency p50 + p99 | HR run details API per-node start_at/completed_at | Blocked on MCP perms; or compute from per-turn latencies if Voice Agent exposes them |
| RPM (calls per minute) | calls_log.created_at, bucketed | Done dashboard-side |
| TPM (tokens per minute) | sum(token columns + voice estimate) bucketed | Done dashboard-side once token columns land |

### 2.12 Current state of telemetry components on disk
Files present at `dashboard/src/components/telemetry/`:
- `category-widget-card.tsx`
- `latency-percentiles-card.tsx`
- `rpm-tpm-chart.tsx`
- `telemetry-empty-state.tsx`
- `telemetry-kpi-strip.tsx`

These are wired in `dashboard/src/app/dashboard/page.tsx` (Telemetry tab inside the Tabs component). Voice Agent BIG widget, Extract widget, and CHS widget files **named in `docs/design/dashboard-widget-integration-plan.md` line 28-34 (`voice-agent-widget.tsx`, `extract-widget.tsx`, `chs-widget.tsx`, `telemetry-filters.tsx`, `telemetry-crosshair.tsx`, `telemetry-types.ts`) are NOT present.** Crosshair sync, auto-refresh toggle, and Pit `.pit-surface` swap also not implemented.

---

## 3. Locked Call Logs tab spec

Source: `project_dashboard_calls_logs_tab.md` (LOCKED 2026-04-30).

### 3.1 Main 9-column table — verbatim
The Call Logs dashboard tab main-list table renders ONLY these 9 columns, in this exact order:
1. `call_id`
2. `mc_number`
3. `carrier_name`
4. `notes`
5. `call_outcome`
6. `lane_origin`
7. `lane_dest`
8. `sentiment`
9. `case_health_score`

Rationale (verbatim): "User's lean-design instinct: the main row should answer 'who called, what happened, and how it went' at a glance. Everything else is detail-on-demand."

### 3.2 Drilldown rules — verbatim
- Click on a row → drilldown / detail view opens with ALL 32 calls_log columns:
  - identity (id, created_at)
  - caller (callback_phone, fmcsa_eligibility_failure_reason)
  - quality (audit_remarks)
  - session (hangup_reason, room_name, status)
  - token usage (10 cols Extract + CHS)
  - telemetry (duration, intermediate_response_count, p70/p90 latency)

### 3.3 Transcript widget — verbatim
"transcript gets its own widget on the drilldown — not inline text. Probably a code-block / accordion / dedicated transcript pane that renders the JSON role/content turns nicely. Don't dump as raw cell text."

### 3.4 Touch list when implementing — verbatim
- `dashboard/src/components/calls-table.tsx` — reduce to 9-column display
- `dashboard/src/components/call-detail/` — add/expand the drilldown view + transcript widget
- `dashboard/src/components/call-detail/call-telemetry.tsx` — already shows p70/p90 + intermediate_response_count (post v2 fix)
- `dashboard/src/lib/api-client.ts` — `getCall(call_id)` returns full CallDetailRecord; list endpoint can stay full-projection or split to lightweight per perf
- Token-usage drilldown widget — natural fit for the Pit Telemetry tab pattern (RPM/TPM/percentiles per `project_telemetry_widgets_locked.md`)

### 3.5 Reality check — current calls-table.tsx
Source: `dashboard/src/components/calls-table.tsx` lines 46-55. The `COLUMNS` array currently renders 8 columns: `created_at`, `mc_number`, `carrier_name`, `outcome`, `sentiment`, `case_health_score`, `apply_rate`, `duration_seconds`. **Drift vs lock**:
- `call_id` missing from main table (is in row key only)
- `notes` column missing (also blocked on Twin DDL — see §7)
- `lane_origin` / `lane_dest` missing
- `apply_rate` and `duration_seconds` are extras the lock said go to drilldown only

The drilldown page (`dashboard/src/app/dashboard/calls/[call_id]/page.tsx`) DOES render `<CallHeader>`, `<CallKpiCards>`, `<CallAuditRemarks>`, `<CallBookingsTable>`, `<CallTelemetry>`, `<CallTranscriptToggle>`, plus a "View all calls for MC X" link — broadly aligned with the spec, but does not yet render all 32 columns and the transcript widget is a `<CallTranscriptToggle>` not a code-block-style accordion.

---

## 4. Outstanding dashboard polish — categorized by area

Each row: short title — source memory file — status — area tag — effort (S ≤ 30 min / M ≤ 2 hr / L ≥ half day).

### 4.1 Theme + branding
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| TB-1 | Apply Freight Terminal `:root` tokens to globals.css (replace Dark Ops palette) | `project_dashboard_theme_composite_locked.md` §1.10, `globals.css` reality | LOCKED, not implemented | Dashboard-only | M |
| TB-2 | Add `.pit-surface` scope swap class for Telemetry tab | `dashboard-widget-integration-plan.md` §"Theme switch readiness" | LOCKED, not implemented | Dashboard-only | S |
| TB-3 | Add `.sigma-grid` component primitive (row height 22px, in-cell data-bar primitives, gridlines) for Calls + Carriers tabs | `project_dashboard_theme_composite_locked.md` §1.4 + §1.8 | LOCKED, not implemented | Dashboard-only | M |
| TB-4 | Mount global Cmd-K palette portal (Loadboard Live spec, fuzzy results: tabs/carriers/calls/lanes) | `project_dashboard_theme_composite_locked.md` §1.5 | LOCKED, not implemented | Dashboard-only | L |
| TB-5 | Replace AcmeMark Freightline mark with theme-derived logo | `LOGO_OPTIONS.md`, `project_dashboard_improvements_plan.md` | LOCKED-conflict (see §8) | Dashboard-only | S |
| TB-6 | Add Geist + Geist Mono fonts (per Freight Terminal type spec) | `themes-v2-modern-saas-lens.md` §3 | LOCKED, not implemented | Dashboard-only | S |
| TB-7 | Add IBM Plex Mono font for Pit telemetry surface | `themes-v2-fintech-lens.md` §B | LOCKED, not implemented | Dashboard-only | S |
| TB-8 | Replace 2x2 hero chart layout (Margin-rate-position / Outcome-funnel / Negotiation-scatter / Lane-margin-heatmap) | `project_dashboard_design_v3_locked.md` §"Overview central widget" | LOCKED, not implemented (current hero is 1× EffectiveDeltaChart) | Dashboard-only | L |
| TB-9 | Replace docs-style copy ("Inbound carrier desk · last 7 days", "Distinct booking rows in Twin", etc.) | `project_dashboard_v2_requirements.md` §"Hard requirements" #4 | DEFERRED 2026-04-29 (per `project_dashboard_polish_deferred.md`) | Dashboard-only | S |
| TB-10 | Redact variable names in chart titles/labels — never `mc_number` / `case_health_score` / `pitched_loadboard_rate` | `project_dashboard_v2_design_directives.md` directive #4 | DEFERRED 2026-04-29 | Dashboard-only | S |
| TB-11 | Drop "Why this matters" subtitles | `project_dashboard_v2_design_directives.md` directive #5 | DEFERRED 2026-04-29 | Dashboard-only | S |
| TB-12 | Multi-tier color hierarchy + accessible contrast | `project_dashboard_v2_design_directives.md` "Postpone (full-enterprise)" | DEFERRED 2026-04-29 | Dashboard-only | M |

### 4.2 Layout + density
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| LD-1 | KPI strip layout: Sigma frozen-merged-cell band on Calls top, Freight Terminal asymmetric strip (1×56px headline + 3 smaller) on Overview | `project_dashboard_theme_composite_locked.md` §1.9 sub-q5 | LOCKED, not implemented (current is 6 equal cards) | Dashboard-only | M |
| LD-2 | Fix tablet KPI grid breakpoint — `lg:grid-cols-3 xl:grid-cols-6` | `dashboard-chart-review.md` "KPI strip — overall" | IDEA | Dashboard-only | S |
| LD-3 | Wire spark + delta on KPI #2 Bookings, #3 Booked rate, all Operational tab cards (API already returns) | `dashboard-chart-review.md` Top-3 #2; `project_dashboard_improvements_plan.md` Goliath #2 | IDEA — high-impact ~30 min | Dashboard-only | S |
| LD-4 | Header sticky to top with backdrop blur + 1px hairline (already implemented) | `dashboard/src/components/header.tsx` | DONE | — | — |
| LD-5 | Sticky DateRangePicker sub-header bar | `dashboard/src/app/dashboard/layout.tsx` line 25 | DONE | — | — |

### 4.3 KPI strip + filters
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| KF-1 | Tier-1 calls filters (date / outcome multiselect / sentiment multiselect / MC text) — `useCallsFilters` hook + URL state | `project_dashboard_improvements_plan.md` Tier-1 | DONE this session | Dashboard-only | — |
| KF-2 | Tier-2 advanced query builder ("Advanced search" expandable below simple bar; LIKE / EQUALS / NOT EQUALS / AND/OR; encode predicate tree in single query param) | `project_dashboard_improvements_plan.md` Tier-1 #2 | IN-PROGRESS (sub-agent shipped `advanced-query-builder.tsx`) | Dashboard-only | M |
| KF-3 | Preset time-window chips: 1d / 1w / 2w / 1mo / 6mo / 1y / All | `project_dashboard_v2_design_directives.md` directive #1 | LOCKED (intermediate scope) | Dashboard-only | S |
| KF-4 | Cross-filter on chart click (click outcome bar → all charts filter) | `project_dashboard_v2_design_directives.md` directive #6 | DEFERRED to full-enterprise | Dashboard-only | L |
| KF-5 | Filterable dashboard endpoints (date/outcome/sentiment/MC/lane) — server WHERE clauses + cache key expansion | `project_dashboard_dynamic_filtering.md` | DEFERRED Tier-2 (~2hr) | needs-FastAPI | M |
| KF-6 | Filter persistence via URL params (already pattern-locked per ADR-011) | `project_dashboard_hr_twin_dependencies.md` Dashboard-only list | DONE | — | — |

### 4.4 Calls table + drilldown
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| CT-1 | Reduce calls-table to the locked 9 columns in exact order | `project_dashboard_calls_logs_tab.md` §3.1 | LOCKED, not implemented (drift documented in §3.5) | Dashboard-only (notes col blocked on Twin) | M |
| CT-2 | Add `lane_origin` / `lane_dest` to calls-table | `project_dashboard_calls_logs_tab.md` | LOCKED, blocked on calls_log having lane fields OR client-side join to bookings/loads | needs-Twin OR client-join | S+ |
| CT-3 | Drilldown shows ALL 32 calls_log columns | `project_dashboard_calls_logs_tab.md` §3.2 | PARTIAL (current renders KPI cards, audit remarks, bookings, telemetry, transcript toggle, related calls) | Dashboard-only | M |
| CT-4 | Transcript-as-its-own-widget (code-block / accordion / dedicated pane that renders JSON role/content turns nicely) | `project_dashboard_calls_logs_tab.md` §3.3 | PARTIAL (current is `<CallTranscriptToggle>` — needs review for "renders JSON role/content turns nicely") | Dashboard-only | M |
| CT-5 | Calls drilldown WAF call_id bug — get_call_by_id + bookings_for_call edited to fetch+filter Python-side | `project_dashboard_improvements_plan.md` DONE list; `project_resume_2026_04_30_post_compact.md` "critical pending" | FIX IN CODE, NOT REDEPLOYED (blocking demo) | needs-FastAPI redeploy | S |
| CT-6 | Long-term WAF fix: query Twin via integer PK instead of UUID | `project_dashboard_improvements_plan.md` Tier-2 | DEFERRED Tier-2 | needs-Twin / FastAPI | M |
| CT-7 | Active-calls indicator: replace `current_node` jargon with friendly label (or omit) | `project_dashboard_improvements_plan.md` Goliath #6 | IDEA | Dashboard-only | S |
| CT-8 | Sign-convention conflict: `EffectiveDeltaChart` + `EconomicsCards` treat NEGATIVE $ as good (margin captured below list); `SalesRepCard` + `CallDetail` treat POSITIVE $ as good | `dashboard-chart-review.md` T-6, `project_dashboard_improvements_plan.md` Goliath #1 | IDEA (must fix before submission) | Dashboard-only | M |
| CT-9 | Triple-duplicate outcome distribution (Funnel-tab horizontal bar + Quality-tab donut + carrier-detail plain list) — rename Funnel→"Outcomes", drop Quality donut | `project_dashboard_improvements_plan.md` Goliath #3 | IDEA (single biggest "looks unfinished" tell) | Dashboard-only | S |
| CT-10 | Carriers rollup table built but no list page exists — build the page (locked per `resume`) | `dashboard-chart-review.md` T-3, `project_dashboard_improvements_plan.md` Goliath; `resume` decision | LOCKED, BUILD it | Dashboard-only | M |
| CT-11 | Wire `chs_distribution` (returned by API but unused) to Quality tab CHS-specific chart | `dashboard-chart-review.md` "Other findings" | IDEA | Dashboard-only | S |
| CT-12 | KPI: append "/100, ≥70 passing" hint + colour-red below 70 | `dashboard-chart-review.md` KPI #6 | IDEA | Dashboard-only | S |

### 4.5 Telemetry tab refinement
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| TR-1 | Build Voice Agent BIG widget (full-conversation tokens, RPM+TPM overlay, latency p50/p70/p90/p99, percentile multi-select, time bucket) | `project_telemetry_widgets_locked.md` §1, `dashboard-widget-integration-plan.md` §"Widget components" | LOCKED, not implemented (file `voice-agent-widget.tsx` missing) | Dashboard-only | L |
| TR-2 | Build Extract Call Details secondary widget (5 token fields + RPM/TPM/latency, field picker dropdown) | `project_telemetry_widgets_locked.md` §1.2 | LOCKED, not implemented (`extract-widget.tsx` missing) | Dashboard-only | M |
| TR-3 | Build CHS secondary widget (clone of Extract with chs_* columns) | `project_telemetry_widgets_locked.md` §1.3 | LOCKED, not implemented (`chs-widget.tsx` missing) | Dashboard-only | M |
| TR-4 | Implement crosshair sync (parent context provider; vertical hairline drawn across all panels on hover) | `project_telemetry_widgets_locked.md` §2.5; `dashboard-widget-integration-plan.md` §"Reusable primitives" | LOCKED, not implemented (`telemetry-crosshair.tsx` missing) | Dashboard-only | M |
| TR-5 | Auto-refresh toggle (off / 10s / 30s / 1m / 2m / 5m) on Telemetry tab | `project_telemetry_widgets_locked.md` §2.6 | LOCKED, not implemented | Dashboard-only | S |
| TR-6 | Time-range relative selector (1h/3h/12h/1d/3d/1w/custom) on Telemetry tab | `project_telemetry_widgets_locked.md` §2.6 | LOCKED, not implemented | Dashboard-only | S |
| TR-7 | Y-axis threshold annotations (RPM > 100 warning, latency p99 > 3s danger) — static config for MVP | `project_telemetry_widgets_locked.md` §2.7 | LOCKED, not implemented | Dashboard-only | S |
| TR-8 | Hand-roll a `<ToggleGroup>` mini-component (~20 LOC) for percentile multi-select; reuse Button styles | `dashboard-widget-integration-plan.md` §"shadcn dependencies" | LOCKED, not implemented | Dashboard-only | S |
| TR-9 | Add 3 new FastAPI endpoints: `GET /v1/telemetry/voice-agent`, `/v1/telemetry/extract`, `/v1/telemetry/chs` | `dashboard-widget-integration-plan.md` §"API contract additions" | LOCKED, not implemented | needs-FastAPI | M |
| TR-10 | Build `api/app/services/transcript_telemetry.py` per design spec | `docs/design/transcript-telemetry-module.md` | LOCKED, not implemented | needs-FastAPI | L |
| TR-11 | Add 4 token-estimate columns OR (recommended) compute on-demand in `transcript_telemetry.py` with 60s TTL cache | `project_telemetry_widgets_locked.md` §"HR + Twin work needed" | LOCKED, not implemented | needs-FastAPI | M |
| TR-12 | Update `dashboard/src/components/call-detail/call-telemetry.tsx` to source p70/p90 from computed transcript values (not raw NULL columns) | ADR-012 §5; `project_dashboard_latency_compute_locked.md` | LOCKED, not implemented | Dashboard-only + needs-FastAPI | M |
| TR-13 | Probe HR `monitor_runs` MCP / Web Call run-details API on first real run_id; document actual shape; if per-node timestamps available, implement Phase 2 latency (real per-tool ms) | ADR-012 §"Phase 2"; `project_dashboard_latency_compute_locked.md` Phase 2 | DEFERRED | Dashboard-only + needs-HR perms | M |
| TR-14 | Telemetry tab 2-col grid layout: Voice Agent BIG (2 cols, ~360px), Extract+CHS side-by-side (~280px), latency below | `project_telemetry_widgets_locked.md` §2.8 | LOCKED, not implemented | Dashboard-only | S |
| TR-15 | Telemetry empty/loading states (1px hairline scanning loading; "—" centered no-data; red `[ERR]` chip on error) | `project_telemetry_widgets_locked.md` §2.10 | LOCKED, not implemented (current empty-state is `<TelemetryEmptyState>`) | Dashboard-only | S |
| TR-16 | Pit Telemetry tab quadrant content: token-spend trend, token-cost-per-booking, dead-air gap histogram, time-to-first-utterance histogram, tool-call sequence + per-tool latency p50/p70/p90, per-turn sentiment trajectory, transcript search box | `project_dashboard_theme_composite_locked.md` §1.7 | LOCKED, not implemented (most quadrants depend on per-turn timestamps — blocked) | Dashboard-only + Phase-2 latency | L |
| TR-17 | Replace NULL `intermediate_response_count` / `p70_latency_ms` / `p90_latency_ms` rendering with computed-from-transcript values + tooltip "computed from transcript" | ADR-012 §"What changes" | LOCKED, not implemented | Dashboard-only + needs-FastAPI | M |

### 4.6 Quality / Operational / Economics tabs
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| QO-1 | Quality tab missing CHS-specific chart (despite being the quality tab) — `chs_distribution` returned by API but unused | `project_dashboard_improvements_plan.md` Goliath; `dashboard-chart-review.md` "Other findings" | IDEA | Dashboard-only | S |
| QO-2 | Replace agreed_rate histogram (makes no sense at low N) with rate-vs-CHS quadrant or top-rates list | `project_dashboard_v2_design_directives.md` directive #8 | DEFERRED 2026-04-29 | Dashboard-only | M |
| QO-3 | avg_loadboard_rate empty: pitched_loadboard_rate is null on every row — fix HR Workflow Dump binding OR remove metric | `project_dashboard_v2_design_directives.md` directive #7 | DEFERRED to HR fix | needs-HR | S |
| QO-4 | Append Listed-rate-avg KPI with `(median)` chip (mean is fragile to outliers) | `dashboard-chart-review.md` KPI #4 | IDEA | needs-FastAPI agg + Dashboard | M |
| QO-5 | Inline margin sub-line under Booked-rate-avg KPI (e.g., "−$83 vs list, 3.2 %") | `dashboard-chart-review.md` KPI #5 | IDEA | Dashboard-only | S |
| QO-6 | Add Booking-rate target band on KPI #3 spark via Recharts `<ReferenceLine>` | `dashboard-chart-review.md` KPI #3 | IDEA | needs-FastAPI agg | M |
| QO-7 | Operational tab: render any of the deferred contact-support / agent-monitoring metrics (call_duration histogram, disconnection_rate, abandoned_within_30s, avg_time_to_MC_capture, transcript-empty rate, p70/p90 latency by hour-of-day, assistant_cut_message_ratio, num_user_filler_messages, tool-call success, num_tool_calls, rounds-distribution, CHS distribution buckets, outcome × CHS heatmap) | `project_post_mvp_dashboard_metrics.md` | DEFERRED post-MVP | Dashboard-only + may-need-Twin schema | L |
| QO-8 | Skipped 7 dashboard endpoint integration tests (`test_funnel_endpoint`, `*_zero_state`, `test_economics_*`, `test_operational_*`, `test_quality_endpoint`) — IMPL-4 KPI Cards added sparkline + prior-period helpers, breaking pre-v2 mock fixtures | `project_dashboard_endpoint_tests_tier2.md` | DEFERRED Tier-2 (~30-60 min) | needs-FastAPI | M |
| QO-9 | Replace `<EffectiveDeltaChart>` hero (1x1) with 2x2 chart grid (booked-rate position-on-distribution, outcome funnel with $ overlay, negotiation-effectiveness scatter, lane-margin heatmap) | `project_dashboard_design_v3_locked.md`; restated in composite §1.6 | LOCKED, not implemented | Dashboard-only + may-need-FastAPI | L |

### 4.7 Real-time / SSE / freshness
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| RT-1 | Webhook + SSE hybrid freshness (Option C: `call.ended` webhook → FastAPI `/v1/events/call-ended` → invalidate cache → SSE → `router.refresh()` + 5min ISR fallback) | ADR-009; `project_dashboard_freshness_options.md` | DONE — see `dashboard/src/components/live-refresh.tsx` + `app/api/events/{session,stream}/route.ts` + `api/app/routers/events.py` | — | — |
| RT-2 | HR-side webhook config: `Workflow → Webhooks → call.ended` → URL + Bearer + retries (defaults 2×10s×2×100s) | ADR-009 §4 | NEEDS USER (HR UI) | needs-HR | S (user-time) |
| RT-3 | Active-call detection via HR Monitor API (webhook fires only on `call.ended`, so we need a different mechanism) — `GET /v1/calls/active` endpoint, cache 10s, live indicator | `project_dashboard_v2_requirements.md` §"Hard requirements" #3 | PARTIAL — `app/api/calls/active/route.ts` + `<ActiveCallsIndicator />` exist; verify HR Monitor wiring | needs-HR + Dashboard | M |
| RT-4 | Multi-machine drift escape hatch: Redis pubsub when scaling beyond `min_machines=1` | ADR-007 §3 / ADR-009 §3; `project_post_mvp_scalability_availability.md` | DEFERRED Tier-2 | infra | L |
| RT-5 | Real-time negotiation hook: HR webhook per negotiation round → SSE → sales-rep dashboard. Payload includes carrier_offer + final_floor + urgency_tier | `project_realtime_negotiation_hook.md` | DEFERRED post-MVP | needs-HR + Dashboard | L |
| RT-6 | Live indicator pulse synced when SSE connected (already implemented in `<LiveRefresh />` polling state) | `dashboard/src/components/live-refresh.tsx` | DONE | — | — |

### 4.8 Performance / caching
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| PC-1 | Two-layer in-process TTL cache: Next.js `revalidate=30` + FastAPI `cachetools.TTLCache(30s)` | ADR-007; `project_dashboard_caching_strategy.md` | DONE; `revalidate=300` now post-ADR-009 | — | — |
| PC-2 | `invalidate_dashboard_cache()` hook exposed for webhook | ADR-007 §"What's done" | DONE; called from webhook receiver per ADR-009 | — | — |
| PC-3 | Tab switching feels sluggish — wrap data fetches in `<Suspense>` boundaries with skeletons (page chrome renders instantly, panels hydrate as data lands) | `project_dashboard_polish_deferred.md` "Performance items deferred" #1 | DEFERRED Tier-2 | Dashboard-only | M |
| PC-4 | Parallelize multiple Twin queries inside each aggregation helper via `asyncio.gather` (current is sequential `await`) | `project_dashboard_polish_deferred.md` #2 | DEFERRED Tier-2 | needs-FastAPI | M |
| PC-5 | Add client-side cache (SWR / React Query) for tab-to-tab navigation within a session | `project_dashboard_polish_deferred.md` #3 | DEFERRED Tier-2 | Dashboard-only | M |
| PC-6 | Pre-fetch on tab-link hover (Next.js Link does this; verify enabled) | `project_dashboard_polish_deferred.md` #4 | TODO verify | Dashboard-only | S |
| PC-7 | Move dashboard cache to Redis when multi-machine | `project_dashboard_polish_deferred.md` #5 / `project_post_mvp_scalability_availability.md` | DEFERRED Tier-2 | infra | L |
| PC-8 | Pre-fetch bookings endpoint on overview render so `/dashboard/sales` is warm | `project_dashboard_polish_deferred.md` #6 | DEFERRED Tier-2 | Dashboard-only | S |

### 4.9 Accessibility
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| AX-1 | Dark/light mode polish — verify all charts legible in both | `project_dashboard_hr_twin_dependencies.md` Dashboard-only #8 | DEFERRED | Dashboard-only | M |
| AX-2 | Loading skeletons (shadcn skeleton on every chart while data fetches) | `project_dashboard_hr_twin_dependencies.md` #7 | PARTIAL — current has Suspense + Skeleton on telemetry tab; not everywhere | Dashboard-only | S |
| AX-3 | Empty-state polish — when calls_log returns 0 rows, show helpful "no calls yet, place a test call from HR" message instead of blank tabs | `project_dashboard_hr_twin_dependencies.md` #6 | PARTIAL — calls table has empty state; tabs do not | Dashboard-only | S |
| AX-4 | A11y conditional formatting: never colour-only, add icon + sign | `06-interaction-patterns.md` §2.6 | DEFERRED | Dashboard-only | S |
| AX-5 | Keyboard nav: focus ring with high contrast + depth | `09-polish-scenarios.md` table #18 | LOCKED preference | Dashboard-only | S |

### 4.10 QC gate items (FAANG prompt)
| # | Item | Source | Status | Tag | Effort |
|---|---|---|---|---|---|
| QC-1 | NON-SKIPPABLE FAANG QC review against `dashboard/src/**` + dashboard-touched FastAPI before signing off | `project_dashboard_qc_gate_faang.md` | LOCKED non-skippable | Dashboard-only | M |
| QC-2 | The QC prompt file at `docs/reviews/faang-qc-prompt.md` — **NOT FOUND** during this audit. Memory says "User maintains this prompt. If missing at run-time, ask user to provide or point to it before signing off." | `project_dashboard_qc_gate_faang.md` "File to use" | BLOCKED — file not found | needs-user | — |
| QC-3 | Surface findings as a punch list with severity (BLOCKING / SHOULD-FIX / NICE-TO-HAVE); resolve all BLOCKING before sign-off | `project_dashboard_qc_gate_faang.md` "How to apply" | TBD | Dashboard-only | M |
| QC-4 | Add this QC gate as the final step of every dashboard-build plan from this point on | `project_dashboard_qc_gate_faang.md` "How to apply" | LOCKED rule | — | — |

---

## 5. New dashboard tabs queued (post-MVP)

Source: `project_dashboard_goliath_three_new_tabs.md` (User direction 2026-04-28). All three DEFERRED — user will explicitly green-light. Do NOT volunteer or pre-build. The dashboard ships at 4 tabs (Funnel, Economics, Operational, Quality) for MVP submission per memory. (Note: as of resume state, dashboard has 5 tabs counting Telemetry, plus Calls + Carriers + Sales pages.)

### 5.1 Tab 5 — Overall Agent Performance
**Persona**: sales operations leader / broker owner reviewing how the AI is doing as a "team member."
**Likely metrics**:
- Win rate (booked / verified-eligible)
- Average rounds to agreement
- Average call duration
- FMCSA decline handling quality (CHS on decline calls)
- Sentiment trend over time
- Anti-jailbreak success rate (calls flagged as injection attempts that ended cleanly)
- Calls per hour / per day trend
- Top failure modes (clarification loops, narrowing missed, etc.)

**Status**: DEFERRED. **Tag**: Dashboard-only.

### 5.2 Tab 6 — New Loads (sales rep persona)
**Persona**: human sales rep doing the post-handoff paperwork. This tab is the workflow downstream of the mock transfer.
**Likely view**:
- Recent bookings (chronological), each row showing: load_id + lane, carrier (MC + legal name), apply rate vs loadboard rate (delta visible), pickup datetime, equipment, status (pending dispatch / dispatched / in transit / delivered / cancelled — Tier-2 lifecycle).
- Action buttons: "view rate con" / "call carrier" / "mark dispatched" / "flag issue"
- Filter by date / carrier / lane / equipment
- Sort by recency / rate / pickup proximity

**Depends on**: load lifecycle status column (per `project_load_booked_status_lifecycle.md` — Tier-2 schema delta).

**Status**: DEFERRED. **Note**: a `/dashboard/sales` route + `<SalesRepCard>` already exists per `project_dashboard_v3_sales_rep_locked.md` (locked 2026-04-29 to replace the Carriers tab with a sales-rep "New Bookings" tab). `<SalesRepCard>` renders a distinct "received load" card-shape (not standard shadcn Card) per locked Q6. The Sales-Rep persona view per `project_sales_dashboard_view.md` SUPERSEDES this slot and adds DUMMY mimic-accept (no backend) — also DEFERRED. **Tag**: Dashboard-only (DUMMY) / both (real backend).

### 5.3 Tab 7 — Agent Metrics (CloudWatch-Bedrock-style)
**Persona**: technical team / engineering leader / FDE-style customer success.
**Likely metrics**:
- LLM latency: p50 / p70 / p90 / p99 per turn
- Tokens consumed per call (input + output)
- Cost per call (LLM tokens × rate)
- Tool call frequency (verify_carrier, query_loads, negotiate_rate, book_load — calls per call)
- Tool failure rate per tool
- Sandbox errors (Run Python failures)
- HR Twin write success rate
- HR Twin read success rate
- FMCSA endpoint latency + failure rate
- Workflow run errors (HR-side observability)
- A/B test cohort breakdown if multiple prompt versions running
- Cost trends over time

**Source data**: mostly NOT in calls_log today; would need HR's Monitor data exposed via MCP API or HR exports / HR Twin observability table (new) / instrumented FastAPI proxy logs.
**Status**: DEFERRED. **Tag**: needs-HR + Dashboard.
**Overlap note**: substantially overlaps the LOCKED Telemetry tab in §2 above (RPM/TPM/latency percentiles + per-tool latency from HR run details API). Telemetry is Tier-1 LOCKED; the broader CloudWatch-Bedrock-style tab is Tier-2 expansion.

### 5.4 Workstream 1 — Multi-agent dashboard chart review (DEFERRED, partially executed)
- Goliath sub-agent ran 2026-04-30 → output: `docs/dashboard-chart-review.md` (395 lines). Findings already integrated into §4.4 (Goliath top-3 + Other findings).
- Future re-runs (e.g. against the Freight Terminal composite + Pit telemetry + Sigma tables build) will pair with `project_dashboard_qc_gate_faang.md` (§4.10 QC-1).

### 5.5 Future deeper integrations (sketched, very-deferred)
- Open-source telemetry / transcript-review dashboard (Langfuse / Phoenix / Logfire / Helicone) layered on top of `calls_log.transcript` per `project_post_mvp_telemetry_transcript_dashboard.md`. DEFERRED until ~50+ calls + ops wants conversation-grain search / prompt-versioned A/B / LLM-judge eval suites / annotation workflow.
- Self-reflection column on calls_log (agent-generated edge-case / improvement-opportunity note per call) feeds recursive self-improvement loop per `project_post_mvp_self_reflection_column.md`. DEFERRED.

---

## 6. Drift findings (D1-D18) from Phase B audit

Source: `project_phase_b_complete_audit_2026_04_28.md`. **Note**: this audit was 2026-04-28 PM. Two days of Phase C work since then have closed several. Statuses below are best-effort cross-reference against more recent memories + file presence; absent verification, marked "verify".

### 6.1 HIGH severity
- **D6**: `api/app/models.py:57-73` CallRecord has stale fields (`outcome`, `agreed_rate`, `pitched_loadboard_rate`, `negotiation_rounds_used`, `legal_name`, `load_id`) that no longer exist in v15 calls_log 12-col schema. Will silently emit nulls or KeyError on `list_calls`. — STATUS: verify (calls-table.tsx still references `r.outcome ?? r.call_outcome` and `r.legal_name` in the search filter, suggesting the dual-shape is still in effect).
- **D7**: `EconomicsMetrics` returns 2 of 3 fields as None in `dashboard.py:202-205`. Next.js renders `—` placeholders. Need JOIN to bookings + loads. — STATUS: likely RESOLVED (current `<EconomicsCards>` reads `data.avg_loadboard_rate`, `data.avg_agreed_rate`, `data.effective_delta_dollars`/`_pct`, `data.total_revenue_booked`, all populated per the dashboard render).
- **D8**: `fly.toml:24-35` still mounts `robot_data` volume + sets `CALLS_JSON_PATH=/data/calls.json`. — STATUS: verify against current fly.toml.
- **D13 BLOCKING**: Next.js scaffold never `npm install`-ed, never built, never deployed. — STATUS: RESOLVED. Per `resume`: `https://robot-dashboard-andres-morones.fly.dev` is live, smoke-tested.
- **D14**: `carrier-drilldown.tsx:26` reads `apply_rate` from CallRecord (wrong table). KPIs always empty. — STATUS: verify.
- **D15**: 5 endpoints expected by Next.js but missing from FastAPI: `GET /v1/calls`, `GET /v1/calls/{id}`, `GET /v1/carriers/{mc}`, populated `funnel.by_outcome`, populated `economics.avg_loadboard_rate`. — STATUS: PARTIAL. `/v1/calls` and `/v1/calls/{id}` exist (per ADR-008 transcript opt-in). `/v1/carriers/{mc}` — verify.
- **D16**: README is 2 architectures behind. — STATUS: open / unknown. Per `project_carlos_email_artifacts.md`, README pass is one of 10 pre-email blockers.

### 6.2 MEDIUM
- **D5**: `hr-architecture-map.md:183` says "25 rows" loads; actual now 150. — STATUS: open / verify.
- **D9**: `OperationalMetrics` returns 3 nulls always. — STATUS: open per `dashboard-chart-review.md` (Operational tab cards "data missing").
- **D11**: `negotiation_rounds_used`/`pct_max_rounds_used`/`avg_discount_pct` Pydantic fields exist but data was dropped from calls_log v15 per ADR-005. — STATUS: open.
- **D12**: `dashboard_view.py` HTML legacy view imports aggregations on dropped columns; renders mostly empty tabs. — STATUS: open. `dashboard_view.py` slated for retirement post-Next.js cutover (ADR-006 §5 step 9).
- **D17**: README says "v4" workflow; map says "v15". — STATUS: open. Phase C has shipped v17 → v19 → v20 → v21 since this finding; README definitely stale.

### 6.3 LOW / cosmetic
- **D2**: `book_load ` trailing space (F9) — should have been fixed during Phase A1 Edit 7. — STATUS: per Phase C audit findings the F-numbered HR review tracked these; verify.
- **D4**: Bookings rows reference LOAD-0002/0007/0010 which now point at different lanes. Demo cosmetic. — STATUS: open. Per `project_loads_dummy_data_refresh.md`, refresh deferred.
- **D10**: `loads.py` route `/loads/{reference_number}` uses CSV not Twin (parallel data path); intentional but worth flagging. — STATUS: documented; intentional.
- **D18**: 35 stray repo-root JSONs awaiting cleanup approval. — STATUS: open. `docs/cleanup-plan.md` exists per `resume`.

### 6.4 Top 5 risks (still ranked)
1. **Next.js never deploys** (D13). — RESOLVED.
2. **3-round negotiation not provably enforced** (Spec O1.4). Round counter is in prompt prose; reviewer can't see it. Add 1-line transcript log per round + screenshot in broker doc. — open.
3. **Stale README + missing reproduce-deployment doc**. — open.
4. **Demo data integrity** (D4). Click-through to LOAD-0002 in bookings shows different lane than the call narrative. Truncate + reseed before recording video. — open.
5. **Fly volume + stale CALLS_JSON_PATH** (D8). — verify.

### 6.5 Parent-agent radar gaps (10 items) — abridged
1. `api/app/main.py:11-18` docstring stale.
2. No `GET /v1/loads/search` registered — actual route is `/loads/search` (no v1 prefix); could 404 reviewers. — verify.
3. `CallRecord.outcome` vs `call_outcome` ambiguity — see D6.
4. `api-client.ts` 3-fallback chain always hits "fallback-empty" today (calls page renders empty). — verify (CallsTable shows `<CallsSourceBadge>` for `fallback-empty`).
5. `dashboard_view.py` SQL pathway not yet audited for injection on user-supplied filters.
6. `docs/dashboard-metric-catalog.md` referenced 4× but never reconciled vs the EconomicsMetrics 3-of-5 nulls.
7. No `.github/workflows/` — CI/CD absent (acceptable; flag in submission as roadmap).
8. `carriers/[mc]/page.tsx` not smoke-tested. — verify.
9. README workflow naming "v4" vs map's "v15" — naming/history confusion to clean up in ADR-006.
10. Spec-mandated sentiment + outcome classifier consolidated into CHS (1 node not 2). Technically meets spec; need a screenshot/explanation ready for demo.

---

## 7. Items that look like dashboard work but actually need HR/Twin first

Source: `project_dashboard_hr_twin_dependencies.md` (canonical map) cross-referenced with downstream memories.

| # | Dashboard feature | What's blocking | Where | Where the dashboard piece lives |
|---|---|---|---|---|
| HT-1 | Show `notes` audit column per call | HR Extract param + `<call_notes>` prompt section + Twin DDL | needs-HR + needs-Twin | `project_callback_audit_field.md` |
| HT-2 | Locked 9-col Calls table includes `notes` (col #4) | HT-1 must land first | needs-Twin DDL `ALTER TABLE calls_log ADD COLUMN notes TEXT NOT NULL DEFAULT ''` | `project_dashboard_calls_logs_tab.md` §3.1 |
| HT-3 | Real-time negotiation visibility (live counter offers + floor on dashboard) | HR `Send Webhook` node downstream of `calculate_rate` (carrier_offer + final_floor + urgency_tier + lane payload) | needs-HR | `project_realtime_negotiation_hook.md`, `project_dashboard_hr_twin_dependencies.md` |
| HT-4 | Carrier name (legal_name) in calls list | HR Extract: add `legal_name` param OR bind from `verify_carrier.content.carrier.legalName` via @ picker into Twin write | needs-HR | `project_dashboard_hr_twin_dependencies.md` |
| HT-5 | Tool-call timeline on drilldown (verify → query → negotiate → book sequence with timestamps) | HR Extract: structured `tool_call_sequence` array OR Workflow Dump captures `__run_steps__` events into a new Twin table | needs-HR + needs-Twin | `project_dashboard_hr_twin_dependencies.md` |
| HT-6 | Per-language language-switch markers on transcript | HR Voice Agent metadata captures language switches per turn (already captured in transcript JSON; just needs UI to render) | needs-Dashboard only (data already there) | `project_dashboard_hr_twin_dependencies.md` |
| HT-7 | Field-rename consistency: `original_rate` / `apply_rate` | Twin DDL rename `bookings.agreed_rate → apply_rate` (probably already done; verify) + Extract param renames | needs-Twin + needs-HR | `project_field_renames_pending.md`; the v15 schema uses `apply_rate` already |
| HT-8 | Load-status lifecycle dropdown / filter on /loads/available | Twin DDL `ALTER TABLE loads ADD COLUMN status TEXT, booked_at TIMESTAMP, booked_by_call_id TEXT` + index on `(status, pickup_datetime)` + HR `book_load` flips status='booked' | needs-Twin + needs-HR | `project_load_booked_status_lifecycle.md` |
| HT-9 | Tool-call timeline (if route via Twin) | `CREATE TABLE tool_calls (id, call_id, tool_name, fired_at, args JSONB, result JSONB)` + HR Workflow Dump fan-out | needs-Twin + needs-HR | `project_dashboard_hr_twin_dependencies.md` |
| HT-10 | Persistent carrier profile aggregates (instead of recomputing each request) | `CREATE TABLE carrier_aggregates (mc_number, total_calls, booking_rate, avg_agreed_discount, ...)` + nightly refresh job | needs-Twin + ETL job | `project_dashboard_hr_twin_dependencies.md` |
| HT-11 | Sales-rep "accept" persistence (Tier-3) | `bookings.sales_accepted_at` column + `/v1/bookings/{id}/accept` endpoint + auth model for sales reps | needs-Twin + needs-FastAPI | `project_dashboard_hr_twin_dependencies.md`, `project_sales_dashboard_view.md` |
| HT-12 | Telemetry tab Pit quadrants — token-spend trend | HR @ picker → calls_log columns (10 added per token_usage_capture); DDL queued | needs-HR + needs-Twin | `project_telemetry_widgets_locked.md` §2.11 |
| HT-13 | Telemetry: per-call latency (p70 + p90) | HR Voice Agent var → calls_log column. Currently broken — F8. Per ADR-012, the columns will stay NULL forever; the dashboard computes p70/p90 dashboard-side from transcript. Direct dashboard fix possible without HR. | LOCKED dashboard-only (per ADR-012) | `project_dashboard_latency_compute_locked.md` |
| HT-14 | Telemetry: real per-tool latency (FMCSA / query_loads round-trip), time-to-first-utterance, dead-air gap | Per-turn timestamps not present in transcript today; blocked on Phase 2 = HR run details API exposing per-node `started_at`/`ended_at` (`monitor_runs` MCP) | needs-HR perms / API probe | ADR-012 §"What's blocked"; `project_telemetry_widgets_locked.md` §2.11 |
| HT-15 | Token columns binding on Log Event Write-to-Twin chip (5 per node × 2 nodes) | HR UI batch | needs-HR | `project_telemetry_widgets_locked.md` §"HR UI work needed" |
| HT-16 | F8 latency type fix (rename + retype p70/p90 columns to int4) | HR + Twin DDL | needs-HR + needs-Twin | `project_telemetry_widgets_locked.md` (claims fixed in Phase C-C4); per `project_dashboard_latency_compute_locked.md` columns still NULL → not chasing |
| HT-17 | F2 prompt dedup, F4 required flags, F3 calculate_rate now/now_iso key rename | HR UI | needs-HR | `project_phase_c_in_progress_resume.md` |
| HT-18 | API redeploy to apply WAF call_id fix | redeploy `robot-api-andres-morones` from current `main` | needs-FastAPI redeploy (NOT-HR-NOT-Twin) | `project_resume_2026_04_30_post_compact.md` |

### 7.1 Other items that ARE pure-dashboard (no HR/Twin block)
Listed for clarity per `project_dashboard_hr_twin_dependencies.md`:
- Calls list filters — DONE
- Call drilldown expand — sub-agent in flight
- Branding refresh — done (Freightline mark wired); theme-composite swap pending
- Sales-rep operational view (DUMMY mimic-accept; no backend) — DEFERRED
- Filter persistence via URL params — DONE
- Empty state polish — partial
- Loading skeletons — partial
- Dark/light mode polish — DEFERRED
- Goliath chart improvements — most are Dashboard-only (sub-agent reviewed; punch list at `dashboard-chart-review.md`)

---

## 8. Logo decision — locked-theme-derived recommendation

The Bloomberg Pit / Freight Terminal aesthetic is locked. Logo should be derived FROM the theme, not chosen separately. Of the 7 logos at `dashboard/src/components/branding/LOGO_OPTIONS.md`:

**Recommended: Concept #6 — Beacon (Dark Monochrome + Glow)**.

Two-line rationale:
- Beacon's exact palette (`#08080A` near-black bg, `#FAFAFA` pure-white wordmark, `#34D399` emerald-green "live" glow, JetBrains Mono wordmark) is the **closest match** to Freight Terminal's `--bg: #060607`, `--primary: #FFFFFF`, `--accent: #00DC82` (electric green for live/healthy), and Geist Mono numerics — same idiom, same colorways, same "Bloomberg terminal / Vercel observability" mood the composite explicitly cites.
- Freightline (currently shipping per `AcmeMark.tsx`) is industrial-orange + slate-navy, locked 2026-04-30 morning before the night theme-composite supersession; it's a structural mismatch (DOT-placard heritage vs Vercel-precision instrument). Beacon swap is a 1-component edit (`AcmeMark.tsx` SVG body + `--brand-orange`/`--brand-slate` tokens repointed to white + emerald) with zero downstream component changes.

**Anti-recommendation**: Concept #1 Freightline (currently shipping) — palette structurally mismatched to Freight Terminal. Concept #5 Atlas (vintage badge, cream-on-steel) — wrong vibe, breaks the Vercel mood. Concept #7 Coyote — high charm but reads as "playful brand identity" against the operator-grade composite.

---

## 9. Anything not on radar — surprises + conflicts

Confidence: HIGH = directly cited memory or file; MEDIUM = inference from cross-refs; LOW = guess from absence.

### 9.1 Surprises (HIGH confidence)
- **S1**: The current `--primary: 36 95% 56%` (amber) in `dashboard/src/app/globals.css` line 80 is the Dark Ops Console palette per `docs/dashboard-v2-research/05-branding-design-tokens.md` §2.1, NOT the locked Freight Terminal `--primary: #FFFFFF` (white-as-primary). The locked composite was never wired into code. **Implication**: TB-1 in §4.1 is the headline blocking work for "shipping the locked theme." HIGH.
- **S2**: The 9-col Call Logs main table (locked 2026-04-30) drifts from current `dashboard/src/components/calls-table.tsx`. Current renders 8 cols missing `call_id`, `notes`, `lane_origin`, `lane_dest`; has extras `apply_rate`, `duration_seconds`. CT-1 is a non-trivial-but-bounded fix. HIGH.
- **S3**: Six telemetry component files named in `dashboard-widget-integration-plan.md` (Voice Agent BIG, Extract, CHS, telemetry-filters, telemetry-crosshair, telemetry-types) **do not exist on disk**. The current 5 telemetry files (`category-widget-card`, `latency-percentiles-card`, `rpm-tpm-chart`, `telemetry-empty-state`, `telemetry-kpi-strip`) are a different design generation — this is a major build-out gap, not polish. HIGH.
- **S4**: The QC gate prompt at `docs/reviews/faang-qc-prompt.md` (LOCKED non-skippable per `project_dashboard_qc_gate_faang.md`) **does not exist in the repo**. `docs/reviews/` directory does not exist. The dashboard cannot be signed off without this file per the locked rule. HIGH.
- **S5**: Two design-spec doc generations stack on top of each other and partially conflict. `docs/dashboard-v2-research/05-branding-design-tokens.md` locked Dark Ops Console + Acme Logistics + Truck-icon wordmark + amber primary. Then on 2026-04-30 morning, `project_dashboard_improvements_plan.md` locked Freightline (concept #1, slate-navy + safety-orange). Then the same evening, `project_dashboard_design_v3_locked.md` locked Pine Ledger v3 + D2 The Tape ticker. Then later that night, `project_dashboard_theme_composite_locked.md` superseded the Pine Ledger lock with the Freight Terminal + Pit + Sigma + Cmd-K composite. Each successive "lock" was real but the file generations under it (`themes-9-dark.md`, `ui-direction-*.md`, `themes-v2-*-lens.md`, `dashboard-v2-research/**`) all still live in `docs/`. Implication: a fresh contributor reading `docs/` could easily implement the wrong theme generation. HIGH.
- **S6**: The Sales-Rep view exists in TWO competing memories. `project_dashboard_v3_sales_rep_locked.md` (2026-04-29) locked it as the Tier-1 replacement of the Carriers tab in main nav (verbatim Q1: "Replace Carriers tab"). Then `project_dashboard_improvements_plan.md` (2026-04-30) decided "Carriers: keep the rollup component + BUILD the missing `/dashboard/carriers/` list page" (because rollup will be used per goliath review). Current `header.tsx` has both: `/dashboard/carriers` AND `/dashboard/sales` in primary nav. The earlier "replace" decision was REVERSED. HIGH.
- **S7**: ADR-012 says HR's `intermediate_response_count` / `p70_latency_ms` / `p90_latency_ms` columns will be NULL forever (HR-platform bug, locked not-chasing). The dashboard's `<CallTelemetry>` component currently reads from those columns directly (per the memory comment "already shows p70/p90 + intermediate_response_count (post v2 fix)" — `project_dashboard_calls_logs_tab.md` §3.4). TR-12 + TR-17 (rebind to dashboard-computed values + add disclosure tooltip) are **silently rendering nulls today**. MEDIUM-HIGH.

### 9.2 Items mentioned once and never again
- **N1**: "Loadboard Live" Cmd-K theme is referenced in the composite (`project_dashboard_theme_composite_locked.md` §1.5) but no implementation plan exists. The 640px floating panel + fuzzy results spec is the only artifact. TB-4 effort estimate is L because the work hasn't been scoped. MEDIUM.
- **N2**: `project_dashboard_v2_design_directives.md` directive #6 ("Interactability — clicking chart elements filters the dashboard") — DEFERRED to full-enterprise; appears nowhere else after 2026-04-27. Cross-filter interactions (Power BI signature) are post-MVP. LOW.
- **N3**: `09-polish-scenarios.md` enumerates 30 micro-interactions (KPI count-up, slide-in side drawer, breath-pulse live indicator, KPI cascade load, smooth theme transition, etc.) — LOW visibility in any newer memory. This entire polish doc is essentially "library of options," not a locked plan. LOW.
- **N4**: The "first 5 seconds" sequence (`09-polish-scenarios.md` §7) is a great Loom cue but never resurfaced in any submission/recording memory. LOW.
- **N5**: Empty-state copy library (`05-branding-design-tokens.md` §8-9) — referenced in `09-polish-scenarios.md` §4 — never wired into actual empty-state components on disk. MEDIUM.
- **N6**: Five-agent dashboard v2 build (`project_dashboard_v2_requirements.md` §"Goliath agents being launched" — lists 5 agents: Freight ops data analyst, UX/IA architect, Visualization specialist, Engineering feasibility + active-call, Branding + design tokens). Outputs landed at `docs/dashboard-v2-research/01-09-*.md`. None of these were re-validated against the night composite-lock. MEDIUM.

### 9.3 Conflicts between memory files
- **C1** (HARD CONFLICT): `project_dashboard_html_decision.md` says "MVP dashboard = server-rendered HTML at `dashboard_view.py`" (locked 2026-04-28 morning) → `project_dashboard_nextjs_committed.md` says "Production-ready ambition wins over MVP minimum. Building Next.js 15..." (committed 2026-04-28 PM). Memory file `project_dashboard_html_decision.md` carries an inline NOTE "user shifted scope to production-ready — Next.js may be back on table"; ADR-006 formalizes the supersession. RESOLVED via ADR-006. HIGH.
- **C2** (SOFT CONFLICT): `project_dashboard_v2_locked_option_b.md` original lock kept nuqs + Tremor (Option B); ADR-011 says "rewritten to reflect Option Y" (full minimization). The memory file body has been updated; index entry still says "cut all 5 libs (nuqs/Tremor/calendar/date-fns/popover) per ADR-011" — consistent. RESOLVED. HIGH.
- **C3** (SOFT CONFLICT): `project_post_mvp_nextjs_dashboard.md` says "FINAL ARCHITECTURE for MVP" (HTML stays); `project_dashboard_nextjs_committed.md` directly contradicts (commit Next.js). Index entry for `project_post_mvp_nextjs_dashboard.md` simply reads "Next.js shipped; filter is the obvious next iteration." Both files retained. The rejection-then-acceptance arc is the ground truth; the older HTML-only memo is dead. HIGH.
- **C4** (SOFT CONFLICT): `project_dashboard_design_v3_locked.md` (Pine Ledger v3 + D2 The Tape) was superseded later same day by `project_dashboard_theme_composite_locked.md` (Freight Terminal + Pit + Sigma + Cmd-K). v3-locked memory does NOT carry a "supersedes" inline marker — it just got named "Pine Ledger v3" while the composite memory says "Retired: Pine Ledger v3 lock." A grepper hitting v3-locked first could implement the wrong theme. MEDIUM.
- **C5** (SOFT CONFLICT): Multiple memories reference the same unique number "30s TTL" for the FastAPI cache (ADR-007). ADR-009 then promotes the webhook path which `invalidate_dashboard_cache()`s into the same cache — implying coordinated 30s + invalidation. `project_dashboard_caching_strategy.md` says "Next.js `revalidate=30`"; `dashboard/src/app/dashboard/page.tsx` line 34 says `export const revalidate = 300;` — bumped to 5 min as the long-poll fallback in ADR-009 §1. Code state matches ADR-009; memory `project_dashboard_caching_strategy.md` entry (2 days old) has not been updated. SOFT — not blocking. MEDIUM.
- **C6** (NAMING DRIFT): `project_dashboard_calls_logs_tab.md` §"Touch list" line 4 says "list endpoint can stay full-projection or split to lightweight per perf" — no decision made. Current code does full projection (passes `include_transcript=true` from list endpoint per `dashboard/src/components/calls-table.tsx` search filter looking at `c.transcript`). Per ADR-008 §2 Item 2.4 transcript opt-in defaults to FALSE — that's only enforced on `GET /v1/calls/{call_id}` per the ADR text, not on the list endpoint. Whether the list endpoint also strips by default is unclear. MEDIUM.

### 9.4 Stale memory entries
- **St1**: `project_dashboard_caching_strategy.md` carries a system reminder "This memory is 2 days old. Memories are point-in-time observations." Same for `project_dashboard_freshness_options.md`, `project_dashboard_goliath_three_new_tabs.md`, `project_dashboard_dynamic_filtering.md`, `project_dashboard_html_decision.md`, `project_dashboard_nextjs_committed.md`, `project_post_mvp_dashboard_metrics.md`, `project_post_mvp_nextjs_dashboard.md`, `project_post_mvp_telemetry_transcript_dashboard.md`, `project_phase_b_complete_audit_2026_04_28.md`, `project_dashboard_polish_deferred.md`, `project_dashboard_endpoint_tests_tier2.md`, `project_dashboard_v2_requirements.md`, `project_dashboard_enterprise_framing.md`, `project_dashboard_v2_design_directives.md`, `project_sales_dashboard_view.md`. Most of these still capture LOCKED decisions (memory aging doesn't invalidate the lock); flagging for reviewer awareness. MEDIUM.
- **St2**: `project_dashboard_design_v3_locked.md` (locked 2026-04-30 evening) is **explicitly retired** by `project_dashboard_theme_composite_locked.md` (2026-04-30 night). v3-locked file content still claims to be canonical. HIGH (intent of retirement is clear in the night memory; the older file just never got updated).
- **St3**: `project_dashboard_html_decision.md` carries inline NOTE "user shifted scope to production-ready — Next.js may be back on table" pointing to the supersession; ADR-006 formalizes it. The body of the memory still describes HTML as the locked architecture. HIGH (resolved by ADR-006 cross-ref).

---

## 10. Implementation order recommendation

**Priority 1 — blocking demo (must land before submission email):**

| # | Title | Rationale | Dependency |
|---|---|---|---|
| P1.1 | Redeploy API to apply WAF call_id fix (CT-5) | Currently shipping returns "Not found" on every call drilldown — direct demo blocker | None |
| P1.2 | Sign-convention conflict fix (CT-8) | Reviewer comparing hero chart to booking cards = confused; principled-or-not is binary | None |
| P1.3 | Wire spark + delta on KPI #2 / #3 / Operational tab cards (LD-3, ~30 min) | "data missing" visual asymmetry reads as broken even when API returns it | None |
| P1.4 | Triple-duplicate outcome distribution dedupe (CT-9) | Single biggest "looks unfinished" tell | None |
| P1.5 | README rewrite (D16) + reproduce-deployment doc | Reviewer's first impression; submission email blocker | Email checklist |
| P1.6 | Truncate + reseed demo data + 3 fresh test calls (D4) | Click-through to LOAD-0002 in bookings shows different lane than the call narrative — kills demo trust | User HR test calls |
| P1.7 | FAANG QC gate file present + run (QC-1 / QC-2) | Non-skippable per locked rule. Either user provides the prompt or scope-cut the gate | needs-user |

**Priority 2 — polish (during Phase C+D ship cycle):**

| # | Title | Rationale | Dependency |
|---|---|---|---|
| P2.1 | Wire Freight Terminal `:root` tokens (TB-1) + Geist + Geist Mono fonts (TB-6) | Themed surface is the locked production deliverable | None |
| P2.2 | Replace Freightline AcmeMark with Beacon (TB-5) | Logo derives from theme; one-component swap | TB-1 |
| P2.3 | Replace 1×1 hero with 2×2 chart grid (TB-8 / QO-9) | 4-panel central widget is locked; current `<EffectiveDeltaChart>` is single-chart | None (data sources exist) |
| P2.4 | Build `transcript_telemetry.py` (TR-10) + 3 new FastAPI telemetry endpoints (TR-9) | Pre-req for any of the locked Telemetry-tab work | None |
| P2.5 | Build Voice Agent BIG widget + Extract + CHS widgets (TR-1 / TR-2 / TR-3) + crosshair sync (TR-4) + auto-refresh (TR-5) + time-range selector (TR-6) | The locked Telemetry tab spec is large; this is the bulk work | TR-10 + TR-9 + TR-8 |
| P2.6 | `.pit-surface` scope swap on Telemetry tab (TB-2) + IBM Plex Mono font (TB-7) | Pit gets visual signature once widgets are in place | TR-1..3 |
| P2.7 | Reduce calls-table to 9 locked columns (CT-1) + drilldown shows all 32 cols (CT-3) + transcript-as-its-own-widget (CT-4) | Locked Call Logs tab spec | needs HT-1 (notes col Twin DDL) for col #4 |
| P2.8 | Implement `.sigma-grid` for Calls + Carriers tabs (TB-3) | Locked Sigma footprint rule | None |
| P2.9 | KPI Layout: Sigma frozen-merged-cell band on Calls top + Freight Terminal asymmetric strip on Overview (LD-1) | Locked sub-q5 | TB-3 + TB-1 |
| P2.10 | Build Carriers list page at `/dashboard/carriers` (CT-10) | Locked decision; prevents dead-rollup-component finding | None |
| P2.11 | Wire `chs_distribution` to Quality tab (QO-1, CT-11) | API returns it; UI ignores | None |
| P2.12 | Drop docs-style copy + redact variable names + drop "Why this matters" (TB-9, TB-10, TB-11) | Locked v2 directives | None |
| P2.13 | Active-calls indicator: replace `current_node` with friendly label (CT-7) | Goliath finding; quick polish | None |
| P2.14 | Empty-state copy library wired to all empty states (N5, AX-3) | Polish; prevents demo dead-zones | None |
| P2.15 | Loading skeletons on every chart (AX-2) + dark/light parity audit (AX-1) | A11y baseline | None |
| P2.16 | Redaction tooltip on telemetry: "computed from transcript (dashboard-side)" (TR-12 / TR-17) | ADR-012 honesty contract | TR-10 |
| P2.17 | Mount global Cmd-K palette portal (TB-4) | Locked; lifts the "deliberately built UX" signal in demo | None (well-scoped) |
| P2.18 | Goliath chart-review fixes: KPI #4 median chip (QO-4), KPI #5 inline margin (QO-5), KPI #6 /100 hint + red-below-70 (CT-12), KPI #3 target band (QO-6) | All `dashboard-chart-review.md` Tier-2 deltas | Mostly Dashboard-only; QO-6 needs new agg |
| P2.19 | Calls tier-2 advanced query builder (KF-2) | Sub-agent landed code; integrate + ship | None |
| P2.20 | Replace agreed_rate histogram (QO-2) + drop placeholder Operational nulls (D9 / D11) | `project_dashboard_v2_design_directives.md` directive #8 | needs-FastAPI agg + Dashboard |
| P2.21 | Fix tablet KPI grid breakpoint (LD-2) | Trivial polish | None |

**Priority 3 — post-MVP:**

| # | Title | Rationale | Dependency |
|---|---|---|---|
| P3.1 | Three new tabs: Overall Agent Performance + New Loads (sales-rep) + Agent Metrics (CloudWatch-Bedrock) | All DEFERRED in `project_dashboard_goliath_three_new_tabs.md` | needs-HR for Agent Metrics; Twin lifecycle for New Loads; both for Overall Performance over time |
| P3.2 | Sales-rep view DUMMY mimic-accept (frontend-only, localStorage) | Demo extension point per `project_sales_dashboard_view.md` | None |
| P3.3 | Real-time negotiation hook (HR webhook → SSE → sales-rep dashboard) | `project_realtime_negotiation_hook.md` | needs-HR + Dashboard |
| P3.4 | Cross-filter on chart click (KF-4) | Power BI moment; full-enterprise scope | None (large) |
| P3.5 | Dynamic dashboard filtering — date/outcome/sentiment/MC/lane on every endpoint (KF-5) | `project_dashboard_dynamic_filtering.md` Tier-2 (~2hr) | needs-FastAPI + Dashboard |
| P3.6 | `notes` audit column (HT-1, HT-2) + field renames (HT-7) | bundled into one schema-update PR | needs-HR + Twin |
| P3.7 | Load-status lifecycle (HT-8) | Tier-2 schema delta | needs-Twin + HR |
| P3.8 | Tool-call timeline + carrier-aggregates table (HT-9, HT-10) | Tier-2 / Tier-3 perf + analytics | needs-Twin + HR / ETL |
| P3.9 | Performance: Suspense streaming, asyncio.gather inside helpers, SWR client cache, link-prefetch verify, Redis migration trigger (PC-3..PC-8) | `project_dashboard_polish_deferred.md` | infra |
| P3.10 | Dashboard endpoint integration tests rewrite (QO-8) | `project_dashboard_endpoint_tests_tier2.md` ~30-60 min | needs-FastAPI |
| P3.11 | Operational + agent-monitoring metric tabs (QO-7) | `project_post_mvp_dashboard_metrics.md` | partially Dashboard-only |
| P3.12 | Open-source telemetry dashboard layer (Langfuse / Phoenix) on `calls_log.transcript` | `project_post_mvp_telemetry_transcript_dashboard.md` | infra + selection |
| P3.13 | Self-reflection column → recursive self-improvement loop | `project_post_mvp_self_reflection_column.md` | needs-Twin schema + HR |
| P3.14 | Pit-quadrant content blocked on per-turn timestamps (TR-13, TR-16) | Probe HR `monitor_runs` API; if no per-node timestamps, escape-hatch via Run Python timing-capture node + `node_timings_json` Twin column | needs-HR perms / Twin if escape-hatch |
| P3.15 | WAF call_id long-term fix (CT-6): integer PK or migrate off Twin | `project_twin_production_lock_in.md` Tier-2 | needs-Twin / FastAPI |
| P3.16 | Multi-machine Redis pubsub (RT-4) for SSE + cache | trigger: scale-out beyond `min_machines=1` | infra |
| P3.17 | Drift cleanup: README workflow rename, `.github/workflows/` CI, `dashboard_view.py` retirement, fly volume + CALLS_JSON_PATH purge | D8 / D17 / D18 / radar #7 | None |

---

## Pairs / cross-reference index

**LOCKED memories** (treat as canonical for theme-and-spec questions):
- `project_dashboard_theme_composite_locked.md` (composite theme — LATEST)
- `project_telemetry_widgets_locked.md` (telemetry — LATEST)
- `project_dashboard_calls_logs_tab.md` (calls table 9 cols)
- `project_dashboard_v2_locked_option_b.md` (library lock + ADR-011)
- `project_dashboard_caching_strategy.md` + ADR-007 (caching)
- `project_dashboard_freshness_options.md` + ADR-009 (webhook + SSE Option C)
- `project_dashboard_latency_compute_locked.md` + ADR-012 (dashboard-side latency)
- `reference_adr_013_operational_analytical.md` + ADR-013 (operational vs analytical store)
- `project_dashboard_qc_gate_faang.md` (QC gate)
- `project_dashboard_nextjs_committed.md` + ADR-006 (Next.js commit)

**RETIRED but still in memory** (treat as historical):
- `project_dashboard_html_decision.md` (superseded by ADR-006)
- `project_post_mvp_nextjs_dashboard.md` (HTML-only "final architecture" — superseded by ADR-006)
- `project_dashboard_design_v3_locked.md` (Pine Ledger v3 + D2 The Tape — explicitly retired by composite)
- `project_dashboard_v2_design_directives.md` (intermediate v2 directives — partially-implemented, partially-deferred)
- `project_dashboard_enterprise_framing.md` (broad enterprise framing — superseded by composite + telemetry locks)
- `themes-9-dark.md` + `themes-preview.html` (v1 9-dark — explicitly rejected)

**DEFERRED (Tier-2 / Tier-3):**
- `project_dashboard_dynamic_filtering.md` (Tier-2 ~2hr)
- `project_dashboard_polish_deferred.md` (visual + perf polish)
- `project_dashboard_endpoint_tests_tier2.md` (test rewrite ~30-60 min)
- `project_post_mvp_dashboard_metrics.md` (5th + 6th tab metrics)
- `project_post_mvp_telemetry_transcript_dashboard.md` (Langfuse/Phoenix)
- `project_dashboard_goliath_three_new_tabs.md` (3 new tabs)
- `project_sales_dashboard_view.md` (sales-rep DUMMY view)
- `project_realtime_negotiation_hook.md` (real-time hook)
- `project_callback_audit_field.md` (notes column)
- `project_field_renames_pending.md` (column renames)
- `project_load_booked_status_lifecycle.md` (load lifecycle)

**ADRs touched by this register:** ADR-006, ADR-007, ADR-008, ADR-009, ADR-011, ADR-012, ADR-013.

**Repo design docs touched:**
- `docs/design-explorations/themes-v2-bi-lens.md` (Sigma lock source)
- `docs/design-explorations/themes-v2-fintech-lens.md` (Pit lock source)
- `docs/design-explorations/themes-v2-modern-saas-lens.md` (Freight Terminal + Loadboard Live lock source)
- `docs/design-explorations/themes-v2-preview.html` (clickable preview, not opened in this audit)
- `docs/design-explorations/themes-9-dark.md` + `themes-preview.html` (rejected v1)
- `docs/design-explorations/ui-direction-data-density.md` (Bloomberg Terminal / Pivot-First Inspector / etc — earlier exploration)
- `docs/design-explorations/ui-direction-fintech-trading.md` (The Pit / The Tape / etc — earlier exploration)
- `docs/design-explorations/ui-direction-ops-tooling.md` (Salesforce / Linear / Vercel / Stripe — earlier exploration)
- `docs/design/dashboard-widget-integration-plan.md` (Telemetry tab build plan)
- `docs/design/transcript-telemetry-module.md` (`transcript_telemetry.py` design spec)
- `docs/dashboard-v2-research/01-09-*.md` (5-agent goliath outputs from 2026-04-29)
- `docs/dashboard-chart-review.md` (395-line goliath chart review from 2026-04-30)
- `docs/dashboard-design-philosophy.md` (referenced; not opened)
- `docs/dashboard-metric-catalog.md` (referenced; not opened)
- `docs/reviews/faang-qc-prompt.md` — **NOT FOUND**

**Repo dashboard files inventoried:**
- All `dashboard/src/**/*.tsx`, `*.ts` files listed via Glob (~80 files)
- Zero TODO/FIXME/XXX/DEFERRED/HACK markers found via Grep on `dashboard/src/`
- `dashboard/src/components/branding/LOGO_OPTIONS.md` (7 logo concepts)
- `dashboard/src/app/globals.css` (Dark Ops Console palette wired)
- `dashboard/src/components/branding/AcmeMark.tsx` (Freightline mark)
- `dashboard/library-cut-comparison.html` (visual A/B from ADR-011)
- `dashboard/branding-preview.html` (logo preview, per resume state)
