"use client";

import { fmtCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RecentBooking } from "@/types/api-types";

import type { PipelineEntry, PipelineState } from "./use-pipeline-state";

// Compressed booking card used inside each pipeline column. Density target:
// lane + margin pill + apply-rate + MC/CHS in ~60px tall. Dimmed for non-
// pending states; click anywhere to open the slide-over detail panel.

type Props = {
  booking: RecentBooking;
  state: PipelineState;
  entry: PipelineEntry | null;
  onClick: () => void;
};

const STATE_BORDER: Record<PipelineState, string> = {
  pending: "border-l-success",
  approved: "border-l-border",
  rejected: "border-l-destructive",
};

const STATE_OPACITY: Record<PipelineState, string> = {
  pending: "opacity-100",
  approved: "opacity-70",
  rejected: "opacity-70",
};

function laneLabel(b: RecentBooking): string {
  const o = b.load?.origin_city;
  const oS = b.load?.origin_state;
  const d = b.load?.destination_city;
  const dS = b.load?.destination_state;
  if (!o && !d) return "Unknown lane";
  const left = [o, oS].filter(Boolean).join(", ") || "??";
  const right = [d, dS].filter(Boolean).join(", ") || "??";
  return `${left} → ${right}`;
}

function laneShort(b: RecentBooking): string {
  // Three-letter abbreviation when possible (PHX → DEN).
  const o = b.load?.origin_city;
  const d = b.load?.destination_city;
  if (!o && !d) return "—";
  const ab = (s: string | null | undefined) =>
    (s ?? "")
      .split(/[\s-]/)
      .map((w) => w[0] || "")
      .join("")
      .slice(0, 3)
      .toUpperCase() || "??";
  return `${ab(o)} → ${ab(d)}`;
}

function marginPct(b: RecentBooking): number | null {
  const apply = b.apply_rate;
  const list = b.load?.loadboard_rate ?? null;
  if (apply == null || list == null || list === 0) return null;
  // Sign convention: NEGATIVE = below list = margin captured (good).
  // For the pill we display the user-facing magnitude with sign, so the
  // broker sees +12.5% when below list, −2.4% when above (concession).
  // Flipping sign here keeps the visual rule consistent with the
  // "green = good" convention without requiring a mental inversion.
  return ((list - apply) / list) * 100;
}

export function PipelineCard({ booking, state, entry, onClick }: Props) {
  const lane = laneShort(booking);
  const fullLane = laneLabel(booking);
  const margin = marginPct(booking);
  const marginPositive = margin !== null && margin > 0;
  const marginNegative = margin !== null && margin < 0;
  const chs = booking.call?.case_health_score ?? null;
  const apply = booking.apply_rate;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-md border border-border bg-card",
        "border-l-2 px-3 py-2 transition-colors hover:bg-card/70",
        STATE_BORDER[state],
        STATE_OPACITY[state],
      )}
      title={fullLane}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs font-medium text-foreground">
          {lane}
          {state === "approved" ? (
            <span className="ml-1.5 text-[10px] text-success">✓</span>
          ) : null}
        </span>
        {margin !== null ? (
          <span
            className={cn(
              "shrink-0 rounded-sm px-1.5 py-0.5 font-mono text-[10px] tabular-nums",
              marginPositive && "bg-success/15 text-success",
              marginNegative && "bg-destructive/15 text-destructive",
              !marginPositive && !marginNegative && "bg-muted text-muted-foreground",
            )}
          >
            {marginPositive ? "+" : ""}
            {margin.toFixed(1)}%
          </span>
        ) : (
          <span className="shrink-0 text-[10px] text-muted-foreground">—</span>
        )}
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 font-mono text-[10px] text-muted-foreground">
        <span className="truncate">
          {fmtCurrency(apply)} · {booking.mc_number}
          {chs !== null ? <> · ●{chs}</> : null}
        </span>
        {state === "rejected" && entry?.reason ? (
          <span className="shrink-0 text-destructive">{entry.reason}</span>
        ) : null}
      </div>
    </button>
  );
}
