// Compact "flagged" headline widget for the narrow Quality reactive column.
// Big count + "CHS < 70" subtitle. The drilldown table lives separately in
// FlaggedDrilldown so the wide column can host it.

import type { CallRecord } from "@/types/api-types";
import { Card, CardContent } from "@/components/ui/card";

const PASS_THRESHOLD = 70;

export function FlaggedHeadline({ calls }: { calls: CallRecord[] }) {
  const flaggedCount = calls.reduce((acc, c) => {
    const v = c.case_health_score;
    if (v !== null && v !== undefined && v < PASS_THRESHOLD) return acc + 1;
    return acc;
  }, 0);

  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          flagged
        </p>
        <p className="mt-1 text-5xl font-bold tabular-nums tracking-tight">
          {flaggedCount}
        </p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          CHS &lt; {PASS_THRESHOLD}
        </p>
      </CardContent>
    </Card>
  );
}
