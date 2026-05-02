// Server-side pre-bucketed CHS distribution (5 buckets of width 20).
// Source: GET /v1/dashboard/quality → QualityMetrics.chs_distribution.
// Distinct from RatingDistribution (which re-buckets per-call CHS into the
// pass/goal 0-70/70-85/85-100 scheme). This widget renders the API's raw
// 0-20/20-40/40-60/60-80/80-100 histogram.

import { Card, CardContent } from "@/components/ui/card";

const BUCKETS = ["0-20", "20-40", "40-60", "60-80", "80-100"] as const;

const LABELS: Record<(typeof BUCKETS)[number], string> = {
  "0-20": "0–20",
  "20-40": "20–40",
  "40-60": "40–60",
  "60-80": "60–80",
  "80-100": "80–100",
};

// Color ramp: under 60 brick red, 60-80 amber-rust, 80-100 forest.
// Mirrors the broader CHS quality semantic used elsewhere in the dashboard.
const COLORS: Record<(typeof BUCKETS)[number], string> = {
  "0-20": "#b91c1c",
  "20-40": "#b91c1c",
  "40-60": "#b91c1c",
  "60-80": "#b45309",
  "80-100": "#15803d",
};

export function ChsDistributionMini({
  buckets,
}: {
  buckets: Record<string, number> | null;
}) {
  const counts = BUCKETS.map((k) => buckets?.[k] ?? 0);
  const total = counts.reduce((a, b) => a + b, 0);
  const max = Math.max(...counts);

  return (
    <Card>
      <CardContent className="p-3">
        <div className="mb-3 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Quality score distribution (5-bucket)
        </div>

        {total === 0 ? (
          <div className="flex h-16 items-center justify-center text-xs text-muted-foreground">
            No CHS data
          </div>
        ) : (
          <div className="space-y-2">
            {BUCKETS.map((k, i) => {
              const n = counts[i];
              const barPct = max > 0 ? (n / max) * 100 : 0;
              return (
                <div
                  key={k}
                  className="flex items-center gap-3"
                >
                  <span className="w-14 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground tabular-nums">
                    {LABELS[k]}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-sm bg-muted">
                    <div
                      className="h-full rounded-sm transition-[width]"
                      style={{
                        width: `${barPct}%`,
                        background: COLORS[k],
                      }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right text-xs font-medium tabular-nums">
                    {n}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
