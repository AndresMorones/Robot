import { fmtNumber, fmtPct } from "@/lib/format";
import type {
  FunnelMetrics,
  OperationalMetrics,
  QualityMetrics,
  TelemetryAggregate,
} from "@/types/api-types";

import { SigmaKpiCell } from "./sigma-kpi-cell";

// Sigma Spreadsheet KPI band — frozen merged-cell strip pinned to the top of
// the Calls tab. 6 equal-rank cells with in-cell horizontal data bars + a
// CHS-tinted background on the case-health cell.
//
// Locked theme composite (memory: project_dashboard_theme_composite_locked):
// gridlines on `--border` (#232328), bars in success / destructive, CHS bg
// at 14% opacity. Calls tab only — Overview keeps the Freight Terminal
// asymmetric KPI strip.
//
// Server Component. No interactivity here; the band is read-only signal.

const SUCCESS_BOOK_RATE_TARGET = 0.5; // 50% booked is the "fully filled bar".
const SUCCESS_AHT_FLOOR_S = 30; // <=30s AHT renders a full bar.
const SUCCESS_AHT_CEIL_S = 600; // >=600s AHT renders an empty bar.
const TARGET_TOTAL_CALLS_BAR_REF = 200; // Bar fills at 200+ calls in window.

// CHS tint mapping per locked spec: <70 red, 70-89 amber, >=90 green.
function chsBgTone(score: number | null | undefined): "bad" | "warn" | "good" | null {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  if (score < 70) return "bad";
  if (score < 90) return "warn";
  return "good";
}

// Format AHT seconds as mm:ss for the cell value.
function fmtMmSs(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "—";
  const s = Math.max(0, Math.round(seconds));
  const mm = Math.floor(s / 60).toString().padStart(2, "0");
  const ss = (s % 60).toString().padStart(2, "0");
  return `${mm}:${ss}`;
}

// Inverse-map AHT to a 0..1 bar — shorter = greener (fuller bar).
function ahtBar(seconds: number | null | undefined): number {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return 0;
  if (seconds <= SUCCESS_AHT_FLOOR_S) return 1;
  if (seconds >= SUCCESS_AHT_CEIL_S) return 0;
  return 1 - (seconds - SUCCESS_AHT_FLOOR_S) / (SUCCESS_AHT_CEIL_S - SUCCESS_AHT_FLOOR_S);
}

// Drop-off bar fills proportional to abandon rate; 30%+ saturates.
const DROP_OFF_BAR_CEIL_PCT = 30;
// Tool error bar saturates at 20% — anything above is unambiguously bad.
const TOOL_ERR_BAR_CEIL_PCT = 20;

export type SigmaKpiBandProps = {
  funnel: FunnelMetrics;
  operational: OperationalMetrics;
  quality: QualityMetrics;
  telemetry: TelemetryAggregate | null;
};

export function SigmaKpiBand({
  funnel,
  operational,
  quality,
  telemetry,
}: SigmaKpiBandProps): React.JSX.Element {
  // ---- 1. Total calls — bar fills against a reference window count.
  const totalCalls = funnel.total_calls ?? 0;
  const totalCallsBar = Math.min(totalCalls / TARGET_TOTAL_CALLS_BAR_REF, 1);

  // ---- 2. Booked rate — bar = rate / target (capped at 100%).
  const bookedRatePct = funnel.booking_rate_pct ?? 0;
  const bookedRateBar = Math.min(bookedRatePct / 100 / SUCCESS_BOOK_RATE_TARGET, 1);

  // ---- 3. Avg case-health score — bar = score/100, CHS-tinted bg.
  const chs = quality.avg_case_health_score;
  const chsBar = chs !== null && chs !== undefined ? Math.min(chs / 100, 1) : 0;
  const chsTone = chsBgTone(chs);

  // ---- 4. Avg handle time — derive from operational.avg_duration_seconds.
  const aht = operational.avg_duration_seconds;
  // Shorter is better, so positive (green) when below the ceiling.
  const ahtPos = aht !== null && aht !== undefined && aht <= SUCCESS_AHT_CEIL_S;

  // ---- 5. No match — % of calls where no matching load was found
  // (call_outcome = "no_match" / total). Lower is better.
  const noMatchPct = operational.no_match_pct ?? null;
  const noMatchBar =
    noMatchPct !== null
      ? Math.min(noMatchPct / DROP_OFF_BAR_CEIL_PCT, 1)
      : 0;
  // Positive (green) when no-match rate is low (<10%).
  const noMatchPos = noMatchPct !== null && noMatchPct < 10;

  // ---- 6. Tool error rate — % of tool calls that returned an error or
  // never returned (timeout). Computed dashboard-side from transcripts in
  // `transcript_aggregations._tool_error_count`. Lower is better.
  const toolErrPct = telemetry?.totals.tool_error_rate_pct ?? null;
  const toolErrBar =
    toolErrPct !== null
      ? Math.min(toolErrPct / TOOL_ERR_BAR_CEIL_PCT, 1)
      : 0;
  const toolErrPos = toolErrPct !== null && toolErrPct < 5;

  return (
    <div
      className={[
        // Sticky frozen band — pins below the global Header (which sits at
        // z-40 with h-14 / top-0). We sit just below at z-30 so the Header's
        // backdrop blur stays on top during scroll.
        "sticky top-14 z-30",
        "border-y border-border bg-background",
        "supports-[backdrop-filter]:bg-background/85",
        "supports-[backdrop-filter]:backdrop-blur-md",
      ].join(" ")}
      role="group"
      aria-label="Calls KPI band"
    >
      <div className="grid grid-cols-3 sm:grid-cols-6">
        <SigmaKpiCell
          label="Total calls"
          value={fmtNumber(totalCalls)}
          bar={totalCallsBar}
          pos
          hint={`vs ${TARGET_TOTAL_CALLS_BAR_REF} ref`}
        />
        <SigmaKpiCell
          label="Booked rate"
          value={fmtPct(bookedRatePct)}
          bar={bookedRateBar}
          pos={bookedRatePct > 0}
          hint={`tgt ${(SUCCESS_BOOK_RATE_TARGET * 100).toFixed(0)}%`}
        />
        <SigmaKpiCell
          label="Avg CHS"
          value={chs !== null && chs !== undefined ? chs.toFixed(1) : "—"}
          bar={chsBar}
          pos={(chs ?? 0) >= 70}
          bgTone={chsTone}
          hint="/100 · ≥70 passes"
          isMobileRowEnd
        />
        <SigmaKpiCell
          label="Avg handle"
          value={fmtMmSs(aht)}
          bar={ahtBar(aht)}
          pos={ahtPos}
          hint="mm:ss · shorter better"
        />
        <SigmaKpiCell
          label="No match"
          value={noMatchPct !== null ? fmtPct(noMatchPct) : "—"}
          bar={noMatchBar}
          pos={noMatchPos}
          hint="no matching load found"
        />
        <SigmaKpiCell
          label="Tool error rate"
          value={toolErrPct !== null ? fmtPct(toolErrPct) : "—"}
          bar={toolErrBar}
          pos={toolErrPos}
          hint="errors + timeouts"
          isLast
        />
      </div>
    </div>
  );
}
