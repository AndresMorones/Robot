"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtNumber } from "@/lib/format";
import type {
  TelemetryRpmPoint,
  TelemetryTpmPoint,
} from "@/types/api-types";

// Stacked RPM / TPM area pair on a single Card. Shared x-axis is implicit:
// both series come bucketed at the same `bucket_minutes` window so the time
// columns line up by index. Bloomberg Pit accent palette: cyan = throughput,
// amber = volume.

const RPM_COLOR = "#22D3EE";
const TPM_COLOR = "#F4A24C";

function fmtTime(t: string): string {
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return t;
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

type AreaDatum = { t: string; [k: string]: string | number };

// TR-7 — static thresholds rendered as Recharts <ReferenceLine>. Tunable
// later via /v1/policy/defaults; hardcoded for MVP.
const RPM_WARNING = 100;
const TPM_WARNING = 50_000;

function MiniArea({
  data,
  dataKey,
  color,
  label,
  gradientId,
  warningThreshold,
}: {
  data: AreaDatum[];
  dataKey: string;
  color: string;
  label: string;
  gradientId: string;
  warningThreshold?: number;
}) {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 0, left: 8 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            stroke="hsl(var(--border))"
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="t"
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            tickFormatter={fmtTime}
            tickMargin={4}
          />
          <YAxis
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            tickFormatter={(v: number) => fmtNumber(v)}
            width={40}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 4,
              fontSize: 11,
              fontFamily: "var(--font-mono, ui-monospace)",
            }}
            labelFormatter={(t: string) => fmtTime(t)}
            formatter={(v) => [fmtNumber(typeof v === "number" ? v : 0), label]}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
          />
          {warningThreshold !== undefined ? (
            <ReferenceLine
              y={warningThreshold}
              stroke="#F5A524"
              strokeDasharray="2 4"
              strokeWidth={1}
              label={{
                value: `warn ≥ ${fmtNumber(warningThreshold)}`,
                position: "insideTopRight",
                fill: "#F5A524",
                fontSize: 9,
              }}
            />
          ) : null}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export type RpmTpmChartProps = {
  rpm: TelemetryRpmPoint[];
  tpm: TelemetryTpmPoint[];
};

export function RpmTpmChart({ rpm, tpm }: RpmTpmChartProps) {
  const hasRpm = rpm.length > 0;
  const hasTpm = tpm.length > 0;
  const empty = !hasRpm && !hasTpm;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="font-mono text-xs uppercase tracking-wider">
          Runs & tokens per minute
        </CardTitle>
        <p className="text-[11px] text-muted-foreground">
          Top: requests/min. Bottom: tokens/min. Shared time axis.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {empty ? (
          <div className="flex h-[200px] items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
            No runs in window.
          </div>
        ) : (
          <>
            <div>
              <div className="mb-1 flex items-center gap-2 px-1">
                <span
                  className="inline-block h-2 w-2 rounded-sm"
                  style={{ background: RPM_COLOR }}
                  aria-hidden
                />
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  RPM
                </span>
              </div>
              <MiniArea
                data={rpm}
                dataKey="rpm"
                color={RPM_COLOR}
                label="rpm"
                gradientId="tel-rpm-fill"
                warningThreshold={RPM_WARNING}
              />
            </div>
            <div>
              <div className="mb-1 flex items-center gap-2 px-1">
                <span
                  className="inline-block h-2 w-2 rounded-sm"
                  style={{ background: TPM_COLOR }}
                  aria-hidden
                />
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  TPM
                </span>
              </div>
              <MiniArea
                data={tpm}
                dataKey="tpm"
                color={TPM_COLOR}
                label="tpm"
                gradientId="tel-tpm-fill"
                warningThreshold={TPM_WARNING}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
