import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { fmtMs, fmtNumber } from "@/lib/format";
import type { TelemetryAggregate } from "@/types/api-types";

// 6-tile horizontal mini-strip across the top of the Telemetry tab. Mirrors
// `OperationalCards` density but renders the phase badge inline so the broker
// can tell at a glance whether the latency numbers are HR run-details (live)
// or transcript-count (approx, ADR-012 fallback).

type StatProps = {
  label: string;
  value: string;
};

function Stat({ label, value }: StatProps) {
  return (
    <div className="flex flex-1 flex-col gap-0.5 px-3 py-2">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="font-mono text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function PhaseBadge({ phase }: { phase: "phase1" | "phase2" }) {
  const isLive = phase === "phase2";
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider",
              isLive
                ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400"
                : "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                isLive ? "bg-cyan-500" : "bg-amber-500",
              )}
              aria-hidden
            />
            {isLive ? "live" : "approx"}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          {isLive
            ? "HR run-details API supplied per-node start/end timestamps."
            : "Phase 1 transcript-count fallback — see ADR-012."}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Latency sample value rules: when the source is `transcript_count` the
// upstream returns null per-percentile (we can only report a turn count), so
// we must show "—" not 0. The newer `transcript` source has the same null
// semantics for windows with no sampled runs.
function fmtLatency(
  value: number | null,
  source: TelemetryAggregate["latency"]["source"],
): string {
  if ((source === "transcript_count" || source === "transcript") && value === null) {
    return "—";
  }
  return fmtMs(value);
}

export function TelemetryKpiStrip({ data }: { data: TelemetryAggregate }) {
  const { latency, totals } = data;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Telemetry · aggregate
        </div>
        <PhaseBadge phase={latency.phase} />
      </div>
      <div className="grid grid-cols-2 divide-x sm:grid-cols-3 lg:grid-cols-5">
        <Stat label="Total runs" value={fmtNumber(totals.runs)} />
        <Stat
          label="p50"
          value={fmtLatency(latency.p50_ms, latency.source)}
        />
        <Stat
          label="p70"
          value={fmtLatency(latency.p70_ms, latency.source)}
        />
        <Stat
          label="p90"
          value={fmtLatency(latency.p90_ms, latency.source)}
        />
        <Stat
          label="p99"
          value={fmtLatency(latency.p99_ms, latency.source)}
        />
      </div>
    </Card>
  );
}
