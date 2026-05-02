# Dashboard UI Direction Exploration — Ops-Tooling Lens

**Purpose:** four distinct directions for the Acme Logistics carrier-ops dashboard, framed through ops-tooling / SaaS-app patterns (Salesforce console, Datadog, Linear, ServiceNow, Vercel, Stripe, GitHub Actions). Each is implementable in Next.js 15 + Tailwind 4 + shadcn/ui + Recharts without reintroducing ADR-011-banned dependencies.

**Shared assumptions across all four:**
- Left-rail nav (icon + label, collapsible). 4 destinations: Overview / Calls / Carriers / New Bookings.
- Sticky header with global date filter (preset chips: 7d / 30d / MTD / Custom) + workspace switcher placeholder.
- Every metric tile shows `value vs target` with delta arrow. Targets stored in a single `targets.ts` constants file for now.
- Call-detail drilldown view (transcript player + KPI strip + outcome pills + future `notes` field) is preserved verbatim across all four — it's the bedrock interaction. Only the *path to it* differs.
- Recharts only for charts. shadcn primitives only (Card, Button, Badge, Tabs, Sheet, Dialog, Command, Table, ScrollArea, Tooltip).
- HR-pending integrations (`notes` field, real-time event push, audio playback URL) shown as TODO placeholder slots, not silent absences, in directions A and B.

---

## Direction A — "Console + Side Detail" (Salesforce Service Console)

The default ops-staff experience is a persistent two-pane: list on the left, selected entity detail on the right. You never lose your place in the queue while drilling.

### Layout

```
+--------------------------------------------------------------------------------+
|  HEADER  [Acme logo] [date: 7d|30d|MTD|Custom]  [refresh] [user]               |
+----------+---------------------------------------------------------------------+
|          |  CANVAS                                                             |
|  L-RAIL  |  +---------------------------+----------------------------------+  |
|  Overview|  |  LIST PANE (40%)          |  DETAIL PANE (60%, sticky)        |  |
|  Calls   |  |  filter chips             |  selected call header             |  |
|  Carriers|  |  virtualized rows         |  KPI strip (CHS / outcome / dur)  |  |
|  Bookings|  |  status pills             |  transcript player                |  |
|          |  |  hover → quick peek       |  notes [TODO HR-pending]          |  |
|          |  |                           |  related: carrier card, load card |  |
|          |  +---------------------------+----------------------------------+  |
+----------+---------------------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **Calls tab** = virtualized list (`react-window` is fine, vanilla; or shadcn Table + `IntersectionObserver`). Click row → right pane updates in place; no route change. URL syncs to `?call=<id>` via `useSearchParams`.
2. **Status pill column** on every row: `call_outcome` (booked/declined/no-fit/escalated) + `sentiment` + `chs` rendered as 3 stacked Badges in a single cell.
3. **Detail pane is sticky** at viewport height; transcript player is the dominant block; KPI strip is a 4-tile row above it.
4. **Notes block** sits below transcript with `<div data-todo="hr-notes-field">Notes pending HR Extract integration</div>` placeholder card — visually present, marked.
5. **Overview tab** = same 2-pane shell, but list = "Flagged calls today" feed and detail = aggregate KPI dashboard (the only tab where detail pane is non-entity).
6. **Carriers tab** = list of MCs sorted by call volume; detail = carrier profile (calls history, booking ratio, CHS distribution mini-bar).
7. **New Bookings tab** = list of recent bookings (newest first); detail = load card + linked call + agreed-rate-vs-listed delta + "open call" jump button.

### How each tab renders

- **Overview:** flagged-calls list (left) + 6 KPI tiles + 2 Recharts in detail pane (calls-over-time area, revenue bar). Date filter applies globally.
- **Calls:** full 16-col virtualized table (left) + drilldown (right). Expand-row toggle bumps list pane to 100% width temporarily.
- **Carriers:** MC list with FMCSA-status pill + call-count + booking-rate. Detail = carrier card.
- **New Bookings:** booking row list + detail pane with load + call link.

### Rationale

Freight-broker ops staff triage flagged calls in queues — they don't want to lose context every time they click. A persistent detail pane is the dominant UX in Salesforce/ServiceNow because case-workers are doing one of: scan list → drill → return to list. Two-pane keeps that loop tight. The same shell handles carriers and bookings, so muscle memory transfers across tabs.

### Sacrifices vs current

- Less canvas for big charts; Overview KPIs feel cramped on 13" laptops.
- Detail pane forces a horizontal commitment — bad for users who want full-width transcript reading.
- Two-pane is overkill for first-time visitors; landing feels "busy" before they pick a row.

---

## Direction B — "Activity Feed First" (Linear / Datadog / GitHub Actions)

The dashboard is a live event stream. KPIs are sidebar context; the canvas is "what just happened."

### Layout

```
+--------------------------------------------------------------------------------+
|  HEADER  [Acme] [date]  [LIVE indicator pulsing]  [user]                       |
+----------+--------------------------------------------------+------------------+
|  L-RAIL  |  CANVAS — ACTIVITY STREAM (70%)                  | KPI RAIL (30%)   |
|  Overview|  +-----------------------------------------------+ Calls today: 47  |
|  Calls   |  | 14:32  CALL booked   MC 12345  $2,400  CHS 88 | Bookings: 12     |
|  Carriers|  | 14:28  CALL flagged  MC 67890  CHS 42         | Booked rate: 25% |
|  Bookings|  | 14:22  CALL no-fit   MC 11111  CHS 71         | + revenue chart  |
|          |  | 14:18  BOOKING       call→load TX-LA          | + sentiment ring |
|          |  | ...                                            | flagged: 3 ▼     |
|          |  +-----------------------------------------------+                  |
+----------+--------------------------------------------------+------------------+
```

### 7 widget-pattern decisions

1. **Activity stream** = reverse-chrono feed of typed events (call_completed, call_flagged, booking_created, fmcsa_failure). Each row is a clickable card → opens detail Sheet (shadcn Sheet from right edge, not full route change).
2. **Live indicator** in header pulses green when SSE connected (TODO marker for HR webhook integration). When disconnected, badge shows "polling 30s" so ops know freshness.
3. **KPI rail** is 30% right column — 4 metric tiles stacked + 1 Recharts pie (sentiment) + 1 sparkline (calls-over-time). Always visible, never scrolls off.
4. **Filter pills above stream**: `All / Booked / Flagged / FMCSA-failed / Low-CHS`. Drives client-side filter on the in-memory stream.
5. **Detail Sheet** (not route) = same drilldown view, slides in from right, dismissible with Esc. Preserves stream scroll position. Notes block included with `[TODO HR-notes-field]` marker.
6. **Carriers tab** keeps the feed model — stream of "MC events" (new MC seen, MC FMCSA-failed, repeat caller). Detail Sheet = carrier card.
7. **Overview tab** is the stream itself — there is no separate Overview canvas; KPI rail *is* the overview.

### How each tab renders

- **Overview:** 100% the same stream + KPI rail (the default landing).
- **Calls:** stream filtered to `event.type=call_*`. Toggle: "Show as table" reveals 16-col grid view as alt mode.
- **Carriers:** stream of carrier-events; KPI rail swaps to carrier metrics (unique MCs, repeat-rate, FMCSA-pass %).
- **New Bookings:** stream filtered to `event.type=booking_*`; KPI rail swaps to booking metrics (avg agreed vs listed, $ booked today).

### Rationale

Voice-agent ops is fundamentally a real-time discipline — calls land continuously, and the question ops most often asks is "what just happened, and is anything going wrong right now?" Datadog/Linear/GitHub-Actions answer that with a feed-first model. KPIs become ambient context rather than the main subject. The feed also makes anomalies (3 FMCSA failures in 5 min) instantly visible without writing alert rules.

### Sacrifices vs current

- Aggregate analysis (week-over-week trends, distributions) is awkward — feeds bias toward the most recent.
- Heavy real-time dependence; without HR webhook landing, the "LIVE" promise is hollow and reverts to 30s polling.
- Less natural home for static tables (the full 16-col calls table feels bolted on).

---

## Direction C — "Command-Palette + Inspector" (Linear / Vercel / Raycast)

Cmd-K is the primary navigation surface. The canvas is minimal — a single inspector pane responding to whatever entity the operator just summoned. Power-user-first.

### Layout

```
+--------------------------------------------------------------------------------+
|  HEADER  [Acme]   [⌘K  Search calls, MCs, loads, bookings...]   [date]  [user] |
+----------+---------------------------------------------------------------------+
|          |  CANVAS — INSPECTOR (single pane, full width)                       |
|  L-RAIL  |  current entity: CALL abc-123                                       |
|  Overview|                                                                     |
|  Calls   |  [KPI strip]  [Outcome pills]                                       |
|  Carriers|  [Transcript player — full width]                                   |
|  Bookings|  [Notes section — TODO HR-pending]                                  |
|          |  [Related entities: carrier card, load card, booking card]          |
|          |                                                                     |
|          |  Footer: keyboard hints  ⌘K search · ⌘[ back · ⌘E expand            |
+----------+---------------------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **Cmd-K palette** (shadcn Command) is the entry point — fuzzy-search across calls (by MC, by transcript snippet), carriers, loads, bookings. Recent searches pinned at top.
2. **Inspector is the only canvas** — no list views by default. You navigate by searching, not scrolling.
3. **Breadcrumb-style entity history** at top of inspector: "Recent: call-abc, MC-12345, load-xyz" → click to time-travel back.
4. **Tab routes degrade gracefully** to "list mode" when reached without a selection: Calls tab without a selected call shows a recent-50 list; selecting one collapses back to inspector.
5. **Keyboard-first**: `j/k` to navigate within list mode, `o` to open, `Esc` to back out, `⌘E` to expand any widget to full screen.
6. **Inspector layout for a Call entity** = KPI strip (5 tiles) + transcript player (60% width) + side column with carrier card, load card, notes block (with TODO for HR `notes` field — explicitly visible).
7. **Overview tab** = single dense "today summary" inspector card with 8 KPIs + 2 sparklines + flagged-calls quick-list. Cmd-K from here is the action prompt.

### How each tab renders

- **Overview:** single inspector card, "Today at Acme" — 8 KPIs, sparklines, top-5 flagged calls clickable.
- **Calls:** inspector shows last-selected call; if none, shows list mode (recent 50 with j/k nav).
- **Carriers:** inspector for last-selected MC; list mode = top-30 MCs by volume.
- **New Bookings:** inspector for last-selected booking; list mode = recent 20.

### Rationale

Power-user ops staff (the persona that shipped Linear) navigate by search and keyboard, not click-trees. For a brokerage with hundreds of MCs and thousands of calls, fuzzy search is the fastest path from "Carlos called, what's going on" to the answer. The inspector pattern means every entity gets the same full-canvas attention, so transcript review is excellent. Lower visual density = lower cognitive load for long shifts.

### Sacrifices vs current

- Discoverability is poor — first-time users won't know to press Cmd-K.
- Aggregate dashboards (multi-chart Overview) become cramped; this direction inherently de-emphasizes "scan many things at once."
- Mobile / tablet UX collapses — palette + keyboard are desktop-first patterns.

---

## Direction D — "Status-Pill Ops Grid" (ServiceNow / Stripe Radar / GitHub Actions runs grid)

Every entity is a row with a colored status pill. The default canvas is a dense grid; the operator's job is to scan pills, filter, and act in bulk.

### Layout

```
+--------------------------------------------------------------------------------+
|  HEADER  [Acme] [date]   [bulk actions ▼ disabled]   [user]                    |
+----------+---------------------------------------------------------------------+
|          |  CANVAS — GRID                                                      |
|  L-RAIL  |  [filter bar: outcome | sentiment | CHS range | FMCSA | MC search]  |
|  Overview|  +-----------------------------------------------------------------+|
|  Calls   |  | ☐ time     MC      outcome    sent.   CHS   dur   FMCSA  rev   ||
|  Carriers|  | ☐ 14:32   12345   [BOOKED]   [POS]   88   3:21   ✓     $2400  ||
|  Bookings|  | ☐ 14:28   67890   [FLAG]     [NEG]   42   1:45   ✗     —      ||
|          |  | ☐ 14:22   11111   [NO-FIT]   [NEU]   71   2:10   ✓     —      ||
|          |  | ...                                                             ||
|          |  +-----------------------------------------------------------------+|
|          |  selected: 0   |   click row → drilldown drawer                     |
+----------+---------------------------------------------------------------------+
```

### 7 widget-pattern decisions

1. **Default Calls view** is full 16-col table with status pills as the dominant visual. Sticky header, sortable columns, virtualized body. Expand-row toggle inflates a row inline to show transcript snippet + KPI ribbon (without leaving the grid).
2. **Status pill taxonomy** is consistent across grids: outcome → 4 colors, sentiment → 3, CHS → green ≥80 / amber 50–79 / red <50, FMCSA → check/x. One legend shipped in Tooltip.
3. **Bulk-select column** (checkbox) reserved for future bulk actions (export, mark reviewed). MVP shows count but action menu disabled with TODO marker.
4. **Filter bar above grid** drives URL state (`?outcome=flagged&chs=lt50`). Multi-filter chips render under the bar so operator sees what's applied.
5. **Click row → drilldown opens as Dialog (modal)** — full-screen-ish on smaller displays, side-Sheet on wider. Different from A/B (no persistent split-pane) — the grid is canonical, drilldown is interruption. Dialog includes notes section (no TODO marker in this direction; D treats `notes` as silent-graceful-degrade — explicitly noted as the difference from A/B).
6. **Overview tab** is itself a "metrics grid" — 12 KPI tiles in a 4×3 grid with status-pill-style coloring (target met / near / missed). Below: 2 Recharts.
7. **Carriers + Bookings** = same grid pattern with different columns. Bulk-select carries through. Visual consistency is the whole point.

### How each tab renders

- **Overview:** 4×3 KPI tile grid (each tile is itself a status-pill metric — green/amber/red vs target) + revenue Recharts area + sentiment ring.
- **Calls:** 16-col grid, full pill density, primary view.
- **Carriers:** grid with MC, calls-30d, booking-rate, FMCSA-status pill, CHS-avg pill, repeat-caller flag.
- **New Bookings:** grid with booking-time, MC, lane (origin→dest), agreed-rate, listed-rate, delta pill (green if ≤0, amber if 0–10%, red if >10%).

### Rationale

Brokerage ops looks a lot like ticket queue ops — operator scans many rows for outliers (red pills) and acts. ServiceNow built an empire on this. Status pills make outliers preattentive, no chart needed. Bulk-select reserves room for future workflows (mark-reviewed, escalate, export-for-coaching) without a redesign. Familiar pattern = low onboarding cost for ops hires from other industries.

### Sacrifices vs current

- Aesthetically dense and busy; can feel "old-school enterprise" rather than modern SaaS.
- Real-time signaling is weaker than direction B — no feed primitive, just rows that change.
- Dialog/Modal drilldown breaks the "stay-in-context" principle that A and C preserve; you lose the grid's scroll position when the dialog dismisses unless we manually preserve it.

---

## Cross-direction comparison

| Aspect                  | A: Console+Detail        | B: Activity Feed         | C: Cmd-K Inspector       | D: Status-Pill Grid       |
|-------------------------|--------------------------|--------------------------|--------------------------|---------------------------|
| Primary nav primitive   | List rows                | Event stream             | Cmd-K palette            | Filter + grid             |
| Drilldown placement     | Persistent right pane    | Right-edge Sheet         | Full-canvas inspector    | Modal Dialog              |
| Real-time emphasis      | Medium (list refresh)    | High (LIVE indicator)    | Low (pull-on-search)     | Medium (row-level)        |
| Aggregate friendly      | Medium                   | Low                      | Medium                   | High (KPI grid)           |
| Mobile/tablet friendly  | Medium                   | Medium                   | Low                      | Low                       |
| Onboarding cost         | Low                      | Low                      | High                     | Low                       |
| HR-`notes` placeholder  | Explicit TODO            | Explicit TODO            | Explicit TODO            | Silent / graceful         |

---

## Recommendation framing (not a decision)

If the deliverable demo prioritizes ops-staff-watching-live-calls vibe, **B**.
If it prioritizes deep call review and case-worker triage, **A**.
If it prioritizes power-user productivity narrative, **C**.
If it prioritizes "this looks like serious enterprise software," **D**.

Hybrid worth considering: A's persistent split for Calls tab + D's KPI-grid for Overview + B's LIVE indicator in the header. The directions aren't mutually exclusive at the tab level — each tab can pick its own framing if we accept some inconsistency.
