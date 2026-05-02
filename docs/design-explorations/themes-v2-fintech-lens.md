# Themes v2 — Fintech-Lens Design Languages

Drafted 2026-04-30. Replaces the rejected v1 set (`themes-9-dark.md`), which the user correctly flagged as "all the same neon sand style" — palette-only variation on identical layout assumptions. This round produces **structurally distinct design languages**, not hex-code reskins. Each theme inherits a different fintech ancestor (Mercury / Bloomberg / Stripe / Robinhood / Carta / Brex / Ramp / Wise / Plaid) and re-thinks the KPI tile, table row, hero metric, and ticker bar from scratch.

The freight-broker ops desk sits at an unusual intersection: every booking is a P&L event, every call is a reactive conversation, every load is an inventory item with a deadline. That is a trader's desk wearing a dispatcher's hat. The four sub-languages below take that brief in four distinctly different directions.

---

## Theme A — **Treasury Note** (Mercury × Carta)

> Soft, light-mode-first, generous whitespace, editorial serif numerics, single-column reading order. The dashboard reads like a private-bank quarterly statement, not a Datadog screen.

**Inspiration source.** Mercury's banking app for the foreground hierarchy (large quiet headers, oversized numerics, enormous gutters, near-zero chrome) crossed with Carta's private-equity formality (serif display face for the hero number, restrained color, hairline rules instead of card shadows). The signal here is deliberate calm: a broker reviewing yesterday's P&L over coffee, not a dispatcher firefighting at 2pm.

### Typography
- **Display / hero numerics:** `"Tiempos Headline", "Source Serif 4", "GT Sectra", Georgia, serif` — weight 400, tabular-nums, letter-spacing -0.02em. Used only for hero metric blocks ($XXX,XXX margin, top-of-tab) and section dividers.
- **UI sans:** `"Inter", "SF Pro Text", system-ui` — weights 400 / 500 / 600. Body 14px / line-height 1.55. Section headings 13px / 600 / tracking 0.04em / uppercase.
- **Tabular numerics for tables:** `"JetBrains Mono", "SF Mono", ui-monospace` — 13px, tabular-nums. Reserved for table cells only; hero numbers stay serif.
- **Scale:** 11 / 12 / 13 / 14 / 16 / 22 / 32 / 56 / 88. The 56 / 88 sizes only appear in hero serif numerics.

### Color tokens (light)
| Token | Hex |
|---|---|
| `--bg` | `#FAF8F4` |
| `--surface` | `#FFFFFF` |
| `--surface-elevated` | `#FFFFFF` |
| `--border` | `#EDE8DF` |
| `--border-strong` | `#D7D0C3` |
| `--fg` | `#1A1A1A` |
| `--fg-muted` | `#6B6B6B` |
| `--primary` | `#1F3A2E` (forest ledger) |
| `--primary-fg` | `#FAF8F4` |
| `--accent` | `#B8945C` (warm brass — used 2-3 times per screen, max) |
| `--success` | `#2E6B4A` |
| `--warning` | `#A66A1F` |
| `--danger` | `#9C3A2E` |
| `--chart-1` | `#1F3A2E` |
| `--chart-2` | `#B8945C` |
| `--chart-3` | `#5C7A8C` |
| `--chart-4` | `#A66A1F` |
| `--chart-5` | `#9C3A2E` |

### Spacing — `4 / 8 / 12 / 16 / 24 / 40 / 64 / 96`. Page padding 64px desktop, 40 mobile. Section vertical rhythm 96px between major blocks. KPI row gap 40px. **This is the spacious end** — empty space carries meaning.

### Radius — `0 / 2 / 4`. Almost nothing is rounded. Tables and KPI tiles have **2px** corners; buttons **4px**; inputs **2px**. Hairline aesthetic.

### Shadow scale — **none.** Hierarchy is conveyed by hairline borders (`1px solid var(--border)`) and whitespace, not elevation. Drill-down panels use `border-left: 3px solid var(--primary)` instead of a drop shadow.

### Component patterns
- **KPI tile.** No card. No background. No border. Just stacked text on the page background:
  - line 1: 11px / uppercase / tracking 0.08em / `--fg-muted` — the label ("MARGIN CAPTURED, MTD")
  - line 2: 56px serif / `--fg` — the value ($142,038)
  - line 3: 13px sans / `--fg-muted` with a tiny inline triangle glyph — the delta ("▲ 12.4% vs prior month")
  - hairline `border-bottom: 1px solid var(--border)` at 24px below, the only chrome.
  Tiles are arranged in a **single horizontal row of 3-4** with 64px gaps, never the 4×2 grid that v1 used.
- **Hero metric block.** Page-top, full bleed inside the 64px gutter. Label small-caps above; **88px serif** value; one-line context sentence below in 14px italic sans ("Up from $128,401 last month, on 47 bookings").
- **Chart card.** White surface, `border: 1px solid var(--border)`, no shadow, 32px internal padding, 4px radius. Title in 13px / 600 / uppercase / tracked. Y-axis labels are removed entirely; instead, two horizontal hairlines mark min and max, annotated inline.
- **Table row.** 48px tall (comfortable, not dense). No alternating zebra. **Hairline bottom border only.** Numerics in mono right-aligned; text columns in sans. Hover = subtle `--bg` shift, no other state.
- **Status pill.** Not a pill at all — a **lowercase text label preceded by a 6px filled circle** colored by status. `● booked` `● negotiating` `● flagged`. No border, no background fill. This deviates structurally from the bordered pills v1 used everywhere.
- **Delta indicator.** A unicode triangle glyph (`▲ ▼`) at 90% size, color-coded, followed by the percentage. No background chip.
- **Ticker bar.** None. This theme rejects tickers — they are too visually loud for the calm.
- **Drill-down panel.** Slides in from the right, occupies 480px, white surface with a 3px `--primary` left border. Closes with esc. No backdrop dim — the page beside it stays readable.
- **Button.** Filled primary uses `--primary` background; secondary is a **pure text button** with a hairline underline on hover, no border, no fill. Icon buttons are 32×32 with no background until hover.

### Motion
- **Subtle, slow.** `cubic-bezier(0.4, 0, 0.2, 1)`, 280ms for panel slides, 180ms for hover-color, 0ms for everything else. No skeleton shimmer — empty states show "—" instead. No counter-rolling animation on numbers (numbers fade in at 220ms).

### Numeric presentation
**Hero numbers are huge serif** (56-88px). **Body numbers are mono inline** (13px). **No "huge bold sans" anywhere.** The contrast is editorial → tabular, never display-bold → display-bold.

### Grid + ordering
**Single-column reading order.** Hero metric on top, then a horizontal row of 3 KPIs, then a single full-width chart, then a single full-width table. The page reads like a one-page summary, not a four-quadrant terminal. Mobile-friendly by accident.

### Diff vs. the other v2 themes
- **vs. Bloomberg Pit:** A is light-mode + serif + ultra-spacious; Pit is black-bg + mono-only + ultra-dense. Opposite ends of the density axis.
- **vs. Robinhood Floor:** A's hero number is a calm 88px serif with a 14px italic sentence underneath; Floor's hero is a 64px sans with a sparkline mounted to the right and a 24px live-shimmer delta chip. A is a quarterly statement; Floor is a live tape.
- **vs. Brex Operator:** A has zero shadows and 2px radii; Brex Operator uses 12px radii with soft 3-layer shadows and brand gradient washes — they look opposite at 50ft.

### Why this fintech sub-language fits a freight-broker ops desk
The owner-broker reviewing weekly P&L is the right audience for this language. Carrier-ops staff in firefight mode have other tabs (Calls, New Bookings) where density-themes make sense — but the **Overview** page is a financial-statement page, and Mercury proved that a banking page reads better with whitespace than with chrome. Treasury Note signals "this brokerage runs like a private bank," which is a recruiting and trust signal as much as a UX one.

---

## Theme B — **Bloomberg Pit** (Bloomberg Terminal × Plaid Dashboard)

> Black background, monospace everywhere, four-quadrant grid, dense tabular numerics. The dashboard reads like a trading terminal: every pixel earns its place.

**Inspiration source.** Bloomberg Terminal for the **layout philosophy** (4-quadrant immutable grid, no scrolling within quadrants, function-key navigation, mono numerics that align across all panels). Plaid's developer dashboard for the **typographic restraint** (single mono family, two weights, neutral palette, color used only for state). The signal here is institutional density: a senior dispatcher running 12 lanes simultaneously needs to see everything without scrolling.

### Typography
- **Single mono family for everything:** `"IBM Plex Mono", "Berkeley Mono", "JetBrains Mono", ui-monospace` — weights 400 and 600 only. No serif, no proportional sans anywhere.
- **Scale (tight):** 10 / 11 / 12 / 13 / 14 / 18 / 24. **No size above 24px.** Hero numerics are 24px mono / 600. The terminal aesthetic demands small text.
- **Letter-spacing:** 0.02em on labels, 0 on data. Line-height 1.3 (tight).
- **All-caps for ALL labels and headings** — section headings, column headers, KPI labels, button text. Body data is mixed case.

### Color tokens (dark, near-black)
| Token | Hex |
|---|---|
| `--bg` | `#0A0A0A` |
| `--surface` | `#0F0F0F` |
| `--surface-elevated` | `#161616` |
| `--border` | `#2A2A2A` |
| `--border-strong` | `#3D3D3D` |
| `--fg` | `#E6E6E6` |
| `--fg-muted` | `#7A7A7A` |
| `--primary` | `#FFB800` (Bloomberg amber) |
| `--primary-fg` | `#0A0A0A` |
| `--accent` | `#FFB800` |
| `--success` | `#00D26A` |
| `--warning` | `#FFB800` |
| `--danger` | `#FF3838` |
| `--chart-1` | `#FFB800` |
| `--chart-2` | `#00D26A` |
| `--chart-3` | `#FF3838` |
| `--chart-4` | `#5BC0EB` |
| `--chart-5` | `#E6E6E6` |

The palette is **deliberately limited** — only amber/green/red/cyan/white. Every additional color the v1 themes used (purple chart-5, teal accent, etc.) is removed. State is encoded by hue; identity is encoded by position.

### Spacing — `2 / 4 / 8 / 12 / 16`. **Cap is 16px.** Page padding 12px. Quadrant gutter 1px (a hairline grid divider, not whitespace). KPI row gap 4px. This is the dense end.

### Radius — `0`. Everything is square. Buttons, tiles, inputs, modals. Square corners are part of the terminal language.

### Shadow scale — **none, ever.** Elevation is conveyed by `border: 1px solid var(--border)` only. Even modals get a hairline border, not a drop shadow.

### Component patterns
- **KPI tile.** A 4-line mono cell, no card chrome:
  - line 1: 10px / uppercase / `--fg-muted` — the four-letter ticker code ("BKDR" for booked-rate, "MGNC" for margin-captured)
  - line 2: 24px / 600 / `--fg` — the value, right-aligned (`$142,038`)
  - line 3: 11px / `--fg-muted` — three columns of mini stats (PREV / DELTA / WK-AVG), pipe-delimited
  - line 4: 10px / `--fg-muted` — timestamp ("UPDATED 14:23:04 EDT")
  Tiles arranged in a **strict 6-across grid** at the top of every tab. Six KPIs, not three; density is the point.
- **Hero metric block.** Doesn't exist. There is no hero. Every metric is equal-rank in the grid. This is the structural opposite of Treasury Note.
- **Chart card.** Quadrant-tile within a 2×2 layout. `border: 1px solid var(--border)`, no padding (chart fills edge-to-edge), title bar at top with a `border-bottom`. Title is 11px / uppercase / amber. Recharts axis text is 10px mono. Sparklines preferred over full charts whenever the metric is single-series.
- **Table row.** **24px tall** (extremely dense). 11px mono. Alternating row backgrounds (`--bg` / `--surface`) for tape-reading. Numerics right-aligned; positive in green, negative in red; **no neutral state** — every number is colored. Sort indicators are inline `▲▼` glyphs in the column header.
- **Status pill.** Not a pill. A **single uppercase letter** in a 16px square: `B` for booked (green bg), `N` for negotiating (amber bg), `F` for flagged (red bg). Mono / black foreground. Hover-tooltips reveal the full word.
- **Delta indicator.** Inline mono: `+12.4% ▲` or `-3.1% ▼`. Always 11px, always colored, never in a chip.
- **Ticker bar.** **Yes** — a 28px-tall band fixed at the top of the viewport, scrolling horizontally with all 12 active loads + their carrier offers, real-time. CSS-keyframe `transform: translateX` over 90s. This is the most pronounced motion in the theme; it is the theme's signature.
- **Drill-down panel.** Replaces the bottom-right quadrant in place — does not slide over. The other three quadrants stay live.
- **Button.** `border: 1px solid var(--fg-muted)`, no background, mono uppercase text, hover swaps to amber border + amber text. Primary action button is the only one with `background: var(--primary)`.

### Motion
- **Pronounced where it carries information.** Ticker bar scrolls continuously. Numbers that update flash a 1-frame `--primary` background then fade to neutral over 600ms — the classic Bloomberg "value changed" cue. Everything else is 0ms (instant). No easing on hover.

### Numeric presentation
**Dense tabular, mono-only, sized small (11-24px), colored by sign.** Negative margin is red; positive is green; zero/neutral is `--fg`. Numbers are the primary visual content — text labels are deliberately tiny.

### Grid + ordering
**Strict 4-quadrant grid** (or 2×3 for 6 KPIs). Each quadrant is independently scrollable; the page itself does not scroll. Quadrant borders are hairlines. **No reading order** — every quadrant is equal-rank, you grok them simultaneously.

### Diff vs. the other v2 themes
- **vs. Treasury Note:** Pit is everything Treasury Note rejects — black, mono, dense, square, no whitespace, no hero. They are the two structural extremes.
- **vs. Robinhood Floor:** Both are dark and trading-themed, but Floor uses a sans+mono pair with a single oversized hero metric and a sparkline-dominant aesthetic; Pit uses mono-only, no hero, full-table dominance. Floor is consumer-trading; Pit is institutional.
- **vs. Brex Operator:** Pit is the harsh-utility opposite of Brex Operator's soft-rounded enterprise polish. Pit has zero radii, no shadows, no gradients; Operator has all three.

### Why this fintech sub-language fits a freight-broker ops desk
A senior dispatcher running 12 simultaneous lanes is doing the same job as a Bloomberg user running 12 watchlists. Glance-driven, multi-asset, time-sensitive. The institutional-density aesthetic is genuinely the right tool for that job — not a costume. It also signals "this brokerage trades freight like a real desk trades futures," which is a compelling narrative for the demo. The cost is that it intimidates non-power users — which is fine, because junior staff use the Calls tab, not Overview-Pit.

---

## Theme C — **Robinhood Floor** (Robinhood Pro × Wise)

> Dark background, sans-display hero numerics with sparkline pairing, big rounded cards, generous accent green for "money in." Consumer-trading bold meets multi-currency clarity. The dashboard reads like a portfolio app.

**Inspiration source.** Robinhood Pro for the **hero-metric pattern** (oversized sans number paired with a wide sparkline as background or sibling, animated on update, accent-green for positive, accent-red for negative). Wise for the **multi-currency clarity** (each KPI has a distinct hue identity, currency badges, a "you got X" framing). The signal: the broker is a portfolio manager; each booking is a position.

### Typography
- **Display sans:** `"Söhne", "Inter Display", "SF Pro Display", system-ui` — weights 500 and 700. Hero numerics 500 (lighter than expected — counterintuitively elegant). Letter-spacing -0.03em on hero. No serif anywhere.
- **UI sans:** `"Inter", "SF Pro Text", system-ui` — 400 / 500 / 600. Body 14px / line-height 1.5.
- **Mono only inside tables:** `"SF Mono", "JetBrains Mono"` — 13px / 400 / tabular-nums. Mono does NOT appear in KPI tiles or headers.
- **Scale:** 12 / 13 / 14 / 15 / 17 / 22 / 28 / 40 / 64. Hero metric is 64px sans / 500.

### Color tokens (dark, lifted-charcoal)
| Token | Hex |
|---|---|
| `--bg` | `#1A1A1F` |
| `--surface` | `#22232A` |
| `--surface-elevated` | `#2C2D36` |
| `--border` | `#34353F` |
| `--border-strong` | `#4A4C58` |
| `--fg` | `#F5F5F7` |
| `--fg-muted` | `#A0A1AC` |
| `--primary` | `#00D982` (Robinhood-green for "money in") |
| `--primary-fg` | `#04200F` |
| `--accent` | `#7B61FF` (Wise-purple for routing/lane identity) |
| `--success` | `#00D982` |
| `--warning` | `#FFB948` |
| `--danger` | `#FF4D5E` |
| `--chart-1` | `#00D982` |
| `--chart-2` | `#7B61FF` |
| `--chart-3` | `#FFB948` |
| `--chart-4` | `#FF4D5E` |
| `--chart-5` | `#5DC2F5` |

Surface stack is **lifted charcoal**, not near-black — the page background is `#1A1A1F`, surfaces are noticeably brighter, which is the consumer-trading "soft dark" treatment (vs. Pit's institutional near-black).

### Spacing — `4 / 8 / 12 / 16 / 20 / 24 / 32`. Comfortable, not spacious. Page padding 24px. KPI grid gap 16px.

### Radius — `8 / 12 / 16 / 24`. **Generous rounding.** Cards are 16px. Pills are fully rounded (9999px). Inputs are 12px. Buttons are 12px. The aesthetic is friendly-modern.

### Shadow scale — **soft, single layer.**
- `--shadow-card`: `0 1px 0 rgba(255,255,255,0.04) inset, 0 0 0 1px rgba(255,255,255,0.02)` — a hairline inner highlight rather than a drop shadow. (Drop shadows on dark backgrounds vanish; inner highlights work better.)
- `--shadow-elevated`: `0 8px 32px rgba(0,0,0,0.4)` for modals and drill-downs.

### Component patterns
- **KPI tile.** A **rounded 16px card with a sparkline mounted along the bottom edge**, full-width:
  - top-left: 13px / 500 / `--fg-muted` — label ("Booked Revenue, today")
  - middle-left: **64px / 500 / sans** — value (`$142,038`), with the trailing zeros in `--fg-muted` (`$142,**038**` styled `$142,**.038**` muted)
  - top-right: a pill-shaped delta chip in success-green or danger-red, fully rounded, 14px / 600, with an inline triangle (`▲ 12.4%`)
  - **bottom edge: a 32px-tall sparkline that bleeds to the card edges**, accent-green fill at 20% opacity under the line. This is the signature element.
  Tiles arranged in a **2×2 grid** for the 4 primary KPIs (calls / bookings / revenue / margin), each ~280px wide.
- **Hero metric block.** Single oversized card spanning two columns. The hero **value lives on the left** (64px sans) with the label above (13px), and **a full-bleed Recharts area chart fills the right two-thirds of the card** as a backdrop. The value sits *over* the chart's mute zone, layered. This is the Robinhood signature pattern.
- **Chart card.** 16px radius, surface bg, 24px padding. Title 15px / 600. Chart fills below the title with full width. Toolbar (date range pills, granularity toggle) lives in the **top-right of the card**, fully rounded pill buttons.
- **Table row.** 56px tall (comfortable). Alternating row treatment OFF. Hover lifts the row by adding the `--surface-elevated` background and a 1px primary border-left. Numerics in mono right-aligned; carrier names in sans 500. **First column has a 32px circular avatar** (carrier logo or MC initials) — the visual anchor.
- **Status pill.** **Fully rounded pills with filled backgrounds at 15% opacity over the surface, and the dot color at full opacity.** `[● Booked]` with `bg: rgba(0,217,130,0.15)`, `color: #00D982`, `border: 1px solid rgba(0,217,130,0.3)`. 24px tall, 12px horizontal padding. **The "rounded chip with translucent fill" is this theme's signature** — explicitly different from Pit's square-letter and Treasury Note's bare-text-with-dot.
- **Delta indicator.** A pill-shaped chip (full-rounded, 24px tall) with translucent green/red background, icon + value. Lives in the top-right of every KPI tile. The chip is a recurring shape across the theme — it appears on KPI tiles, on table cells (for margin), on chart legends.
- **Ticker bar.** Optional. If present: a single horizontal scrolling row at top showing recent bookings as **rounded 32px cards** ("ATL→DAL · $2,400 · ▲ booked 2m ago"), each card is its own pill. Pills slide in from the right at 600ms ease-out as new bookings arrive.
- **Drill-down panel.** Slides up from the bottom (mobile-style sheet) on tablet, slides in from the right on desktop. 16px radius on the leading edge. Has its own chart-and-pill sub-layout. **Uses the elevated shadow.**
- **Button.** Primary: filled green, 12px radius, 40px tall, 600 weight, white-ish foreground. Secondary: outlined with `--border-strong`, same shape. Tertiary: text-only with hover-underline. **All buttons are pill-friendly** (high radius / height ratio).

### Motion
- **Pronounced and celebratory.** Numbers animate via counter-roll over 1200ms with `cubic-bezier(0.16, 1, 0.3, 1)` (overshoot easing) on every update. Sparklines redraw with a 800ms left-to-right wipe. New booking pills slide-in + bounce. Hover transitions 180ms. Skeleton-shimmer state on first load, 1500ms duration. **This is the most motion-heavy theme** — the consumer-trading "feel good when number go up" energy.

### Numeric presentation
**Hero-and-context.** Big sans hero numbers paired with a sparkline below or behind them. Trailing zeros muted. Positive movement is the brand-defining moment — green, animated, celebrated. Body numbers are mono and right-aligned in tables, sans and centered in pills.

### Grid + ordering
**2×2 KPI grid** at the top, then a **2-column main area** (chart on left, recent-bookings list on right), then a single full-width table. The grid is rectangular (always pairs of cards), reinforcing the "portfolio of positions" frame.

### Diff vs. the other v2 themes
- **vs. Treasury Note:** Floor is dark / sans / animated / pill-heavy / chart-backdrop hero; Treasury is light / serif / motion-free / hairline-only. Different planet.
- **vs. Bloomberg Pit:** Both are dark, but Floor has 16px radii vs. Pit's 0px, soft inner-highlight shadows vs. Pit's none, sparkline-backdrop hero vs. Pit's no-hero, pill chips vs. Pit's square letters.
- **vs. Brex Operator:** Both have rounded cards, but Floor's shadow strategy is inner-highlight (subtle on dark), Operator's is multi-layer drop-shadow on light cream. Floor's accent is green-and-purple; Operator's is brand-orange-and-warm-cream. Floor is consumer-app energy; Operator is enterprise-product polish.

### Why this fintech sub-language fits a freight-broker ops desk
The owner-broker watching daily booking revenue is, emotionally, a Robinhood user watching a portfolio. The "money came in" moment matters; the green animated counter is a dopamine hit that keeps them on the dashboard. For demo purposes, this theme is **the most screenshot-friendly and Loom-friendly** — recruiters and reviewers respond to the consumer-app polish. It is also the theme where "Acme Logistics" can lean into a consumer-trading brand identity if the company decides that's the positioning.

---

## Theme D — **Brex Operator** (Brex × Ramp × Stripe)

> Light background with cream accents, oversized weight-contrast typography, brand-orange call-to-actions, multi-layer soft shadows, generous 12px radii. The dashboard reads like a modern enterprise SaaS — Brex's spend dashboard or Ramp's expense view.

**Inspiration source.** Brex's spend dashboard for the **layered card hierarchy** (cream-tinted background, white surface cards with multi-layer shadows, brand-orange CTA chips, bold sans heroes paired with subtle context lines, brand-illustration accents on empty states). Ramp's transaction view for the **table-as-feed pattern** (timeline-style transaction rows with leading metadata column and trailing action column). Stripe Dashboard for the **typographic weight contrast** (paired 17px regular labels with 32px medium values, generous 32px gutters, subtle gradient washes behind hero blocks). The signal: this brokerage runs operations like a YC-grade enterprise SaaS.

### Typography
- **Display sans (heavy):** `"Söhne Breit", "Inter Display", "Söhne", system-ui` — weights 500 / 600 / 700. **Weight contrast is the move** — 17px regular labels paired with 32px medium values create a "Stripe-feel" hierarchy without size-only differentiation.
- **UI sans:** `"Inter", system-ui` — 400 / 500. Body 15px / line-height 1.5 (slightly larger than the others — Brex/Ramp use larger body text).
- **Mono ONLY for transaction IDs / load IDs / MC numbers:** `"JetBrains Mono"`, 13px. Numerics in body and tables use **sans tabular-nums**, NOT mono. This is a deliberate departure — Brex uses sans-tabular for amounts.
- **Scale:** 12 / 13 / 15 / 17 / 20 / 24 / 32 / 48. Hero is 48px / 600. KPI value is 32px / 500.

### Color tokens (light with cream warmth)
| Token | Hex |
|---|---|
| `--bg` | `#FAF6F0` (cream wash) |
| `--surface` | `#FFFFFF` |
| `--surface-elevated` | `#FFFFFF` |
| `--border` | `#E8E2D6` |
| `--border-strong` | `#D4CCB8` |
| `--fg` | `#1F1F1F` |
| `--fg-muted` | `#6E6E6E` |
| `--primary` | `#FF5C26` (Brex-orange) |
| `--primary-fg` | `#FFFFFF` |
| `--accent` | `#1F1F1F` (high-contrast black for secondary CTAs — Brex pattern) |
| `--success` | `#0E7B3F` |
| `--warning` | `#B66A05` |
| `--danger` | `#C4322A` |
| `--chart-1` | `#FF5C26` |
| `--chart-2` | `#1F4E78` |
| `--chart-3` | `#0E7B3F` |
| `--chart-4` | `#B66A05` |
| `--chart-5` | `#7B4F9C` |

Surface is pure white **on a cream background** — the contrast between `#FAF6F0` and `#FFFFFF` is the cue that signals "this is a card." This is structurally different from any v1 theme and from the other v2 themes (Treasury is white-on-cream-but-borderless; Operator is white-on-cream-with-multi-layer-shadow).

### Spacing — `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64`. Page padding 32px. KPI grid gap 24px. Section gap 48px. Comfortable-to-spacious.

### Radius — `4 / 8 / 12 / 16`. Cards 12px (the Brex signature). Buttons 8px. Inputs 8px. Pills 9999px (fully rounded). Avatars 9999px.

### Shadow scale — **multi-layer soft shadows.** This is the most distinctive axis.
- `--shadow-card`: `0 1px 2px rgba(31,31,31,0.04), 0 4px 12px rgba(31,31,31,0.04)` — subtle two-layer.
- `--shadow-card-hover`: `0 2px 4px rgba(31,31,31,0.06), 0 12px 24px rgba(31,31,31,0.08)` — lifts on hover.
- `--shadow-elevated`: `0 4px 8px rgba(31,31,31,0.06), 0 24px 48px rgba(31,31,31,0.12)` — modals.

The card-hover lift is a key interaction cue.

### Component patterns
- **KPI tile.** A **white card on cream background** with multi-layer shadow:
  - top: a 32×32 brand-tinted icon in a 8px-radius square (orange tint at 10% opacity background, orange icon foreground) — this icon-as-anchor is the Brex/Ramp signature
  - row 2: 13px / 500 / `--fg-muted` — label
  - row 3: **32px / 500 / sans tabular-nums** — value
  - row 4: a single line combining the delta and a context phrase: `↑ $14k vs last week` in 13px / `--success`
  - bottom-right corner: a tiny "→" link icon that drills down on click
  16px internal padding. Tiles in a **3-across grid** (3 KPIs, not 4 or 6) at the top of Overview. Hover-lifts via shadow change + 1px translate-y.
- **Hero metric block.** A **wide cream-gradient card** spanning the full top of the page with a subtle radial gradient wash (`radial-gradient(ellipse at top right, rgba(255,92,38,0.06), transparent 60%)`). 48px label-and-value pair on the left, an illustration or sparkline on the right, an orange "View report →" pill button in the bottom-right.
- **Chart card.** White surface, 12px radius, multi-layer shadow, 24px padding. Title in 17px / 600. Toolbar in the top-right with **8px-radius pill toggles** (the Brex segmented-control pattern). Chart fills below.
- **Table row.** 64px tall (spacious-feed style — Ramp transaction row). Each row has:
  - **Leading column (left, 48px wide): a colored circular avatar** with the carrier MC's initials, brand-tinted by carrier-status (orange for active, gray for inactive)
  - middle column: stacked text — line 1 carrier name (15px / 500), line 2 lane in `--fg-muted` (13px)
  - data columns: 15px sans-tabular numerics
  - **trailing column (right): a "•••" overflow-action menu and a small status pill**
  - Row hover: subtle `--bg` background shift (no border change). Click opens drill-down.
- **Status pill.** **Fully rounded with solid-colored backgrounds at 12% opacity, dark-colored text, NO border.** `[Booked]` with `bg: rgba(14,123,63,0.12)`, `color: #0E7B3F`. 22px tall, 10px horizontal padding, 13px / 500 text. **Filled-tint pills** are the Brex/Ramp pattern — distinct from Floor's bordered translucent pills, Pit's square letters, and Treasury Note's bare text.
- **Delta indicator.** Inline text with a colored arrow glyph at 90% size: `↑ 12.4%` in `--success`. NOT in a chip — context is conveyed by proximity to the value, not container.
- **Ticker bar.** Optional second-tier UI element: a horizontal **list of recent-event chips** (not a continuously scrolling band). Each chip is a 32px-tall fully-rounded pill. Chips fade in from the left and dismiss after 8s, like a notification stream.
- **Drill-down panel.** Right-side sheet, 560px wide, 16px radius on the leading edge, multi-layer elevated shadow, **dimmed backdrop** at 30% black. Internal padding 32px. Has a sticky header with the carrier name + a "View full profile →" link.
- **Button.** Primary: `bg: var(--primary)`, white foreground, 8px radius, 36px tall, 500 weight, 16px horizontal padding. Hover: subtle shadow + `bg-primary` darker shade. Secondary: `bg: var(--accent)` (black) with white text — the Brex high-contrast secondary CTA pattern. Tertiary: text-only.

### Motion
- **Subtle but present.** Hover transitions 200ms `cubic-bezier(0.4, 0, 0.2, 1)`. Card-lift on hover combines a `translateY(-1px)` and shadow-strengthening. Number changes use a 400ms fade-in (no counter-roll). Skeleton shimmer at 1200ms. Drill-down sheet 320ms ease-out. **No continuous motion** (no scrolling tickers, no auto-refreshing pulses) — motion is reserved for user-initiated state changes.

### Numeric presentation
**Sans tabular-nums everywhere — no mono.** The 32px / 500 KPI value paired with a 13px label and a 13px context-phrase delta is the recurring rhythm. Trailing decimals are NOT muted (full opacity, full weight) — Brex commits to the precision.

### Grid + ordering
**3-across KPI grid** → **wide hero card** (or vice versa, depending on which is the focus tab) → **2-column body** (chart on left, activity feed on right) → **full-width table**. The hierarchy is "KPIs as scoreboard, hero as featured, then drill-deeper sections." This is the standard Brex/Ramp dashboard reading order.

### Diff vs. the other v2 themes
- **vs. Treasury Note:** Both light, but Operator has multi-layer shadows (Treasury has none), 12px radii (Treasury has 2px), brand-orange CTA (Treasury has forest-green), sans-only typography (Treasury has serif heroes), 64px table rows with avatars (Treasury has 48px borderless rows). They share a light-mode base but diverge on every other axis.
- **vs. Bloomberg Pit:** They are opposite ends of the density-and-warmth spectrum. Pit is square-cold-mono-dense; Operator is rounded-warm-sans-comfortable.
- **vs. Robinhood Floor:** Both have generous radii and pill chips, but Floor is dark with translucent-bordered pills + sparkline-backdrop heroes + animated counters, while Operator is light with filled-tint pills + cream-gradient heroes + static numerics. Floor is consumer-emotional; Operator is enterprise-considered.

### Why this fintech sub-language fits a freight-broker ops desk
A growing brokerage hiring its second and third operations staff needs a dashboard that **looks like the SaaS tools the team already pays for** (Ramp for spend, Brex for cards, Stripe for payments). Familiarity reduces onboarding friction and signals "this brokerage uses modern tools." The brand-orange CTA also gives the broker a single visually-loud color to use in marketing collateral — every dashboard screenshot becomes a brand asset. Treasury Note signals private-bank trust; Operator signals modern-enterprise growth.

---

## Per-axis comparison matrix

| Axis | A — Treasury Note | B — Bloomberg Pit | C — Robinhood Floor | D — Brex Operator |
|---|---|---|---|---|
| **Mode** | Light, cream | Dark, near-black | Dark, lifted-charcoal | Light, cream-on-white |
| **Type families** | Serif (hero) + Sans (UI) + Mono (table) | Mono only | Sans (display+UI) + Mono (table) | Sans only (incl. tabular) + Mono (IDs) |
| **Hero size** | 88px serif | None — no hero | 64px sans + sparkline | 48px sans + cream-gradient card |
| **Density** | Spacious (64px gutters) | Dense (12px page padding) | Comfortable (24px) | Comfortable-spacious (32px) |
| **Radius** | 0-2-4 | 0 | 8-12-16-24 | 4-8-12-16 |
| **Shadow** | None | None | Inner highlight + soft elevated | Multi-layer soft (signature) |
| **KPI tile shape** | Borderless stacked text | 4-line mono cell, 6-across | Rounded card w/ sparkline-bottom | White card on cream, icon-anchored, 3-across |
| **Hero pattern** | 88px serif on bare bg | Doesn't exist | Sans value layered on chart | Cream-gradient banner card |
| **Status indicator** | `● booked` text+dot | Square letter `B` | Translucent bordered pill | Filled-tint rounded pill, no border |
| **Delta indicator** | `▲ 12%` glyph + text | Inline mono colored | Pill chip in tile corner | Inline arrow glyph, no chip |
| **Ticker** | None (rejected) | Continuous scrolling band (signature) | Pill-cards sliding in | Notification-stream pills |
| **Table row height** | 48px | 24px | 56px w/ avatar | 64px w/ avatar + overflow menu |
| **Motion** | Slow / minimal (220ms fade) | Pronounced (continuous ticker, value-flash) | Pronounced (counter-roll, sparkline wipe, bounce) | Subtle (200ms hover-lift, no continuous) |
| **Numeric philosophy** | Editorial serif hero + mono body | Tabular mono small, sign-colored | Sans hero + sparkline + muted-zero | Sans tabular weight-contrast |
| **Grid** | Single-column reading | 4-quadrant terminal | 2×2 KPI + 2-column body | 3-across KPI + 2-column body |
| **Reading audience** | Owner-broker, weekly review | Senior dispatcher, glance-driven | Owner-broker, daily P&L | Operations team, modern-SaaS familiar |
| **Demo signal** | "Runs like a private bank" | "Trades freight like futures" | "Consumer-app polished" | "Modern enterprise SaaS" |

---

## Notes for adoption

- All four themes are buildable on the locked stack (Next.js 15 + Tailwind 4 + shadcn/ui + Recharts) with **no library additions** beyond what ADR-011 already permits. The shadcn token set covers `--background`, `--foreground`, `--primary`, `--secondary`, `--accent`, `--muted`, `--muted-foreground`, `--border`, `--destructive`; the v2 themes' extra `--surface`, `--surface-elevated`, `--success`, `--warning`, `--chart-1..5`, `--border-strong`, `--fg-muted` tokens slot in alongside without conflict.
- Typography requires loading **at most three font families** per theme (none currently in the bundle). Treasury Note: Tiempos/Sectra (serif) + Inter + JetBrains Mono. Bloomberg Pit: IBM Plex Mono only. Robinhood Floor: Söhne Display + Inter + SF Mono. Brex Operator: Söhne Breit + Inter + JetBrains Mono. All four can be pulled from Google Fonts or Adobe Fonts; cost is one extra `<link>` per chosen theme.
- Recommend picking ONE theme and shipping it cleanly rather than building a theme switcher — the structural differences between themes touch component shapes (table row height, KPI tile structure, hero pattern) that cannot be cleanly abstracted behind CSS variables alone. A theme switcher would require parallel component variants per theme.
- If forced to choose two for a switch demo: Treasury Note (light) + Robinhood Floor (dark) is the cleanest pairing because they share a comparable component count even though they differ on every axis. Operator + Pit is the most dramatic contrast but requires the most variant components.
- All four themes hit WCAG AA on body text (≥4.5:1) by construction; chart palettes all clear 3:1 against their respective surfaces. Spot-check edge cases: Pit's `--fg-muted` on `--bg` runs ~4.6:1 (passes); Treasury Note's accent brass on cream runs ~3.4:1 — use it only for icons/borders, never small text.
