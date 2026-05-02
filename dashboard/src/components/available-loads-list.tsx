import { ArrowRight } from "lucide-react";

import { fmtCurrency, fmtNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AvailableLoad } from "@/types/api-types";

// Compact card stack for unpitched loads — shown in the right column of the
// sales page beneath the in-flight calls panel. Server-rendered (no polling
// required) — server-side fetch through getAvailableLoads().
//
// Visually quieter than <SalesRepCard /> on purpose: this is inventory the
// rep can pitch, not finished work.

const MAX_ROWS = 6;

function lane(load: AvailableLoad): { origin: string; destination: string } {
  const origin =
    [load.origin_city, load.origin_state].filter(Boolean).join(", ") || "—";
  const destination =
    [load.destination_city, load.destination_state].filter(Boolean).join(", ") ||
    "—";
  return { origin, destination };
}

export function AvailableLoadsList({
  loads,
}: {
  loads: AvailableLoad[];
}): React.JSX.Element {
  const rows = loads.slice(0, MAX_ROWS);

  return (
    <div className="rounded-lg border border-border bg-card">
      <header className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h2 className="text-sm font-semibold tracking-tight">
          Available loads
        </h2>
        <span className="text-xs tabular-nums text-muted-foreground">
          {fmtNumber(loads.length)} ready
        </span>
      </header>
      {rows.length === 0 ? (
        <p className="px-4 py-6 text-center text-xs text-muted-foreground">
          No unpitched loads in inventory
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {rows.map((load, idx) => {
            const { origin, destination } = lane(load);
            return (
              <li
                key={load.load_id ?? `load-${idx}`}
                className={cn(
                  "group relative flex flex-col gap-1.5 border-l-2 border-l-transparent",
                  "px-4 py-3 transition-colors hover:border-l-primary/60 hover:bg-muted/30",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="flex items-center gap-1.5 truncate font-mono text-xs font-medium">
                      <span className="truncate">{origin}</span>
                      <ArrowRight
                        aria-hidden
                        className="h-3 w-3 shrink-0 text-primary"
                      />
                      <span className="truncate">{destination}</span>
                    </p>
                  </div>
                  <p className="shrink-0 font-mono text-sm font-semibold tabular-nums">
                    {fmtCurrency(load.loadboard_rate)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-muted-foreground">
                  {load.equipment_type ? <span>{load.equipment_type}</span> : null}
                  {load.miles !== null && load.miles !== undefined ? (
                    <span className="tabular-nums">
                      {fmtNumber(load.miles)} mi
                    </span>
                  ) : null}
                  {load.commodity_type ? <span>{load.commodity_type}</span> : null}
                  <span
                    className={cn(
                      "ml-auto inline-flex items-center gap-1 rounded-full",
                      "bg-success/15 px-2 py-0.5 text-[10px] font-medium",
                      "uppercase tracking-wider text-success",
                    )}
                  >
                    <span
                      aria-hidden
                      className="h-1 w-1 rounded-full bg-success"
                    />
                    Available now
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
