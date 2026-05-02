"use client";

// Per-tab reactive headline widget on the Monitor page.
// Listens to the active Tabs value (passed via prop) and renders one of:
//   - Economics  → Revenue captured (this period) + bookings + per-load avg
//   - Operational → 3-metric stack: avg duration, FMCSA-decline %, abandon %
//   - Quality    → Flagged-cases count (CHS<70) + sub-line
//   - Telemetry  → kept as combined booking-rate + margin (placeholder until
//                  per-tab Telemetry treatment is unblocked)

import { Card, CardContent } from "@/components/ui/card";
import { RatingDistribution } from "@/components/quality/rating-distribution";
import { FlaggedSentimentCard } from "@/components/quality/flagged-sentiment-card";
import { TelemetryReactiveWidget } from "@/components/telemetry/telemetry-reactive-widget";
import { fmtCurrency, fmtPct } from "@/lib/format";
import type {
  EconomicsMetrics,
  FunnelMetrics,
  OperationalMetrics,
  CallRecord,
  TelemetryAggregate,
} from "@/types/api-types";
import type { DailySentimentBucket } from "@/lib/daily-buckets";

type Props = {
  tab: "economics" | "operational" | "quality" | "telemetry";
  funnel: FunnelMetrics;
  economics: EconomicsMetrics;
  operational: OperationalMetrics;
  calls: CallRecord[];
  dailySentiment: DailySentimentBucket[];
  telemetry: TelemetryAggregate | null;
};

export function ReactiveWidget(props: Props) {
  switch (props.tab) {
    case "economics":
      return <EconomicsView e={props.economics} />;
    case "operational":
      return <OperationalView o={props.operational} />;
    case "quality":
      return (
        <QualityView
          calls={props.calls}
          dailySentiment={props.dailySentiment}
        />
      );
    case "telemetry":
      return (
        <TelemetryReactiveWidget
          telemetry={props.telemetry}
          calls={props.calls}
        />
      );
    default:
      return <FallbackView f={props.funnel} e={props.economics} />;
  }
}

function EconomicsView({ e }: { e: EconomicsMetrics }) {
  const perLoad =
    e.total_calls_with_rate > 0
      ? e.total_revenue_booked / e.total_calls_with_rate
      : null;
  return (
    <Card>
      <CardContent className="p-6">
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Revenue booked
        </p>
        <p className="mt-1 text-5xl font-semibold tabular-nums tracking-tight">
          {fmtCurrency(e.total_revenue_booked)}
        </p>
        <div className="mt-4 border-t border-border pt-4">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Margin vs list (total)
          </p>
          {/* Sign convention (locked 2026-05-01): negative = booked below list
              = margin captured (good). Render the raw signed value so the
              text matches the colour. */}
          <p
            className={`mt-1 text-2xl font-semibold tabular-nums ${
              e.effective_delta_dollars === null
                ? "text-muted-foreground"
                : e.effective_delta_dollars < 0
                  ? "text-success"
                  : e.effective_delta_dollars > 0
                    ? "text-destructive"
                    : "text-muted-foreground"
            }`}
          >
            {e.effective_delta_dollars === null
              ? "—"
              : fmtCurrency(e.effective_delta_dollars * e.total_calls_with_rate)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">
            {perLoad !== null ? `${fmtCurrency(perLoad)}/load avg · ` : ""}
            {e.total_calls_with_rate} bookings
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function OperationalView({ o }: { o: OperationalMetrics }) {
  return (
    <Card>
      <CardContent className="p-6 space-y-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Call duration (avg)
          </p>
          <p className="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
            {o.avg_duration_seconds !== null
              ? `${Math.round(o.avg_duration_seconds)}s`
              : "—"}
          </p>
        </div>
        <div className="border-t border-border pt-4">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Carriers turned away
          </p>
          <p className="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
            {fmtPct(o.fmcsa_decline_pct)}
          </p>
        </div>
        <div className="border-t border-border pt-4">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Drop-offs
          </p>
          <p className="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
            {fmtPct(o.abandon_rate_pct)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Calls hung up before booking
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function QualityView({
  calls,
  dailySentiment,
}: {
  calls: CallRecord[];
  dailySentiment: DailySentimentBucket[];
}) {
  // Quality reactive widget — locked 2026-05-01:
  // 1. Flagged + Favorable sentiment combined card (side-by-side)
  // 2. Rating distribution (3 buckets)
  return (
    <div className="space-y-3">
      <FlaggedSentimentCard calls={calls} dailySentiment={dailySentiment} />
      <RatingDistribution calls={calls} />
    </div>
  );
}

function FallbackView({
  f,
  e,
}: {
  f: FunnelMetrics;
  e: EconomicsMetrics;
}) {
  // Sign convention (locked 2026-05-01): negative = below list = margin
  // captured (good). Match the SalesRepCard / EconomicsCards / hero chart.
  const total =
    e.effective_delta_dollars !== null
      ? e.effective_delta_dollars * e.total_calls_with_rate
      : null;
  return (
    <Card>
      <CardContent className="p-6">
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Booking rate
        </p>
        <p className="mt-1 text-5xl font-semibold tabular-nums tracking-tight">
          {fmtPct(f.booking_rate_pct)}
        </p>
        <div className="mt-4 border-t border-border pt-4">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Margin vs list (total)
          </p>
          <p
            className={`mt-1 text-2xl font-semibold tabular-nums ${
              total === null
                ? "text-muted-foreground"
                : total < 0
                  ? "text-success"
                  : total > 0
                    ? "text-destructive"
                    : "text-muted-foreground"
            }`}
          >
            {total === null ? "—" : fmtCurrency(total)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
