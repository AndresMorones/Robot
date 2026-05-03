"""Pydantic request/response models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# Sparkline shape: list of {d: ISO-date, v: numeric}. Daily-bucketed series
# powering the Tremor SparkAreaChart slot in each KPI card. We keep the value
# loose (`Any`) so int/float counts and floats both serialize cleanly.
SparklinePoint = dict[str, Any]


class Load(BaseModel):
    """A freight load — covers all 13 spec fields plus split origin/destination for filterability."""

    load_id: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    weight: float | None = None
    commodity_type: str | None = None
    num_of_pieces: int | None = None
    miles: int | None = None
    dimensions: str | None = None
    notes: str | None = None

    @property
    def origin(self) -> str:
        return f"{self.origin_city}, {self.origin_state}"

    @property
    def destination(self) -> str:
        return f"{self.destination_city}, {self.destination_state}"

    def to_response_dict(self) -> dict:
        """JSON response shape — includes derived `origin`/`destination` strings for spec compliance."""
        d = self.model_dump(mode="json")
        d["origin"] = self.origin
        d["destination"] = self.destination
        return d


class LoadSearchRequest(BaseModel):
    origin_state: str | None = None
    destination_state: str | None = None
    equipment_type: str | None = None
    pickup_after: datetime | None = None
    max_results: int = 5


class LoadSearchResponse(BaseModel):
    matches: list[dict]
    total_in_store: int


class CallRecord(BaseModel):
    """Mirrors the v15 calls_log Twin table (12 cols).

    All fields nullable — abandoned calls / partial Extract runs leave the
    classification + sentiment + CHS columns NULL. Per-booking fields (rate,
    load_id) live in the `bookings` table joined on `call_id`.
    """

    id: int | None = None
    call_id: str | None = None
    mc_number: str | None = None
    call_outcome: str | None = None
    sentiment: str | None = None
    case_health_score: int | None = None
    audit_remarks: str | None = None
    fmcsa_eligibility_failure_reason: str | None = None
    callback_phone: str | None = None
    duration_seconds: int | None = None
    transcript: str | None = None
    created_at: datetime | None = None


class FunnelMetrics(BaseModel):
    total_calls: int
    by_outcome: dict[str, int]
    booking_rate_pct: float
    # v2 spark-card surfaces. `delta_pct_vs_prior` is the % change in
    # total_calls relative to the same-length prior window; `sparkline` is the
    # daily-bucketed call count over the requested window.
    delta_pct_vs_prior: float | None = None
    sparkline: list[SparklinePoint] = Field(default_factory=list)


class EconomicsMetrics(BaseModel):
    """Rate KPIs sourced from the bookings + loads join.

    `avg_loadboard_rate` = AVG(loads.loadboard_rate) for booked loads (the
    list/ceiling rate).
    `avg_agreed_rate` = AVG(bookings.apply_rate) — what we actually agreed to
    pay the carrier. Sourced from the `bookings` table (NOT calls_log).
    `effective_delta_dollars` = avg_agreed_rate - avg_loadboard_rate. Negative
    when we negotiated below list (broker upside).
    `effective_delta_pct` = (agreed - loadboard) / loadboard × 100.
    """

    total_calls_with_rate: int
    avg_loadboard_rate: float | None
    avg_agreed_rate: float | None
    effective_delta_dollars: float | None
    effective_delta_pct: float | None
    total_revenue_booked: float
    # v2 spark-card surfaces. Delta tracks total_revenue_booked vs the prior
    # window of equal length; sparkline is the daily revenue bucket.
    delta_pct_vs_prior: float | None = None
    sparkline: list[SparklinePoint] = Field(default_factory=list)


class OperationalMetrics(BaseModel):
    """Operational signals computed from calls_log post-v15 cleanup.

    Negotiation-rounds metrics were dropped (multi-load loop pattern moved
    per-load detail into `bookings`). New fields surface call duration, FMCSA
    decline rate, and abandon rate (no carrier follow-through).
    """

    avg_duration_seconds: float | None
    fmcsa_decline_pct: float | None
    abandon_rate_pct: float | None
    no_match_pct: float | None = None
    # v2 spark-card surfaces. Delta tracks avg_duration_seconds vs the prior
    # window; sparkline is the daily mean duration.
    delta_pct_vs_prior: float | None = None
    sparkline: list[SparklinePoint] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    sentiment_distribution: dict[str, int]
    outcome_distribution: dict[str, int]
    chs_distribution: dict[str, int]
    avg_case_health_score: float | None
    auditor_remarks_sample: list[str]
    # v2 spark-card surfaces. Delta tracks avg_case_health_score vs the prior
    # window; sparkline is the daily mean CHS.
    delta_pct_vs_prior: float | None = None
    sparkline: list[SparklinePoint] = Field(default_factory=list)


class AlertResult(BaseModel):
    name: str
    severity: Literal["info", "warn", "page"]
    value: float | None
    threshold: float | None
    fired: bool
    detail: str | None


class ObservabilityMetrics(BaseModel):
    generated_at: datetime
    alerts: list[AlertResult]
    case_health_series: list[float]
    booking_rate_series: list[float]
    audit_remark_tags: list[dict]


class CarrierRollupRow(BaseModel):
    mc_number: str | None
    carrier_name: str | None
    call_count: int
    booked_count: int
    booking_rate_pct: float
    avg_chs: float | None
    last_call_at: datetime | None
    # Avg booking margin per MC, expressed as % of list rate:
    # mean((apply_rate − loadboard_rate) / loadboard_rate * 100) across the
    # carrier's bookings in the window. Negative = below list (margin captured),
    # positive = above list (concession). Null when the MC has zero priced
    # bookings in the window. Sign convention matches the rest of the dashboard.
    avg_booking_margin_pct: float | None = None


class CarrierRollupMetrics(BaseModel):
    top_carriers: list[CarrierRollupRow]
    total_unique_carriers: int


# ----------------------------------------------------------- recent bookings
#
# Powers the dashboard's "Recent bookings" feed — joins bookings to
# calls_log (call_outcome / sentiment / CHS / duration) and to loads (lane
# + spec). All sub-objects are nullable because either side of the join
# may be missing in degraded cases (call ingested but no booking yet, or
# stale booking pointing at a deleted load).


class BookingCallSummary(BaseModel):
    call_outcome: str | None = None
    sentiment: str | None = None
    case_health_score: int | None = None
    duration_seconds: int | None = None


class BookingLoadSummary(BaseModel):
    load_id: str
    origin_city: str | None = None
    origin_state: str | None = None
    destination_city: str | None = None
    destination_state: str | None = None
    equipment_type: str | None = None
    loadboard_rate: float | None = None
    miles: int | None = None
    weight: float | None = None
    commodity_type: str | None = None
    num_of_pieces: int | None = None
    dimensions: str | None = None
    pickup_datetime: datetime | None = None
    delivery_datetime: datetime | None = None
    notes: str | None = None


class RecentBookingRow(BaseModel):
    booking_id: int | None = None
    booked_at: datetime | None = None
    mc_number: str | None = None
    call_id: str | None = None
    call: BookingCallSummary | None = None
    apply_rate: float | None = None
    load: BookingLoadSummary | None = None


class RecentBookingsResponse(BaseModel):
    bookings: list[RecentBookingRow]
    count: int


# --------------------------------------------------------- available loads


class AvailableLoadRow(BaseModel):
    load_id: str
    origin_city: str | None = None
    origin_state: str | None = None
    destination_city: str | None = None
    destination_state: str | None = None
    equipment_type: str | None = None
    loadboard_rate: float | None = None
    miles: int | None = None
    weight: float | None = None
    commodity_type: str | None = None
    pickup_datetime: datetime | None = None
    delivery_datetime: datetime | None = None
    notes: str | None = None


class AvailableLoadsResponse(BaseModel):
    loads: list[AvailableLoadRow]
    count: int


# ----------------------------------------------------- transcript timeline
#
# Wraps the transcript_parser output for the dashboard call drill-down. Every
# field is nullable on the wire because pathological transcripts (missing IDs,
# malformed JSON, no user offsets) must not crash the endpoint — the parser
# already degrades gracefully and the response model honors that.


class TranscriptToolCall(BaseModel):
    """One tool_call ↔ tool_result pair with derived timing.

    `started_at` is the assistant turn's UUIDv7 wall-clock; `ended_at` is the
    next event's wall-clock (best available proxy — tool result rows don't
    carry their own timestamp). `duration_ms` is the gap between them.
    """

    tool_name: str | None = None
    args: Any = None
    result: Any = None
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: int | None = None


class TranscriptSummary(BaseModel):
    started_at: str | None = None
    ended_at: str | None = None
    duration_seconds: int | None = None
    turn_count: int = 0
    assistant_turn_count: int = 0
    user_turn_count: int = 0
    tool_call_count: int = 0
    tool_result_count: int = 0
    time_to_first_assistant_response_ms: int | None = None
    tool_calls: list[TranscriptToolCall] = Field(default_factory=list)
    per_turn_gaps_ms: list[int] = Field(default_factory=list)
    assistant_response_latency_ms: list[int] = Field(default_factory=list)
    # Token totals per role family. Counted with tiktoken o200k_base when
    # available; falls back to char-len/4 when the lib isn't importable so the
    # endpoint never 500s on a missing optional dep. None when no text observed.
    agent_input_tokens: int | None = None
    agent_output_tokens: int | None = None
    tool_input_tokens: int | None = None
    tool_output_tokens: int | None = None


class TranscriptTimelineEntry(BaseModel):
    """One wire-shape timeline row consumed by the Next.js dashboard.

    Distinct from the parser's internal event shape (which uses `text`,
    `wall_clock`, nested `tool_calls` per assistant turn, nested `tool_result`
    per tool turn). The router flattens that to a per-tool-call row plus a
    leading assistant_message row when the same assistant turn carried both
    spoken content AND a tool invocation — so the dashboard renders the
    preamble ("Looking up load 0010.") as its own bubble before the tool card.
    """

    kind: str
    timestamp: str | None = None
    content: str | None = None
    tool_name: str | None = None
    args: Any = None
    result: Any = None
    duration_ms: int | None = None


class TranscriptTimelineResponse(BaseModel):
    call_id: str
    timeline: list[TranscriptTimelineEntry]
    summary: TranscriptSummary
