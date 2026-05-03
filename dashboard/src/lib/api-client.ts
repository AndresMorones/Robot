import "server-only";

import { apiBaseUrl, apiBearerToken } from "@/lib/config";
import type {
  AvailableLoadsResponse,
  CallRecord,
  CallTimelineResponse,
  CarrierProfile,
  CarrierRollupMetrics,
  EconomicsMetrics,
  EffectiveDeltaSeries,
  FunnelMetrics,
  LoadFull,
  ObservabilityMetrics,
  OperationalMetrics,
  QualityMetrics,
  RecentBookingsResponse,
  TelemetryAggregate,
} from "@/types/api-types";

// Server-only fetch helper. The Bearer token is read from process.env via
// `lib/config`; this module imports `server-only` so any accidental import
// from a Client Component fails the build instead of leaking the secret.
//
// Each call uses Next.js fetch revalidation so dashboard pages can re-render
// at most every REVALIDATE_S seconds without a hard reload. Pages that want
// fresh-on-demand can pass { cache: "no-store" } via callers. Aligned with
// the 5-min page-level ISR fallback (ADR-009) — push (webhook+SSE) drives
// real-time freshness, this is the safety net.
const REVALIDATE_S = 300;

class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string, message?: string) {
    super(message ?? `API ${status}: ${body.slice(0, 200)}`);
    this.status = status;
    this.body = body;
  }
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { revalidate?: number | false },
): Promise<T> {
  const url = `${apiBaseUrl}${path}`;
  const headers = new Headers(init?.headers);
  headers.set("accept", "application/json");
  if (apiBearerToken) {
    headers.set("authorization", `Bearer ${apiBearerToken}`);
  }
  const next =
    init?.cache === "no-store"
      ? undefined
      : { revalidate: init?.revalidate ?? REVALIDATE_S };
  const res = await fetch(url, {
    ...init,
    headers,
    next,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text);
  }
  return (await res.json()) as T;
}

// ---------- /v1/dashboard/* surface ----------

// Global date filter passed by every server-rendered dashboard page. `from`
// and `to` are forwarded as ISO-8601 query params; absent values omit the
// param entirely (FastAPI then defaults to "no filter" → full table scan).
export type DashboardFilters = { from?: Date; to?: Date };

/**
 * Parse YYYY-MM-DD URL params into inclusive UTC day bounds.
 *
 * Why this exists: the picker writes local-tz dates as "YYYY-MM-DD" strings.
 * Naively `new Date("YYYY-MM-DD")` parses as UTC midnight at the START of the
 * day — so a `to=2026-04-30` bound becomes 2026-04-30T00:00:00Z, which excludes
 * every call placed during 2026-04-30 itself. Result: clicking any preset for
 * a window ending "today" returns zero rows.
 *
 * Fix: from = start of UTC day (00:00:00.000Z), to = end of UTC day
 * (23:59:59.999Z). Keeps the URL contract (`YYYY-MM-DD` strings) intact while
 * sending inclusive bounds to FastAPI's `created_at BETWEEN ...` clause.
 *
 * Also tolerates the older full ISO-8601 datetime shape — if the param already
 * carries time + offset we round-trip it as-is.
 */
// When the URL carries no explicit ?from/?to, every page defaults to the
// last DEFAULT_WINDOW_DAYS days. Lock-in 2026-05-02 — keeps the dashboard
// from rendering a year of data on first load and forces granularity to
// stay daily until the user widens the window themselves.
const DEFAULT_WINDOW_DAYS = 7;

export function parseFilterParams(sp: {
  from?: string;
  to?: string;
}): DashboardFilters {
  const fromExplicit = parseStartBound(sp.from);
  const toExplicit = parseEndBound(sp.to);
  // If neither bound is provided, fall back to the last 7 days. If only one
  // is provided, leave the other undefined so the user's intent (open-ended
  // half-window) is preserved.
  if (fromExplicit === undefined && toExplicit === undefined) {
    const now = new Date();
    const from = new Date(now.getTime() - DEFAULT_WINDOW_DAYS * 24 * 60 * 60 * 1000);
    return { from, to: now };
  }
  return { from: fromExplicit, to: toExplicit };
}

function parseStartBound(s: string | undefined): Date | undefined {
  if (!s) return undefined;
  const dateOnly = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateOnly) {
    return new Date(
      Date.UTC(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]), 0, 0, 0, 0),
    );
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? undefined : d;
}

function parseEndBound(s: string | undefined): Date | undefined {
  if (!s) return undefined;
  const dateOnly = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (dateOnly) {
    return new Date(
      Date.UTC(
        Number(dateOnly[1]),
        Number(dateOnly[2]) - 1,
        Number(dateOnly[3]),
        23,
        59,
        59,
        999,
      ),
    );
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? undefined : d;
}

function withFilters(path: string, filters?: DashboardFilters): string {
  if (!filters?.from && !filters?.to) return path;
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from.toISOString());
  if (filters.to) params.set("to", filters.to.toISOString());
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}${params.toString()}`;
}

// Dashboard fetchers all use `revalidate: 30` so the global date picker
// reflects in every widget within 30 seconds — the underlying Next.js Data
// Cache otherwise reuses a 300s-cached payload across filter changes and
// makes filtered dashboards look frozen.
const DASHBOARD_REVALIDATE = 30;

export async function getFunnel(filters?: DashboardFilters): Promise<FunnelMetrics> {
  return apiFetch<FunnelMetrics>(withFilters("/v1/dashboard/funnel", filters), {
    revalidate: DASHBOARD_REVALIDATE,
  });
}

export async function getEconomics(filters?: DashboardFilters): Promise<EconomicsMetrics> {
  return apiFetch<EconomicsMetrics>(withFilters("/v1/dashboard/economics", filters), {
    revalidate: DASHBOARD_REVALIDATE,
  });
}

export async function getOperational(filters?: DashboardFilters): Promise<OperationalMetrics> {
  return apiFetch<OperationalMetrics>(withFilters("/v1/dashboard/operational", filters), {
    revalidate: DASHBOARD_REVALIDATE,
  });
}

export async function getQuality(filters?: DashboardFilters): Promise<QualityMetrics> {
  return apiFetch<QualityMetrics>(withFilters("/v1/dashboard/quality", filters), {
    revalidate: DASHBOARD_REVALIDATE,
  });
}

export async function getObservability(filters?: DashboardFilters): Promise<ObservabilityMetrics> {
  return apiFetch<ObservabilityMetrics>(
    withFilters("/v1/dashboard/observability", filters),
    { revalidate: DASHBOARD_REVALIDATE },
  );
}

export async function getCarriers(filters?: DashboardFilters): Promise<CarrierRollupMetrics> {
  return apiFetch<CarrierRollupMetrics>(withFilters("/v1/dashboard/carriers", filters), {
    revalidate: DASHBOARD_REVALIDATE,
  });
}

// Hero chart payload — daily mean of (apply_rate - loadboard_rate) over the
// active filter window. Falls back to a trailing-30-day window when no filter
// is set. See `app/services/dashboard_aggregations.py::effective_delta_series`.
export async function getEffectiveDelta(
  filters?: DashboardFilters,
): Promise<EffectiveDeltaSeries> {
  return apiFetch<EffectiveDeltaSeries>(
    withFilters("/v1/dashboard/effective-delta", filters),
    { revalidate: DASHBOARD_REVALIDATE },
  );
}

// Per-carrier rollup. Returns null on 404 (no calls for this MC) so callers
// can render an empty-state card without try/catch noise.
export async function getCarrierProfile(
  mc: string,
): Promise<CarrierProfile | null> {
  try {
    return await apiFetch<CarrierProfile>(
      `/v1/carriers/${encodeURIComponent(mc)}`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

// Twin REST returns numeric columns as JSON strings ("100" not 100). Coerce
// known numeric fields at the boundary so every consumer sees true numbers
// and `case_health_score >= 70` type-checks. See
// `reference_twin_returns_numerics_as_strings.md` for the root-cause memory.
function normalizeCallRow<T extends CallRecord>(row: T): T {
  const raw = row.case_health_score as unknown;
  if (raw === null || raw === undefined || raw === "") {
    return { ...row, case_health_score: null };
  }
  const n = Number(raw);
  return { ...row, case_health_score: Number.isNaN(n) ? null : n };
}

// ---------- calls list (best-effort) ----------
//
// The FastAPI service does not currently expose a JSON `GET /v1/calls` route
// (the only exposed call endpoint is the legacy 410-Gone POST). We attempt the
// most likely candidates and fall back to an empty list so the UI degrades
// gracefully. Document which path returned data via the `source` field.
//
// Data-need gap: the dashboard wants per-call rows for /dashboard/calls and
// /dashboard/carriers/[mc]; recommend adding a minimal `GET /v1/calls`
// endpoint on FastAPI that wraps `app.services.calls_store.list_calls`.
export type CallsListResult = {
  calls: CallRecord[];
  source: "v1-calls" | "v1-dashboard-calls" | "fallback-empty";
  error?: string;
};

export async function getCalls(
  limit = 100,
  filters?: DashboardFilters,
): Promise<CallsListResult> {
  const candidates = [
    `/v1/calls?limit=${limit}`,
    `/v1/dashboard/calls?limit=${limit}`,
  ] as const;
  for (const base of candidates) {
    const path = withFilters(base, filters);
    try {
      // `cache: "no-store"` keeps the calls list fresh on every visit. The
      // page that renders it (`/dashboard/calls`) is `force-dynamic`, so an
      // ISR-cached fetch here would silently undo that and re-introduce the
      // empty-on-soft-nav bug.
      const data = await apiFetch<CallRecord[] | { calls?: CallRecord[] }>(path, {
        cache: "no-store",
      });
      const raw = Array.isArray(data) ? data : (data?.calls ?? []);
      const calls = raw.map(normalizeCallRow);
      return {
        calls,
        source: base.startsWith("/v1/calls") ? "v1-calls" : "v1-dashboard-calls",
      };
    } catch {
      // try next candidate
    }
  }
  return { calls: [], source: "fallback-empty" };
}

// Per-call detail. The FastAPI endpoint returns a `{call, bookings}` wrapper;
// we flatten so callers can read `CallRecord` fields directly while still
// exposing the joined bookings under `.bookings`. `include_transcript=true`
// is opt-in defense-in-depth on the backend — we ask for it here because the
// detail page is the only surface that renders transcripts.
export type CallBookingRow = {
  id?: number | null;
  created_at?: string | null;
  call_id?: string | null;
  mc_number?: string | null;
  load_id?: string | null;
  apply_rate?: number | null;
  load?: LoadFull | null;
};

export type CallDetailRecord = CallRecord & {
  bookings?: CallBookingRow[];
};

export async function getCallById(
  callId: string,
): Promise<CallDetailRecord | null> {
  try {
    const res = await apiFetch<{
      call: CallRecord;
      bookings: CallBookingRow[];
    }>(`/v1/calls/${encodeURIComponent(callId)}?include_transcript=true`);
    if (!res || !res.call) return null;
    return { ...normalizeCallRow(res.call), bookings: res.bookings ?? [] };
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    return null;
  }
}

// Per-call conversation timeline. Backend in `api/app/routers/calls.py`. The
// payload is transcript-derived and immutable post-call, so we cache for 60s
// (vs 30s on live aggregates). Returns null on 404 so the drilldown page can
// render an empty-state without try/catch noise; other errors still throw so
// build/runtime regressions surface.
export async function getCallTimeline(
  callId: string,
): Promise<CallTimelineResponse | null> {
  try {
    return await apiFetch<CallTimelineResponse>(
      `/v1/calls/${encodeURIComponent(callId)}/timeline`,
      { revalidate: 60 },
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

// ---------- New Bookings (sales) tab fetchers ----------
//
// Both endpoints below are wired by the parallel BACKEND-A agent. If they
// haven't landed yet, the API returns 404 — we degrade to an empty payload so
// the page still renders skeletons instead of crashing.

export async function getRecentBookings(
  filters?: DashboardFilters,
): Promise<RecentBookingsResponse> {
  try {
    return await apiFetch<RecentBookingsResponse>(
      withFilters("/v1/dashboard/bookings", filters),
      { revalidate: 30 },
    );
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 405)) {
      return { bookings: [], count: 0 };
    }
    // Network / 5xx — still degrade gracefully so the sales page renders.
    return { bookings: [], count: 0 };
  }
}

export async function getAvailableLoads(
  filters?: DashboardFilters,
): Promise<AvailableLoadsResponse> {
  try {
    return await apiFetch<AvailableLoadsResponse>(
      withFilters("/v1/dashboard/loads/available", filters),
    );
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 405)) {
      return { loads: [], count: 0 };
    }
    return { loads: [], count: 0 };
  }
}

// ---------- /v1/dashboard/telemetry ----------
//
// Window-aggregated telemetry (RPM/TPM/latency/Extract/CHS) + per-call
// drilldown. Backend in `api/app/routers/telemetry.py`. The aggregate endpoint
// accepts optional from/to/bucket_minutes; the drilldown takes a `run_id`
// (which equals the HR `call_id` for runs originating in our workflow).

export type TelemetryAggregateOpts = {
  from?: Date;
  to?: Date;
  bucketMinutes?: number;
  maxRuns?: number;
};

export async function getTelemetry(
  opts?: TelemetryAggregateOpts,
): Promise<TelemetryAggregate | null> {
  const params = new URLSearchParams();
  if (opts?.from) params.set("from", opts.from.toISOString());
  if (opts?.to) params.set("to", opts.to.toISOString());
  if (opts?.bucketMinutes) params.set("bucket_minutes", String(opts.bucketMinutes));
  if (opts?.maxRuns) params.set("max_runs", String(opts.maxRuns));
  const qs = params.toString();
  const path = qs ? `/v1/dashboard/telemetry?${qs}` : "/v1/dashboard/telemetry";
  try {
    return await apiFetch<TelemetryAggregate>(path, { revalidate: 30 });
  } catch (err) {
    // 502 = HR run-details unreachable; degrade to null so the tab can render
    // an empty-state instead of crashing the page.
    if (err instanceof ApiError && (err.status === 502 || err.status === 503)) {
      return null;
    }
    throw err;
  }
}

export { ApiError };
