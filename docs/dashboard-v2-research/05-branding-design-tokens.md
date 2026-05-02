# Dashboard v2 — Branding & Design Tokens (Acme Logistics)

## 1. Brand identity for "Acme Logistics"

### 1.1 Wordmark

- **Treatment:** text-only wordmark, no fabricated logo file.
- **Composition:** lucide `Truck` icon at 18×18 px (stroke 1.75) + `Acme` (semibold) + `Logistics` (regular, slightly muted) on single baseline.
- **Typography:** `Inter` or `Geist`.
- **Color (Dark Ops default):** icon and "Acme" in `--foreground` (near-white); "Logistics" in `--muted-foreground` (warm gray).
- **Color (Light Editorial alt):** icon and "Acme" in `--primary` (deep navy); "Logistics" in `--muted-foreground`.
- **Why `Truck`:** reads "freight brokerage" instantly without being cute. `Route` is fine alternate; reject `Package` (e-commerce) and `MapPin` (logistics-tech-startup).

### 1.2 Tagline

Omit on header. If shown anywhere: **"Carrier capacity, on the line."** Operational, not marketing.

### 1.3 Header copy — replace "Carrier Voice Agent"

1. **`Carrier Operations`** ← **RECOMMENDED**. Generic, neutral, reads like internal product name.
2. `Capacity Desk` — industry-flavored.
3. `Inbound Carrier Console` — descriptive, slightly verbose.

Final lockup: `Acme Logistics · Carrier Operations`.

### 1.4 "Powered by HappyRobot" placement

- **Where:** footer, far-right, `text-xs` in `--muted-foreground`.
- **Where NOT:** never in header, never in KPI hint, never in chart subtitles.
- **Wording:** literal `Powered by HappyRobot`.
- **Link:** `https://happyrobot.ai` with `rel="noopener"`.

### 1.5 UI copy tone

1. **Terse.** KPI label = 2 words max; chart title = 4.
2. **Ops vocabulary.** "Booked", "in-progress", "abandoned", "no-match", "decline" — dispatch-floor words.
3. **No internals.** Never `calls_log`, `bookings`, `Twin`, `extract`, `webhook`, `loadboard_rate`.

## 2. Color palette

### 2.1 Option A — Dark Ops Console (DEFAULT)

| Token | HSL | Hex | Role |
|---|---|---|---|
| `--background` | `222 24% 8%` | `#0F141C` | App canvas |
| `--card` | `222 22% 11%` | `#161C26` | KPI cards, table rows |
| `--popover` | `222 22% 13%` | `#1B2230` | Menus, tooltips |
| `--secondary` | `222 18% 18%` | `#262E3D` | Secondary surfaces |
| `--border` | `222 18% 22%` | `#2F384A` | Card borders |
| `--foreground` | `220 14% 96%` | `#F1F3F7` | Primary text |
| `--muted-foreground` | `220 10% 64%` | `#9AA1AE` | Secondary text |
| `--primary` | `36 95% 56%` | `#F4A52B` | Brand accent — safety amber |
| `--accent` | `36 95% 56%` | `#F4A52B` | Same as primary on dark |
| `--ring` | `36 95% 56%` | `#F4A52B` | Focus ring |
| `--success` | `142 65% 45%` | `#28B765` | Booked, healthy |
| `--warning` | `38 92% 55%` | `#F2A83A` | Above-list rate |
| `--destructive` | `0 72% 55%` | `#DC4444` | Abandons, errors |
| `--info` | `199 89% 55%` | `#27B6F0` | Neutral signals |

**Chart palette:**

| Token | Hex | Use |
|---|---|---|
| `--chart-1` | `#F4A52B` | Primary series |
| `--chart-2` | `#27B6F0` | Secondary |
| `--chart-3` | `#28B765` | Positive |
| `--chart-4` | `#DC4444` | Negative |
| `--chart-5` | `#9F88D9` | Tertiary |

**Why amber for primary:** color of high-vis vests, trailer reflectors, DOT signage. Freight industry's most recognized accent. Semantically distinct from green/red.

### 2.2 Option B — Light Editorial (alternate)

| Token | Hex | Role |
|---|---|---|
| `--background` | `#FAF7F2` | Warm off-white |
| `--card` | `#FFFFFF` | Cards pop |
| `--secondary` | `#EEF0F4` | Table header |
| `--border` | `#DBDFE6` | Hairline |
| `--foreground` | `#0F1729` | Rich black |
| `--primary` | `#10295E` | Deep navy — Trimble-flavored |
| `--accent` | `#F09A0F` | Same amber, tuned for light |

### 2.3 Recommendation

**Default = Option A (Dark Ops Console).** Light Editorial behind toggle (persisted to `localStorage`).

## 3. Typography

### 3.1 Families
- **Body & headings:** `Inter` Variable via `next/font/google`.
- **Numeric:** `Geist Mono`. Apply via Tailwind's `font-mono` plus `tabular-nums`.

### 3.2 Type scale (rem)

| Token | rem | px | Use |
|---|---|---|---|
| `text-display` | 2.25 | 36 | Hero metric |
| `text-h1` | 1.5 | 24 | Page title |
| `text-h2` | 1.125 | 18 | Section title |
| `text-h3` | 0.95 | 15 | Card title |
| `text-body` | 0.875 | 14 | Default body |
| `text-caption` | 0.75 | 12 | Hints, footer, timestamps |
| `text-micro` | 0.6875 | 11 | Badges, table column headers |
| `text-num-xl` | 1.875 | 30 | KPI value |
| `text-num-lg` | 1.5 | 24 | Secondary KPI |

**Weights:** 400 body, 500 labels, 600 numerics + headers. **No 700+.**

## 4. Active tab indicator

### Recommendation

**Option (a) — bottom underline** for global nav (Overview / Calls / Carriers).
**Option (b) — pill** for inner tab groups inside a page.

Two distinct treatments so visual hierarchy stays legible.

Mobile: nav collapses behind hamburger; active item appears at top of dropdown sheet with underline.

## 5. Header structure

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Truck Acme Logistics · Carrier Operations]   [Overview] [Calls] [Carriers]   ● Live · 2 active   [Apr 22 → Apr 28]   [☼/◐]   [AM ▾] │
│                                                ‾‾‾‾‾‾‾‾                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

1. Wordmark + product label
2. Primary nav with bottom-underline active state
3. Live indicator (pulsing dot + count)
4. Global date filter
5. Theme toggle
6. User menu

Header height: 56 px desktop, 48 px mobile. Sticky with 1px `--border` bottom hairline + `backdrop-filter: blur(8px)`.

## 6. Footer

```
[● Online]   Last sync 12s ago             v0.4.2 · Powered by HappyRobot
```

1. API status indicator (green/amber/red dot)
2. Sync timestamp from SSE last-message
3. Build + attribution

## 7. Component-level visual treatment

**Radii:** `--radius-sm` 4px (badges), `--radius-md` 8px (cards/inputs), `--radius-lg` 12px (modals).

**Shadows (dark):** `--shadow-card` = `0 1px 0 hsl(var(--border)) inset`.

### KPI card
- `bg-card border border-border rounded-md p-4`
- Label: `text-micro uppercase tracking-wider text-muted-foreground`
- Value: `text-num-xl font-semibold tabular-nums tracking-tight`
- Delta: right of value at `text-caption`, colored by direction
- Hint: `text-caption text-muted-foreground` below
- Focus (interactive): 2px `--ring` outline, offset 2px

### Table row
- Header: `bg-secondary text-micro uppercase tracking-wider text-muted-foreground`
- Body: `border-b border-border/60`. Hover: `bg-muted/40`
- First column emphasis (MC #): `font-mono text-caption`
- Numeric columns: `text-right tabular-nums`
- Sticky header on scroll for tables ≥ 10 rows

### Chart container
- Outer: `Card`
- Title row: `flex items-center justify-between`
- Chart area: `aspect-[16/7]` for trends, `aspect-square` for pies, `min-h-[280px]`
- Recharts axis: `stroke="hsl(var(--border))"`, font-size 11

### Badge
- Base: `inline-flex items-center rounded-sm px-1.5 py-0.5 text-micro font-medium`
- Variants: `success`, `warning`, `destructive`, `info`, `muted`

## 8. Customer-facing copy replacements

| Old | New | File |
|---|---|---|
| `Live operations of the HappyRobot inbound carrier voice agent. Metrics computed against the Twin calls_log and bookings tables.` | `Inbound carrier desk · last 7 days` | `app/dashboard/page.tsx` |
| `Robot · Carrier Voice Agent` | `Acme Logistics · Carrier Operations` | `app/layout.tsx` |
| `Read-only mirror of HappyRobot Twin · server-only Bearer auth` | `● Online · Last sync 12s ago · v0.4.2 · Powered by HappyRobot` | `app/layout.tsx` |
| `Distinct booking rows in Twin.` | (delete) | `app/dashboard/page.tsx` |
| `Bookings (count)` | `Bookings` | `app/dashboard/page.tsx` |
| `Total Calls` | `Calls` | `app/dashboard/page.tsx` |
| `Booking Rate` | `Booked rate` | `app/dashboard/page.tsx` |
| `Calls that booked at least one load.` | (delete) | `app/dashboard/page.tsx` |
| `Avg Case Health` / `Pass threshold = 70.` | `Quality score` / (delete) | `app/dashboard/page.tsx` |
| `Outcome distribution` | `Calls by outcome` | `app/dashboard/page.tsx` |
| `No call outcomes captured. Run a HappyRobot test call to populate.` | `No calls in the selected window.` | `app/dashboard/page.tsx` |
| `What we listed (loads.loadboard_rate).` | (delete) | `economics-cards.tsx` |
| `What we paid carriers (bookings.apply_rate).` | (delete) | `economics-cards.tsx` |
| `Avg Loadboard Rate` | `Listed rate (avg)` | `economics-cards.tsx` |
| `Avg Agreed Rate` | `Booked rate (avg)` | `economics-cards.tsx` |
| `Effective Delta` | `Margin captured` | `economics-cards.tsx` |
| `Total Revenue Booked` / `Sum across N bookings.` | `Revenue booked` / `Across ${N} loads` | `economics-cards.tsx` |
| `Avg Call Duration` | `Call duration (avg)` | `operational-cards.tsx` |
| `FMCSA Decline Rate` | `Carriers turned away` | `operational-cards.tsx` |
| `Abandon Rate` | `Drop-offs` | `operational-cards.tsx` |
| `Avg Case Health Score` | `Quality score (avg)` | `quality-pies.tsx` |
| `Most recent N calls. Click an MC to drill into a carrier.` | `Last ${N} calls. Click an MC to open the carrier.` | `app/dashboard/calls/page.tsx` |
| `No calls in the window. Trigger a HappyRobot test call to populate this table.` | `No calls in the selected window. Adjust the date range or wait for the next inbound.` | `calls-table.tsx` |
| `Recent auditor remarks` | `Quality flags from recent calls` | `app/dashboard/page.tsx` |
| `Conv %` | `Booked %` | `carrier-rollup-table.tsx` |

**Tone rules:**
1. Never reference `Twin`, `calls_log`, `bookings`, etc.
2. Don't say "metric" — name what it is.
3. Prefer noun phrases for KPI labels.
4. Hints clarify units/thresholds, never repeat label or describe internals.
5. No "this dashboard…" — dashboard is invisible.
6. No "we" / "you".

## 9. Empty states

| Surface | Copy |
|---|---|
| Calls table, window has no calls | `No calls in the selected window. Try widening the date range, or wait for the next inbound.` |
| Carriers table, none in window | `No carriers in the selected window.` |
| Carrier drilldown, MC has no calls | `No calls on record for MC #${mc} in this window.` |
| Outcome chart, no outcomes | `No calls in the selected window.` |
| Sentiment pie, no data | `Sentiment captures once calls complete.` |
| Quality remarks list, none flagged | `No quality flags in this window — clean run.` |
| Effective delta KPI, no data | `—` |
| Carrier profile, MC not found | `No calls on record for MC #${mc} in the selected window.` |
| Live indicator, no active call | `Idle` |
| Live indicator, status unknown | `Status unknown` |
| API status, offline | `Offline · retrying` |

Tone: short, factual, never apologetic. Suggest action only when one exists.

## Summary

- **Recommended default palette:** Option A — Dark Ops Console
- **Recommended header copy:** `Acme Logistics · Carrier Operations`
- **Recommended tab indicator:** bottom underline (global nav) + shadcn pill (inner tabs)
- **Top 3 visual changes for max impact:**
  1. Swap palette + replace header (one-day change)
  2. Strip documentation copy (~10 files; mechanical)
  3. Add active-tab underline + sticky header with live indicator
