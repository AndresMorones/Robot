# Dashboard widget integration plan — Telemetry tab

## Tab structure

Navigation is hardcoded in `dashboard/src/components/header.tsx` in a static `NAV` array. Adding the Telemetry tab is a one-line change:

```typescript
{ href: "/dashboard/telemetry", label: "Telemetry" }
```

Plus a new page at `dashboard/src/app/dashboard/telemetry/page.tsx`. Active-state detection in the header is automatic via pathname matching.

Final route hierarchy:

```
/dashboard                  Overview (Tabs: Outcomes, Economics, Operational, Quality)
/dashboard/calls            Calls list
/dashboard/calls/[call_id]  Call detail
/dashboard/carriers         Carrier rollup
/dashboard/carriers/[mc]    Carrier detail
/dashboard/sales            New Bookings
/dashboard/telemetry        ← NEW (Pit-style, CloudWatch-Bedrock pattern)
```

## Widget components — files to add

```
dashboard/src/components/telemetry/
├── voice-agent-widget.tsx     BIG card; RPM + TPM + latency overlay; field/percentile/bucket pickers
├── extract-widget.tsx         Field-pick token chart (input/output/reasoning/cached/uncached)
├── chs-widget.tsx             Same shape as extract; CHS columns
├── telemetry-filters.tsx      Per-page period + auto-refresh + threshold controls
├── telemetry-crosshair.tsx    Shared cursor context provider (CloudWatch sync hover)
└── telemetry-types.ts         Local widget prop types
```

## Reusable primitives identified

Existing components in `dashboard/src/components/`:

| Component | Used for new widgets? |
|---|---|
| `charts/trend-line.tsx` (LineChart wrapper, null-safe) | YES — TPM/latency series base |
| `charts/funnel-chart.tsx` | NO — outcome-specific |
| `charts/distribution-pie.tsx` | NO — categorical only |
| `kpi-card.tsx` | YES — per-widget headline metric |
| `sentiment-badge.tsx` / `chs-badge.tsx` / `outcome-badge.tsx` | NO — out of scope for telemetry |
| `effective-delta-chart.tsx` | YES — pattern reference for hero chart |
| `quality/chs-trend-chart.tsx` | YES — pattern reference for trend overlay |
| `calls-table.tsx` | YES — pattern for any drill-down table inside a widget |
| `live-refresh.tsx` | YES — already wired for SSE; reuse for auto-refresh toggle |

## shadcn dependencies

Confirmed in `dashboard/package.json`:

| Primitive | Status | Use |
|---|---|---|
| `@radix-ui/react-select` | ✅ available | bucket dropdown, period dropdown |
| `@radix-ui/react-tabs` | ✅ available | (not needed for telemetry, present) |
| `@radix-ui/react-tooltip` | ✅ available | hover tooltips on chart points |
| `@radix-ui/react-toggle-group` | ❌ NOT installed | percentile multi-select — hand-roll OR install |
| `@radix-ui/react-dropdown-menu` | ❌ cut per ADR-011 | not needed |
| `@radix-ui/react-popover` | ❌ cut per ADR-011 | not needed |

Recommendation: hand-roll a `<ToggleGroup>` mini-component (~20 lines, reuses Button styles) rather than adding a dep. Stays inside ADR-011's "no new libraries" lock.

## API contract additions

Add to `dashboard/src/lib/api-client.ts`:

```typescript
export async function getTelemetryVoiceAgent(
  filters?: DashboardFilters,
  bucket?: string,
  percentiles?: number[],
): Promise<TelemetryVoiceAgentMetrics>;

export async function getTelemetryExtract(
  filters?: DashboardFilters,
  bucket?: string,
  fields?: string[],
): Promise<TelemetryExtractMetrics>;

export async function getTelemetryChs(
  filters?: DashboardFilters,
  bucket?: string,
  fields?: string[],
): Promise<TelemetryCHSMetrics>;
```

Backend additions in `api/app/routers/`:
- `telemetry.py` (new) — three GET endpoints, all behind `Depends(require_bearer)`:
  - `GET /v1/telemetry/voice-agent`
  - `GET /v1/telemetry/extract`
  - `GET /v1/telemetry/chs`
- Each delegates to functions in `api/app/services/transcript_telemetry.py` (per `docs/design/transcript-telemetry-module.md`).

Add to `dashboard/src/types/api-types.ts`:

```typescript
export type TelemetryVoiceAgentMetrics = {
  rpm_series: Array<{ t: string; v: number }>;
  tpm_series: Array<{ t: string; v: number }>;
  latency_series: Array<{ t: string; p50?: number; p70?: number; p90?: number; p99?: number }>;
  latency_percentiles: { p50?: number; p70?: number; p90?: number; p99?: number };
  totals: { calls: number; agent_tokens: number; tool_tokens: number };
};

export type TelemetryExtractMetrics = {
  rpm_series: Array<{ t: string; v: number }>;
  tpm_series: Array<{ t: string; v: number }>;
  field_series: Record<string, Array<{ t: string; v: number }>>;
  totals: Record<string, number>;
};

export type TelemetryCHSMetrics = TelemetryExtractMetrics;
```

## Data flow

1. Server-side `app/dashboard/telemetry/page.tsx` reads `searchParams` → calls `useDashboardFilters()`-derived from/to dates.
2. Parallel `Promise.all([getTelemetryVoiceAgent, getTelemetryExtract, getTelemetryChs])` per render.
3. Each widget gets initial data as a server prop; client-side state owns picker values (bucket, percentiles, fields).
4. Picker change → refetch via `router.refresh()` (cheap, leverages 5-min ISR) OR client-side `fetch` to the same endpoint with new query params (faster, no full-page rerender).
5. Crosshair sync: a `<TelemetryCrosshairProvider>` at page root holds `{hoverTimestamp: string | null}` in context; each chart calls `useTelemetryCrosshair()` to read + write.
6. Auto-refresh: reuse `<LiveRefresh />`; expose a toggle in telemetry-filters.tsx that maps to its existing interval prop.

## Theme switch readiness

All design tokens centralized in `dashboard/src/app/globals.css` at `:root` and `.dark` levels. Pit telemetry palette swap = adding a new class block:

```css
.pit-surface {
  --background: 0 0% 4%;
  --foreground: 0 0% 90%;
  --card: 0 0% 6%;
  --primary: 41 100% 50%;     /* amber, Pit signature */
  --chart-1: 41 100% 50%;     /* amber */
  --chart-2: 142 100% 41%;    /* green */
  --chart-3: 0 100% 61%;      /* red */
  --chart-4: 200 70% 64%;     /* cyan */
}
```

Apply `.pit-surface` class to the `<main>` element on the Telemetry page only — leaves the rest of the app on Freight Terminal tokens. Zero component-level changes.

## Build order

1. Backend: write `transcript_telemetry.py` per its design doc + `api/app/routers/telemetry.py` with the 3 endpoints + tests.
2. Type definitions in `api-types.ts`.
3. API client functions in `api-client.ts`.
4. `<TelemetryCrosshairProvider>` + the hand-rolled ToggleGroup primitive.
5. Voice Agent widget (biggest, most complex; sets the pattern).
6. Extract widget + CHS widget (clones of each other with different column prefixes).
7. Telemetry page composition + nav update.
8. `.pit-surface` palette class in `globals.css`.
9. Auto-refresh toggle wiring.
10. Threshold annotations + alarm bands (Tier-2; defer if time-pressed).

## Integration checklist

- [ ] Type definitions added (`api-types.ts`)
- [ ] API client fetchers added (`api-client.ts`)
- [ ] Backend `transcript_telemetry.py` shipped + tests pass
- [ ] Backend `routers/telemetry.py` shipped + tests pass
- [ ] Voice Agent widget renders with mock data
- [ ] Extract widget renders
- [ ] CHS widget renders
- [ ] Telemetry page composes widgets in 2-col grid
- [ ] Header NAV updated
- [ ] `.pit-surface` palette class added
- [ ] Crosshair sync working across all 3 widgets
- [ ] Auto-refresh toggle wired
- [ ] FAANG QC prompt run against the changes (per `project_dashboard_qc_gate_faang.md`)

## Key takeaways

- No blockers. All primitives + theme infrastructure already in place.
- The hand-rolled ToggleGroup is the only new code primitive; everything else is composition.
- Pit palette swap is a one-class change scoped to the Telemetry page.
- The transcript_telemetry.py module (per its own design doc) is the load-bearing piece — write that first.
