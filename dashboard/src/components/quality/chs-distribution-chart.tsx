"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// CHS distribution histogram — 5 buckets (0-20, 20-40, 40-60, 60-80, 80-100).
// Bars below the 70 pass threshold render in destructive red; the rest in
// success green so the eye lands on failure clusters first.

const BUCKETS = ["0-20", "20-40", "40-60", "60-80", "80-100"] as const;

function bucketColor(label: string): string {
  // 0-20, 20-40, 40-60 are below pass (70); 60-80 straddles; 80-100 = goal
  if (label === "80-100") return "hsl(142 71% 45%)";
  if (label === "60-80") return "hsl(38 92% 50%)";
  return "hsl(0 72% 51%)";
}

export function ChsDistributionChart({
  distribution,
  height = 240,
}: {
  distribution: Record<string, number>;
  height?: number;
}) {
  const data = BUCKETS.map((b) => ({ bucket: b, count: distribution[b] ?? 0 }));
  const hasData = data.some((d) => d.count > 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">CHS distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div
            className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
            style={{ height }}
          >
            No CHS samples in the selected window.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis
                dataKey="bucket"
                tick={{ fontSize: 11 }}
                stroke="currentColor"
                strokeOpacity={0.4}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11 }}
                stroke="currentColor"
                strokeOpacity={0.4}
                width={36}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted) / 0.3)" }}
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {data.map((d) => (
                  <Cell key={d.bucket} fill={bucketColor(d.bucket)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
