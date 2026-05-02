// Hand-mirrored response types for the FastAPI dashboard endpoints.
//
// Source of truth: api/app/models.py (FunnelMetrics, EconomicsMetrics,
// OperationalMetrics, QualityMetrics, ObservabilityMetrics, CarrierRollupMetrics,
// CarrierRollupRow, CallRecord, AlertResult).
//
// Run `npm run gen:types` to also generate the full openapi-typescript bundle
// at src/types/api.d.ts (this file remains the curated, ergonomic surface used
// by the dashboard pages).

// Daily-bucketed series point for the inline Recharts spark area on KPI
// cards. `d` is an ISO date (YYYY-MM-DD), `v` is the numeric value (count,
// dollars, mean — depends on the metric).
export type SparklinePoint = { d: string; v: number };

export type FunnelMetrics = {
  total_calls: number;
  by_outcome: Record<string, number>;
  booking_rate_pct: number;
  // % change vs the same-length prior window. null = no comparable prior
  // (window starts before any data).
  delta_pct_vs_prior?: number | null;
  sparkline?: SparklinePoint[];
};

export type EconomicsMetrics = {
  total_calls_with_rate: number;
  avg_loadboard_rate: number | null;
  avg_agreed_rate: number | null;
  // Effective delta = avg_agreed_rate - avg_loadboard_rate.
  // Negative = below list (broker margin captured); positive = above list
  // (concession given). _pct = (agreed - loadboard) / loadboard × 100.
  effective_delta_dollars: number | null;
  effective_delta_pct: number | null;
  total_revenue_booked: number;
  // Tracks total_revenue_booked vs the prior same-length window.
  delta_pct_vs_prior?: number | null;
  sparkline?: SparklinePoint[];
};

// Hero chart payload — daily mean of (apply_rate - loadboard_rate).
// `v` may be null on days with no bookings (chart suppresses, doesn't zero).
export type EffectiveDeltaPoint = {
  d: string;
  v: number | null;
  n: number;
};

export type EffectiveDeltaSeries = {
  series: EffectiveDeltaPoint[];
};

// Per-carrier rollup shape returned by GET /v1/carriers/{mc_number}.
// Source of truth: api/app/routers/carriers.py::_carrier_stats.
export type CarrierProfile = {
  mc_number: string;
  total_calls: number;
  total_bookings: number;
  conversion_rate: number; // 0.0 – 1.0 (NOT pre-multiplied by 100)
  avg_apply_rate: number | null;
  last_call_at: string | null;
  sentiment_breakdown: {
    positive: number;
    neutral: number;
    negative: number;
  };
  outcome_breakdown: {
    load_booked: number;
    carrier_not_qualified: number;
    call_abandoned: number;
    non_load_booking_engagement: number;
  };
};

export type OperationalMetrics = {
  // Source of truth: api/app/models.py::OperationalMetrics. v15 schema dropped
  // negotiation tracking; current shape is duration + decline + abandon rates.
  avg_duration_seconds: number | null;
  fmcsa_decline_pct: number | null;
  abandon_rate_pct: number | null;
  // Tracks avg_duration_seconds vs the prior same-length window.
  delta_pct_vs_prior?: number | null;
  sparkline?: SparklinePoint[];
};

export type QualityMetrics = {
  sentiment_distribution: Record<string, number>;
  outcome_distribution: Record<string, number>;
  // CHS distribution as 5 buckets (0-20, 20-40, 40-60, 60-80, 80-100) → count.
  chs_distribution: Record<string, number>;
  avg_case_health_score: number | null;
  auditor_remarks_sample: string[];
  // Tracks avg_case_health_score vs the prior same-length window.
  delta_pct_vs_prior?: number | null;
  sparkline?: SparklinePoint[];
};

export type AlertResult = {
  name: string;
  severity: "info" | "warn" | "page";
  value: number | null;
  threshold: number | null;
  fired: boolean;
  detail: string | null;
};

export type ObservabilityMetrics = {
  generated_at: string;
  alerts: AlertResult[];
  case_health_series: number[];
  booking_rate_series: number[];
  audit_remark_tags: { tag: string; count: number }[];
};

export type CarrierRollupRow = {
  mc_number: string | null;
  carrier_name: string | null;
  call_count: number;
  booked_count: number;
  booking_rate_pct: number;
  avg_chs: number | null;
  last_call_at: string | null;
  // Mean ((apply_rate − loadboard_rate) / loadboard_rate * 100) over this MC's
  // bookings in the window. Negative = below list (margin captured);
  // positive = above list (concession). Null when the MC has zero priced
  // bookings in the window.
  avg_booking_margin_pct?: number | null;
};

export type CarrierRollupMetrics = {
  top_carriers: CarrierRollupRow[];
  total_unique_carriers: number;
};

// CallRecord mirrors calls_log row dicts (v2 schema, 32 columns).
// Every field is nullable because HR's Write-to-Twin may not populate every
// column on every call. Post-v15: rate fields live on bookings rows; CallRecord
// carries `apply_rate` only if the API joins bookings into the row dict.
export type CallRecord = {
  // identity
  id?: number | null;
  created_at?: string | null;
  call_id?: string | null;

  // caller
  mc_number?: string | null;
  carrier_name?: string | null;
  callback_phone?: string | null;
  fmcsa_eligibility_failure_reason?: string | null;

  // lane (transcript-derived via Extract)
  lane_origin?: string | null;
  lane_dest?: string | null;

  // quality
  call_outcome?: string | null;
  sentiment?: string | null;
  case_health_score?: number | null;
  audit_remarks?: string | null;
  notes?: string | null;

  // session (reserved; currently unbound in HR)
  hangup_reason?: string | null;
  room_name?: string | null;
  status?: string | null;

  // conversation data
  transcript?: string | null;

  // token usage — Extract Call Details
  extract_input_tokens?: number | null;
  extract_output_tokens?: number | null;
  extract_reasoning_tokens?: number | null;
  extract_cached_input_tokens?: number | null;
  extract_uncached_input_tokens?: number | null;

  // token usage — Case Health Score
  chs_input_tokens?: number | null;
  chs_output_tokens?: number | null;
  chs_reasoning_tokens?: number | null;
  chs_cached_input_tokens?: number | null;
  chs_uncached_input_tokens?: number | null;

  // operational telemetry — duration is real; the other 3 are HR-side NULL per
  // ADR-012 (kept defensively in case HR fixes the platform bug). Dashboard
  // derives latency from HR REST API /runs/{call_id}/nodes timestamps.
  duration_seconds?: number | null;
  intermediate_response_count?: number | null;
  p70_latency_ms?: number | null;
  p90_latency_ms?: number | null;

  // joined from bookings (when API merges); not a calls_log column
  apply_rate?: number | null;
  load_id?: string | null;

  // DEPRECATED — never populated under v2 schema. Several dashboard components
  // still nullish-fallback to it (`r.carrier_name ?? r.legal_name`); the chain
  // resolves to undefined harmlessly. Drop this + the fallbacks together.
  legal_name?: string | null;
};

// Full load row shape, mirrored from `data/loads.json` + Twin `loads` table.
// Used by the embedded `load` field on bookings + the available-loads list.
export type LoadFull = {
  load_id?: string | null;
  origin_city?: string | null;
  origin_state?: string | null;
  destination_city?: string | null;
  destination_state?: string | null;
  equipment_type?: string | null;
  loadboard_rate?: number | null;
  miles?: number | null;
  weight?: number | null;
  commodity_type?: string | null;
  num_of_pieces?: number | null;
  dimensions?: string | null;
  pickup_datetime?: string | null;
  delivery_datetime?: string | null;
  notes?: string | null;
};

// Recent-bookings row for the New Bookings (sales) tab.
// Source: GET /v1/dashboard/bookings.
export type RecentBooking = {
  booking_id: number;
  booked_at: string;
  mc_number: string;
  call_id: string;
  call: {
    call_outcome: string | null;
    sentiment: string | null;
    case_health_score: number | null;
    duration_seconds: number | null;
  };
  apply_rate: number | null;
  load: LoadFull | null;
};

export type RecentBookingsResponse = {
  bookings: RecentBooking[];
  count: number;
};

// Available (unpitched) loads for the New Bookings (sales) tab.
// Source: GET /v1/dashboard/loads/available.
export type AvailableLoad = LoadFull;

export type AvailableLoadsResponse = {
  loads: AvailableLoad[];
  count: number;
};

// Sentiment + outcome enum surface used by chart components.
export type Sentiment = "positive" | "neutral" | "negative";
export type Outcome =
  | "load_booked"
  | "no_match"
  | "carrier_not_qualified"
  | "call_abandoned"
  | string;

// ---------------------------- /v1/dashboard/telemetry ----------------------
// Mirrors `api/app/routers/telemetry.py` + `transcript_telemetry.py` widget
// bundles. Phase 1 (transcript count fallback) vs Phase 2 (HR run-details
// per-node timestamps) is signalled via `latency.phase`. See ADR-012.

export type TelemetryRpmPoint = { t: string; rpm: number };
export type TelemetryTpmPoint = { t: string; tpm: number };

export type TelemetryLatency = {
  phase: "phase1" | "phase2";
  // "transcript" = post-call transcript-derived (current production source).
  // "hr_rest_api" / "transcript_count" are legacy phase-1/phase-2 labels kept
  // for backward compatibility with older payloads.
  source: "hr_rest_api" | "transcript_count" | "transcript";
  sample_count: number;
  p50_ms: number | null;
  p70_ms: number | null;
  p90_ms: number | null;
  p99_ms: number | null;
};

export type TelemetryLatencyPoint = {
  t: string;
  n: number;
  p50_ms: number | null;
  p70_ms: number | null;
  p90_ms: number | null;
  p99_ms: number | null;
};

export type TelemetryToolLatency = {
  sample_count: number;
  p50_ms: number | null;
  p70_ms: number | null;
  p90_ms: number | null;
  p99_ms: number | null;
  series: TelemetryLatencyPoint[];
};

export type TelemetryAggregate = {
  window: { from: string; to: string; bucket_minutes: number };
  totals: { runs: number; node_samples: number };
  rpm_series: TelemetryRpmPoint[];
  tpm_series: TelemetryTpmPoint[];
  latency: TelemetryLatency;
  latency_series: TelemetryLatencyPoint[];
  // Per-tool breakdown — each tool_name maps to its own headline percentiles +
  // bucketed series. Used by the latency-card tool filter and by the active
  // alerts widget to name the offending tool when a threshold breaches.
  latency_by_tool?: Record<string, TelemetryToolLatency>;
};

// ---------------------------- /v1/calls/{call_id}/timeline ------------------
// Per-turn conversation timeline derived from the post-call transcript +
// node-level timestamps. Source of truth: `api/app/routers/calls.py`. Used by
// the per-call drilldown page for conversational flow + token totals.
//
// `kind` enumerates the four turn shapes the backend emits. `args`/`result`
// are arbitrary JSON shapes; we keep them as `Record<string, unknown>` so the
// renderer can pretty-print without coupling to specific tool signatures.
// `tool_name` is only present on tool_call / tool_result entries.
export type CallTimelineEntryKind =
  | "assistant_message"
  | "assistant_tool_call"
  | "user_message"
  | "tool_result";

export type CallTimelineEntry = {
  kind: CallTimelineEntryKind;
  timestamp: string;
  content?: string | null;
  tool_name?: string | null;
  args?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  // Backend-attached duration on tool_result entries (round-trip ms from the
  // matching assistant_tool_call). Optional — falls back to "—" if absent.
  duration_ms?: number | null;
};

export type CallTimelineToolCallSummary = {
  tool_name: string;
  duration_ms: number | null;
};

export type CallTimelineSummary = {
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  turn_count: number;
  assistant_turn_count: number;
  user_turn_count: number;
  tool_call_count: number;
  tool_result_count: number;
  time_to_first_assistant_response_ms: number | null;
  per_turn_gaps_ms: number[];
  assistant_response_latency_ms: number[];
  tool_calls: CallTimelineToolCallSummary[];
  agent_input_tokens?: number | null;
  agent_output_tokens?: number | null;
  tool_input_tokens?: number | null;
  tool_output_tokens?: number | null;
};

export type CallTimelineResponse = {
  call_id: string;
  timeline: CallTimelineEntry[];
  summary: CallTimelineSummary;
};
