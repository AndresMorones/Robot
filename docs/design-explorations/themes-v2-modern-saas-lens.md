# Themes v2 — Modern SaaS Design-Languages

> Round 2. The previous round (`themes-9-dark.md`) was rejected as "all the same neon-sand style — palette swaps with identical layout." This round produces **structurally distinct design languages**, each rooted in a specific real-world SaaS tool's visual signature. KPI tile, table row, ticker, and button are intentionally different shapes per theme — not recolors.

Audience: Acme Logistics ops desk (long sessions), owner-broker, workflow author. Stack: Next.js 15 + Tailwind 4 + shadcn/ui + Recharts. No Tremor, nuqs, react-day-picker, date-fns, Popover-Calendar (per ADR-011).

---

## Theme 1 — "Dispatch Console" (Linear × Zed, dark, status-first)

**Inspiration.** Linear's calm, opinionated chrome (left rail, status pills, Cmd-K-everywhere) crossed with Zed's editor-grade typographic restraint and quiet-but-precise color use. The dashboard reads like a tool you live inside, not a report you skim. Status is the first-class citizen: every row, tile, and chart legend leads with a tiny shape-coded indicator before the number.

### Typography
- **Family stack.** UI: `"Inter Variable", "Inter", system-ui` (grotesque, neutral).
- **Numerals.** UI numbers use Inter `font-feature-settings: "tnum","cv11","ss03"` (tabular, slashed-zero). Code/IDs in `"JetBrains Mono Variable"` 12.5/13px.
- **Scale (px / line-height).** 11/16 micro-label, 12/18 caption, 13/20 body, 14/22 body-lg, 16/24 section-title, 20/28 page-title, 28/34 KPI hero, 40/44 hero-XL.
- **Weights.** 420 body · 520 emphasis · 600 page-title (variable axis; never 700, no bold blocks).
- **Letter-spacing.** -0.005em on body, -0.015em on KPI hero, +0.06em uppercase on 11px micro-labels.

### Color tokens (dark, blue-gray base)
```
--bg:               #0B0D10
--surface:          #101317
--surface-elevated: #161A20
--border:           #1F242C
--border-strong:    #2A313B
--fg:               #E6EAF0
--fg-muted:         #8893A3
--primary:          #5B8DEF   /* Linear-blue, restrained */
--primary-fg:       #0B0D10
--accent:           #A78BFA   /* used SPARINGLY — only for "in-progress" */
--success:          #34D399
--warning:          #F5B454
--danger:           #F87171
--chart-1:          #5B8DEF
--chart-2:          #34D399
--chart-3:          #F5B454
--chart-4:          #A78BFA
--chart-5:          #94A3B8
```

### Spacing (4px base, **tight Linear cadence**)
4 / 8 / 12 / 16 / 20 / 28 / 40. Tile padding 16. Table row vertical padding 8 (compact). Section gutter 28. Page gutter 40.

### Radius
6 everywhere. Pills 999. **No 12s, no 16s.** Crisp, restrained.

### Shadow
None on tiles. `inset 0 0 0 1px var(--border)` is the only "elevation" — borders do the work. Drilldown panel: `0 0 0 1px var(--border-strong)` + a 1px inner top highlight `inset 0 1px 0 #FFFFFF06`.

### Component patterns (structurally distinctive)
- **KPI tile.** *Horizontal layout.* Left: 4px-wide colored status bar (full tile height) → label stack (11px uppercase micro-label + 28px tabular hero) → right: a 14px-wide sparkline (40 datapoints, line only, no fill). Delta sits *to the right of the hero*, not below: `+12.4%` in 13px tabular, color-coded. No card shadow; the left status bar is the entire visual identifier.
- **Table row.** 36px tall, single-line. Leading 8px circle status dot · MC# in mono · carrier name in body · lane (origin → destination, em-dash separator) · CHS as inline `[██████░░] 72` mini-bar with monospace number. Hover: `--surface-elevated` background + 2px primary left border slides in (150ms ease-out).
- **Ticker (live calls).** Horizontal scroll-marquee disabled. Instead: vertical stack of 24px rows, newest fades in from top (`opacity 0→1, translateY -4→0, 220ms`). Each row = `time · MC · status-pill · 1-line summary`. Auto-prunes older than 10 entries.
- **Button.** Default: 28px tall, `--surface-elevated` fill, 1px `--border` outline, 13/20 medium. Primary: solid `--primary`, **no shadow, no gradient**. Hover: outline darkens to `--border-strong`, no fill change. Press: 1px translateY.
- **Drilldown panel.** Right-side slide-over, 480px wide, dark `--surface`. Header is a sticky 48px bar with breadcrumbs in 12px. Content is a 2-col definition list (`grid-template-columns: 140px 1fr`).

### Motion
Linear-subtle. 150–220ms `cubic-bezier(0.16, 1, 0.3, 1)` for state changes. Tab switches: opacity-only crossfade 120ms. No scale, no bounce. Skeletons are a static `--surface-elevated` rectangle (no shimmer).

### Information hierarchy
**Status-first.** Every list/row/tile leads with a shape-coded status (dot, bar, pill). Numbers come second. Names third.

### Grid
12-col strict, 24px gutters, 1280–1440 max content width. KPI strip: 4 tiles × 3 cols each. Charts: 8 cols + 4-col side-panel.

### Why this fits a freight-broker ops desk
Brokers triage **states** (open / pending / booked / dropped) faster than they read numbers. A status-first language matches how the work is actually scanned across an 8-hour shift. Linear's restraint avoids visual fatigue; Zed's mono numerics keep MCs and rates aligned in dense tables.

### Diff vs the others
- **Density:** tightest of all four (compact rows, 16px tile padding).
- **Decoration:** zero shadows, only borders + a status accent bar.
- **Hierarchy:** status comes BEFORE numbers (Theme 2 leads with numbers).
- **Radius:** 6 everywhere, no soft 12/16.
- **Numerals:** Inter tabular + JetBrains Mono for IDs; no display-serif.

---

## Theme 2 — "Bill of Lading" (Notion × Stripe Atlas, light, content-first)

**Inspiration.** Notion's content-first generosity (soft borders, room to breathe, type leads, decoration follows) crossed with Stripe Atlas's formal-but-warm prose-document feel. The dashboard reads like a structured operations document — sections have headings and intros, KPIs sit inline in prose like "We booked **12 loads** today across **8 carriers**," and tables feel like spreadsheet-tables-in-a-doc rather than data-grid-on-a-screen.

### Typography
- **Family stack.** Body & UI: `"Inter Variable", "Inter", system-ui` (humanist tuning via OpenType). **Display & section titles:** `"Tiempos Text", "Söhne", "Inter Display"` — a humanist serif-adjacent sans with warmer terminals. **Numerals (large only):** `"GT America Mono"` or `"Berkeley Mono"` 13px.
- **Scale.** 12/20 caption, 14/24 body (READING SIZE — not 13), 15/26 body-lg, 17/28 small-heading, 22/32 section-heading, 30/40 page-title, 44/52 KPI hero (yes, larger than Theme 1).
- **Weights.** 400 body · 500 emphasis · 600 headings · 700 reserved for KPI hero only.
- **Letter-spacing.** Default 0. Headings -0.01em. **Generous line-height** (`1.6` body) is the signature.

### Color tokens (warm light, off-white)
```
--bg:               #FAF9F6   /* warm paper, not pure white */
--surface:          #FFFFFF
--surface-elevated: #FFFFFF
--border:           #E8E4DC   /* warm taupe — not gray */
--border-strong:    #D6D0C4
--fg:               #1F1B16   /* warm near-black */
--fg-muted:         #6B6356
--primary:          #2C5F4A   /* deep ledger-green */
--primary-fg:       #FAF9F6
--accent:           #B45309   /* burnt-orange highlight */
--success:          #2C5F4A
--warning:          #B45309
--danger:           #9F1239
--chart-1:          #2C5F4A
--chart-2:          #B45309
--chart-3:          #7C5E3A
--chart-4:          #4A6FA5
--chart-5:          #8B7355
```

### Spacing (8px base, **Notion-spacious**)
8 / 16 / 24 / 32 / 48 / 64 / 96. Tile padding 32. Section gutter 64. Page gutter 96 (yes, ninety-six). The whitespace IS the design.

### Radius
12 on tiles, 8 on inputs, 4 on inline chips, 0 on table cells (tables are bare). No pills — chips are slightly-rounded rectangles.

### Shadow
None on tiles (Notion-flat). One shadow scale, used only on the drilldown drawer: `0 1px 2px #1F1B1608, 0 12px 32px #1F1B1612`.

### Component patterns (structurally distinctive)
- **KPI tile.** *Vertical, prose-leading.* No card chrome at all — just whitespace separating it from neighbors. Layout: 12px uppercase warm-taupe label · 44px display KPI hero (humanist sans) · a one-sentence prose subline ("up from 38 yesterday, mostly Atlanta lanes") in 14/24 body. Delta is **inline in the prose**, not a chip. Sparklines absent at the tile level — they live one level down in the section chart.
- **Table row.** 44px tall (generous). Borderless rows; only a 1px `--border` separator between rows. First column is a small carrier-avatar circle (initials, warm taupe ring). MC#, name, lane each get their own visual weight. CHS rendered as a horizontal *typographic* bar: `72 / 100` with a thin 2px underline whose width = score%. No status dots — status is a text chip in the rightmost column.
- **Ticker.** *Reading-pane style.* A vertical column under a "Live activity" heading. Each entry is a 2-line block: timestamp + carrier in 13px muted, then a one-sentence summary in 14/22 body ("Carrier MC-453221 booked Atlanta → Dallas at $2,840."). Reads like a feed of notes, not a console.
- **Button.** 36px tall, 16px horizontal padding. Default: white surface, 1px `--border`, 14px medium body. Primary: solid `--primary` (deep green) with `--primary-fg`. Underlined-text variant for tertiary ("View all calls →"). Hover: 4px shift in border darkness.
- **Drilldown panel.** Full-width modal-page (Notion peek-style), max 880px, centered, generous 64px outer margin. Has its own H1, sub-prose, then sectioned content with anchor links in the right margin.

### Motion
Functional and slow-by-design. 240–320ms `ease-in-out`. Drilldown opens with a 280ms fade + 8px upward slide. Hover transitions are subtle background-color only (180ms). Skeletons are warm-taupe blocks with NO shimmer (Notion uses static placeholders).

### Information hierarchy
**Content-first.** Headings, prose subtitles, then numbers embedded in sentences. KPIs are framed; they don't dominate.

### Grid
Asymmetric, single-reading-column-feel. Max content width 1080. KPI strip: 4 tiles in a row but with internal whitespace doing the dividing, not borders. Side-rail navigation is collapsible to icons.

### Why this fits a freight-broker ops desk
The owner-broker reads this dashboard like a daily ledger / journal of operations — close to how brokers historically used paper bill-of-lading books. Prose context ("mostly Atlanta lanes") teaches a less-technical owner WHY the number moved, not just THAT it did. Stripe Atlas's warmth keeps a financial document from feeling sterile.

### Diff vs the others
- **Density:** loosest of the four (Notion-spacious, 32px tile padding).
- **Color:** only light theme; warm taupe + ledger green (not blue-gray).
- **Hierarchy:** prose-led; KPI numbers are in sentences, not isolated cards.
- **Typography:** uses a humanist display sans + reading-size 14/24 body — Theme 1 uses 13/20.
- **Tables:** borderless rows with typographic CHS bar, not a `[██░░]` blocks.

---

## Theme 3 — "Freight Terminal" (Vercel × Apple Developer, dark, metric-first)

**Inspiration.** Vercel's dashboard precision (sharp corners, dense numerics, mono-everywhere for measurements) crossed with Apple Developer's Pro-tools polish (Inter-style neutral chrome, subtle elevation, the feeling that this is *the instrument*). Where Theme 1 leads with status, Theme 3 leads with **the number** — large, mono-tabular, precise to two decimals where it matters. A traffic-management terminal aesthetic.

### Typography
- **Family stack.** UI: `"Geist Variable", "Geist", "Inter"` (Vercel's chosen geometric grotesque). **All numerics:** `"Geist Mono Variable"` — *every* number on screen is mono-tabular (KPIs, table cells, axis labels, deltas).
- **Scale.** 11/16 axis-label, 12/18 caption, 13/20 body, 14/22 body-lg, 18/26 section-title, 24/30 page-title, 36/40 KPI hero, 56/60 hero-XL (used on Overview headline KPI).
- **Weights.** 400 body · 500 emphasis · 600 KPI hero. **No 700.** Mono is always 500.
- **Letter-spacing.** -0.011em on KPI hero (Vercel signature). +0.04em on uppercase 11px labels. Otherwise 0.

### Color tokens (deep, near-pure-black, cool)
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

### Spacing (4px base, **medium**)
4 / 8 / 12 / 16 / 24 / 32 / 48. Tile padding 20. Table row 32. Section gutter 32. Page gutter 32.

### Radius
**8 on all surfaces, 4 on inputs, 0 on table cells.** Mid-sharp. Pills are 6px radius rectangles, not 999 — this is a Vercel-specific signature (chiclets, not pills).

### Shadow
Soft and functional. `--shadow-1: 0 1px 0 #FFFFFF06 inset, 0 0 0 1px var(--border)`. `--shadow-2 (drilldown): 0 24px 48px -12px #00000080`. The 1px inner-top-highlight is the Vercel hallmark — gives surfaces a subtle "lit from above."

### Component patterns (structurally distinctive)
- **KPI tile.** *Hero-numeric-first.* Layout: 36–56px mono-tabular hero number CENTERED-LEFT, dominating. Above: 11px uppercase tracked label (`BOOKED RATE`). Below: a horizontal pair — `+0.42pp` mono delta chip (rectangle, 6px radius, colored bg) and a 36×16 horizontal bar-spark (NOT a line — 12 tiny vertical bars, 2px wide each, 1px gap). No top status bar (Theme 1's signature) — just a 1px subtle border. Tile background is `--surface` with the inner-top highlight.
- **Table row.** 32px tall. **All numeric columns are mono-tabular AND right-aligned** (Vercel logs-table pattern). Status is a tiny 6px-radius rectangle chip (`BOOKED`, `LIVE`, `FLAGGED`) in 11px mono uppercase. CHS is a number only (`72`) — no bar, no dot — relying on the mono alignment to make scanning easy. Hover: `--surface-elevated` + a subtle inner-top highlight slides in.
- **Ticker.** *Logs-style.* Fixed-height (240px) scrolling pane with mono 12px lines: `[12:43:07] MC-453221  BOOKED  Atlanta→Dallas  $2,840  CHS=84`. New lines push down from top. Auto-scroll pauses on hover. Looks like a `kubectl logs -f` stream — appropriate for an ops desk.
- **Button.** 32px tall. Default: `--surface-elevated`, 1px `--border`, 13px 500. Primary: **solid white on near-black** (Vercel's exact pattern), `--primary-fg` text. Hover: lifts via 1px inner-top brighten, no movement. Cmd-K trigger button on top-right shows `⌘K` in mono on the right side of the button.
- **Drilldown panel.** Full-screen modal-overlay (Vercel deployment-detail style), not a side drawer. Tabbed nav inside. Sub-tables use the same mono-tabular pattern. ESC closes; Cmd+. also closes (developer-tooling muscle memory).

### Motion
Functional, fast, deterministic. 120–180ms cubic-bezier(0.4, 0, 0.2, 1). Modal opens with 160ms scale `0.98 → 1` + fade. Charts animate dataIn at 240ms, but ONLY on first load — never on filter change (Vercel rule: no re-animation on data update). Skeletons: faint horizontal shimmer (1.6s loop), only on first paint.

### Information hierarchy
**Metric-first.** The number is the largest thing on the tile. Label is secondary. Status is a compact mono chip, not a colored bar.

### Grid
12-col strict, 24px gutters, 1440 max width. KPI strip: 4 tiles, but the headline KPI (Booked Rate) is a **2-col-wide** tile with 56px hero — asymmetric strip, not equal quarters.

### Why this fits a freight-broker ops desk
A dispatcher staring at a screen for 8 hours benefits from extreme numeric precision and predictability. Mono-tabular alignment means MC numbers and rates never jitter as data updates. The Vercel "logs" ticker maps perfectly onto the call-stream nature of the product — calls ARE log entries. Apple-Developer polish keeps the dense surface from feeling cheap.

### Diff vs the others
- **Numerics:** ALL numbers on screen are mono-tabular (Themes 1, 2, 4 use proportional with `tnum` only for select tables).
- **Hierarchy:** number-first, not status-first (T1) or content-first (T2).
- **Status indicator:** small mono uppercase chiclet, not a dot, bar, or colored pill.
- **Ticker:** kubectl-logs aesthetic with bracketed timestamps — Theme 1's ticker is rows-with-pills, Theme 2's is prose-feed.
- **Primary color:** WHITE (Vercel signature) — none of the others use white as primary.

---

## Theme 4 — "Loadboard Live" (Raycast × Arc Browser, dark, command-first)

**Inspiration.** Raycast's command-palette-flavored polish (rounded corners, micro-interactions everywhere, every action one keystroke away) crossed with Arc Browser's playful motion-heavy aesthetic (cards that feel physical, satisfying transitions, color used as personality not just signal). Where Theme 3 is "instrument," Theme 4 is "delightful tool I want to use." The Cmd-K palette isn't an afterthought — it's the **center of the navigation model**.

### Typography
- **Family stack.** UI: `"SF Pro Text", "Inter Variable", system-ui` (Apple-style humanist tuning, Raycast's choice on macOS). Mono: `"SF Mono", "JetBrains Mono"` 12.5px for IDs only. Headings can use a slight optical-size variation (`font-variation-settings: "opsz" 28`) at 22px+ for a refined display feel.
- **Scale.** 11/16 caption, 13/18 body (Raycast standard — slightly tighter line-height than Theme 1), 14/20 body-lg, 16/22 row-emphasis, 22/28 section-title, 30/36 page-title, 38/42 KPI hero (smaller than T2/T3 — micro-tile philosophy).
- **Weights.** 400 body · 500 row-emphasis · 600 KPI hero · 700 reserved for command-palette heading.
- **Letter-spacing.** 0 throughout (humanist; tracking is *not* a tool here).

### Color tokens (charcoal, with personality color)
```
--bg:               #1A1A1F        /* warmer than T1/T3 — charcoal, not blue-black */
--surface:          #25252C
--surface-elevated: #32323B
--border:           #3A3A45
--border-strong:    #54545F
--fg:               #F4F4F5
--fg-muted:         #A0A0AB
--primary:          #FF6363        /* Raycast red-coral — signature personality color */
--primary-fg:       #FFFFFF
--accent:           #4ECDC4        /* teal — secondary personality */
--success:          #4ADE80
--warning:          #FBBF24
--danger:           #F43F5E
--chart-1:          #FF6363
--chart-2:          #4ECDC4
--chart-3:          #FBBF24
--chart-4:          #A78BFA
--chart-5:          #60A5FA
```

### Spacing (4px base, **very tight Raycast cadence**)
2 / 4 / 8 / 12 / 16 / 24 / 32. Tile padding 14 (yes, 14 — Raycast list-item philosophy). Section gutter 24. Page gutter 24.

### Radius
**12 on tiles, 10 on cards, 8 on inputs, 8 on chips, 999 on icon buttons.** Rounded everywhere — the signature. Even table rows have a 6px radius on hover (rare in dashboards, distinctive here).

### Shadow
Glow + lift hybrid. `--shadow-rest: 0 1px 0 #FFFFFF08 inset, 0 0 0 1px var(--border)`. `--shadow-hover: 0 0 0 1px var(--border-strong), 0 4px 16px #00000040`. **Cmd-K palette has a colored glow:** `0 0 60px #FF636322`. Drilldown: `0 24px 60px #00000060` + a subtle 1px primary-color outline at top.

### Component patterns (structurally distinctive)
- **KPI tile.** *Compact card with personality.* Layout: top-left 18×18 colored icon-square (rounded 6px) with an emoji-style monoline icon (📞 calls, 🚚 bookings, ✅ booked-rate). Right of icon: 11px label. Below the row: 38px KPI hero in row-emphasis weight, with a colored delta `+12.4%` AS A pill-button-shaped chip (rounded 999, colored bg with 12% opacity, colored fg). At the bottom-right corner: a 24×8 "rolling" sparkline that subtly pulses on data update (250ms scale 1.0→1.04→1.0). Tile is 12px radius, soft shadow on hover, lifts 2px on hover.
- **Table row.** 40px tall, 6px radius on hover (gap of 4px between rows shows the rounding clearly). Each row leads with a tiny 24×24 colored avatar-square (rounded 6px) with carrier initials. Status is a soft pill (rounded 999, 11px medium, 8px horizontal padding, colored bg at 14% opacity + colored fg). CHS is a *circular* progress ring (16px diameter, 2px stroke) plus the number — a tiny visual delight. Right-end of row has a `⌘` hint icon that appears on hover ("press ⌘ to open").
- **Ticker.** *Card-stack.* Each entry is its own 12px-radius mini-card (not a row in a list). Cards stack vertically with 4px gap. New cards animate in with a 280ms scale `0.96→1` + fade + 6px slide-down. The newest card has a 1-second subtle outline pulse in `--accent`. Older cards fade their content to 70% opacity.
- **Button.** 32px tall, 12px horizontal padding, 8px radius. Default: `--surface-elevated` with subtle 1px inner-top highlight. Primary: solid `--primary` (coral red), bold-but-friendly. **Every button has a `⌘`-key hint** if it has a keyboard shortcut, rendered as a small mono chiclet on the right (`Open ⌘O`). Hover: 1.5px outline appears + the icon-side micro-rotates 4deg (300ms cubic-bezier with overshoot).
- **Cmd-K palette (signature).** Center-top floating panel, 640px wide, 12px radius, with the colored glow shadow. Search input at top, fuzzy-matched results below as 40px rows. Each row has an icon-square + label + a `⌘N` shortcut on the right. Arrow keys navigate, Enter executes. **This is the primary navigation model** — the left sidebar is collapsed by default; users open the palette to switch tabs, filter dates, jump to a carrier, etc.
- **Drilldown panel.** Center-stage modal, 720px wide, 16px radius, with a satisfying 320ms spring opening (scale 0.94→1, opacity, slight upward shift). Background dims with a backdrop-filter blur(12px). The top of the modal has a colored 4px "tab" indicating the kind of drill (call=coral, carrier=teal, load=amber).

### Motion
**Arc/Raycast-pronounced.** 240–320ms with spring curves (`cubic-bezier(0.34, 1.56, 0.64, 1)` for openings — very slight overshoot). Hover lifts are 2px translateY with shadow growth. Sparklines pulse on data update. Tab change: 240ms slide-and-fade in the direction of the new tab. Skeletons shimmer (1.4s loop). The product *moves* — every interaction has a visible response.

### Information hierarchy
**Command-first.** The Cmd-K palette is the entry point. Tabs are de-emphasized (sidebar collapses to icons). Tiles and rows are designed to be jumped TO from the palette, not browsed.

### Grid
Asymmetric, content-driven. KPI strip is 4 small tiles + 1 large "headline" card on the right (a "today's narrative" card with a paragraph + the day's standout metric). Charts below in a 2/3 + 1/3 split. No 12-col rigidity.

### Why this fits a freight-broker ops desk
Dispatch is keyboard-heavy work. A command-palette-first navigation model lets a power-broker stop reaching for the mouse — `⌘K → "MC-453221" → Enter` opens that carrier's record in two keystrokes. The motion personality keeps a long-shift tool from feeling oppressive; the coral/teal palette gives Acme a brand voice that doesn't require external branding to feel ownable. Raycast users (developers, designers, prosumer ops staff) already know this interaction pattern.

### Diff vs the others
- **Radius:** rounded everywhere (12/10/8/999). Theme 1 is 6 flat. Theme 3 is 8 mid. Theme 4 is the softest by far in dark themes.
- **Motion:** spring curves + visible hover lifts + pulsing sparklines. Themes 1 & 3 are flat-functional; this is the only one with personality motion.
- **Navigation model:** Cmd-K is the primary entry, sidebar is collapsed. Themes 1, 2, 3 use a persistent sidebar.
- **Status chips:** soft pills with 14% opacity bg + colored fg (Raycast pattern). Theme 3 uses sharp mono chiclets; Theme 1 uses dots+bars; Theme 2 uses text chips.
- **Color personality:** coral-red primary + teal accent gives this a brand voice. Theme 1 is corporate blue, Theme 3 is white-on-black, Theme 2 is ledger-green-on-paper.

---

## Cross-theme structural diff matrix

| Axis                      | T1 Dispatch Console      | T2 Bill of Lading       | T3 Freight Terminal     | T4 Loadboard Live        |
| ------------------------- | ------------------------ | ----------------------- | ----------------------- | ------------------------ |
| **Mode**                  | Dark blue-gray           | Light warm-paper        | Dark near-black         | Dark warm-charcoal       |
| **Primary color**         | Restrained blue          | Ledger green            | White                   | Coral red                |
| **Density**               | Tight (16/8)             | Spacious (32/24)        | Medium (20/12)          | Very tight (14/8)        |
| **Radius philosophy**     | 6 everywhere             | 12 tile, 0 table        | 8 surface, 6 chip       | 12/10/8/999 rounded      |
| **Shadow**                | Borders-only, no shadow  | None except drawer      | Inner-top highlight     | Glow + lift hybrid       |
| **Typography**            | Inter grotesque          | Humanist + display sans | Geist + Geist Mono ALL  | SF Pro humanist          |
| **Numerals**              | Inter tabular + mono IDs | Mono only on big KPIs   | Mono EVERYWHERE         | Proportional + mono IDs  |
| **KPI tile structure**    | H-layout, status bar L   | Vertical, prose subline | Hero-num + bar-spark    | Icon-square + ring delta |
| **Status indicator**      | 8px dot + status bar     | Text chip in column     | Mono uppercase chiclet  | Soft pill 14% opacity    |
| **Ticker style**          | Console rows w/ pills    | Prose feed              | kubectl logs mono       | Card-stack springing in  |
| **Button signature**      | Outlined, no shadow      | Underlined tertiary     | White-on-black primary  | Coral + ⌘-hint chiclet   |
| **Drilldown shape**       | Right side-drawer        | Centered doc page       | Full-screen modal       | Center modal w/ spring   |
| **Motion**                | Subtle 150–220ms ease    | Slow 240–320ms ease     | Fast 120–180ms          | Spring 240–320ms         |
| **Hierarchy**             | Status-first             | Content-first           | Metric-first            | Command-first            |
| **Navigation**            | Sidebar persistent       | Sidebar collapsible     | Sidebar persistent      | Cmd-K primary, no sidebar |
| **Grid**                  | 12-col strict            | Asymmetric reading      | 12-col + asym KPI strip | Asymmetric content       |
| **Chart fill**            | Line-only sparks         | None at tile, charts only | Vertical bar-sparks   | Pulsing line-sparks      |
| **CHS rendering**         | `[██████░░] 72` blocks   | Typographic underline   | Number only (mono)      | Circular ring + number   |

---

## Picking guidance for Acme

- **Owner-broker primary user, less technical:** T2 Bill of Lading. Prose context teaches.
- **Heads-down dispatcher, 8-hour shift, mouse-light:** T4 Loadboard Live. Cmd-K + motion delight.
- **Engineer-broker / workflow author who'll demo this to Carlos:** T3 Freight Terminal. Vercel-grade precision reads as "we know what we're doing."
- **Default-safe, opinionated tooling, broadest appeal:** T1 Dispatch Console. Linear's calm scales.

If only one ships: **T1 or T3.** If two: T1 + T2 (covers both audiences). If goal is differentiation in a Carlos demo: **T4** (most distinctive, hardest to mistake for "another dashboard template").
