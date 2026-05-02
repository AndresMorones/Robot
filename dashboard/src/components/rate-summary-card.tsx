// Booked-rate KPI card with a delta line (vs listed).
// Sign convention (locked 2026-05-01): negative dollars = below list = margin
// captured (good, success). Positive = above list = concession given (bad,
// destructive). Sign is preserved in the rendered text so the user reads the
// raw economics, not an absolute magnitude.

import { Card } from "@/components/ui/card";
import { fmtCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { EconomicsMetrics } from "@/types/api-types";

export function RateSummaryCard({ economics }: { economics: EconomicsMetrics }) {
  const deltaPerLoad = economics.effective_delta_dollars;
  const pct = economics.effective_delta_pct;
  const totalDelta =
    deltaPerLoad !== null
      ? deltaPerLoad * economics.total_calls_with_rate
      : null;

  const showDelta = pct !== null && totalDelta !== null;
  const tone =
    !showDelta || totalDelta === 0
      ? "text-muted-foreground"
      : (totalDelta as number) < 0
        ? "text-success"
        : "text-destructive";

  return (
    <Card className="px-3 py-2 leading-tight">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Rate (avg) · Booked
      </p>
      <p className="text-lg font-semibold tabular-nums tracking-tight">
        {fmtCurrency(economics.avg_agreed_rate)}
      </p>
      {showDelta ? (
        <p className={cn("text-[10px] tabular-nums", tone)}>
          {pct > 0 ? "+" : ""}
          {pct.toFixed(1)}% vs listed · {totalDelta > 0 ? "+" : ""}
          {fmtCurrency(totalDelta)}
        </p>
      ) : null}
    </Card>
  );
}
