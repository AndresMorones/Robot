import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtNumber } from "@/lib/format";
import type { CallRecord, TelemetryAggregate } from "@/types/api-types";

// Quadrant #1 of the Pit composite — token-spend trend split into input vs
// output. The aggregate `tpm_series` only carries combined totals, so the
// per-bucket time chart for input/output is parked behind a backend split.
// What we CAN show today: total token volume in window, split into the four
// observable role-families:
//   - Conversation: agent_input + agent_output + tool_input + tool_output
//     (combined sum recovered from tpm_series; per-call splits exist via
//     /v1/calls/{id}/timeline summary but aren't fan-out cheap on aggregate)
//   - Post-call processing: extract_*_tokens + chs_*_tokens (per-row on
//     CallRecord — input vs output IS available here)
// Render: horizontal segmented bars per category. Combined Conversation sits
// on top with a note that the input/output split is upstream-blocked; Extract
// + CHS show a real input/output split that operators can act on.

const COLORS = {
  conv: "#22D3EE",
  extract_in: "#FFB800",
  extract_out: "#F4A24C",
  chs_in: "#34D399",
  chs_out: "#10B981",
};

type Category = {
  key: string;
  label: string;
  total: number;
  segments: { label: string; value: number; color: string }[];
};

function sumNullable(values: Array<number | null | undefined>): number {
  let total = 0;
  for (const v of values) if (typeof v === "number") total += v;
  return total;
}

function conversationTotalFromTpm(tpm: TelemetryAggregate["tpm_series"], bucketMinutes: number): number {
  // tpm_series carries per-minute rate (aggregator divides bucket sum by
  // bucket_minutes). Recover the total by multiplying back.
  let total = 0;
  for (const p of tpm) total += p.tpm * bucketMinutes;
  return Math.round(total);
}

function Segment({ value, total, color }: { value: number; total: number; color: string }) {
  if (value <= 0 || total <= 0) return null;
  const pct = (value / total) * 100;
  return <span className="block h-full" style={{ width: `${pct}%`, background: color }} />;
}

export function TokenSpendTrendCard({
  telemetry,
  calls,
}: {
  telemetry: TelemetryAggregate;
  calls: CallRecord[];
}) {
  const bucketMin = telemetry.window.bucket_minutes || 1;
  const conversation = conversationTotalFromTpm(telemetry.tpm_series, bucketMin);
  const extractIn = sumNullable(calls.map((c) => c.extract_input_tokens));
  const extractOut = sumNullable(calls.map((c) => c.extract_output_tokens));
  const chsIn = sumNullable(calls.map((c) => c.chs_input_tokens));
  const chsOut = sumNullable(calls.map((c) => c.chs_output_tokens));

  const categories: Category[] = [
    {
      key: "conv",
      label: "Conversation (combined)",
      total: conversation,
      segments: [
        { label: "all roles", value: conversation, color: COLORS.conv },
      ],
    },
    {
      key: "extract",
      label: "Extract Call Details",
      total: extractIn + extractOut,
      segments: [
        { label: "input", value: extractIn, color: COLORS.extract_in },
        { label: "output", value: extractOut, color: COLORS.extract_out },
      ],
    },
    {
      key: "chs",
      label: "Case Health Score",
      total: chsIn + chsOut,
      segments: [
        { label: "input", value: chsIn, color: COLORS.chs_in },
        { label: "output", value: chsOut, color: COLORS.chs_out },
      ],
    },
  ];

  const grandMax = Math.max(...categories.map((c) => c.total), 1);
  const empty = categories.every((c) => c.total === 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="font-mono text-xs uppercase tracking-wider text-primary">
          Token spend · input / output split
        </CardTitle>
        <p className="text-[11px] text-muted-foreground">
          Window totals by role-family. Conversation is combined (per-bucket
          split needs backend role-tagged TPM).
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {empty ? (
          <div className="flex h-[120px] items-center justify-center border border-dashed border-border text-sm text-muted-foreground">
            No token activity in window.
          </div>
        ) : (
          categories.map((cat) => {
            const widthPct = (cat.total / grandMax) * 100;
            return (
              <div key={cat.key} className="space-y-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                    {cat.label}
                  </span>
                  <span className="font-mono text-[11px] tabular-nums">
                    {fmtNumber(cat.total)} tok
                  </span>
                </div>
                <div className="h-3 w-full border border-border bg-background/40">
                  <div
                    className="flex h-full"
                    style={{ width: `${Math.max(widthPct, 1)}%` }}
                  >
                    {cat.segments.map((s) => (
                      <Segment
                        key={s.label}
                        value={s.value}
                        total={cat.total}
                        color={s.color}
                      />
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                  {cat.segments.map((s) => (
                    <span
                      key={s.label}
                      className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground"
                    >
                      <span
                        className="inline-block h-2 w-2"
                        style={{ background: s.color }}
                        aria-hidden
                      />
                      {s.label} {fmtNumber(s.value)}
                    </span>
                  ))}
                </div>
              </div>
            );
          })
        )}
        <div className="text-[10.5px] text-muted-foreground">
          {fmtNumber(calls.length)} call{calls.length === 1 ? "" : "s"} in window ·
          conversation total recovered from tpm_series × bucket_minutes
        </div>
      </CardContent>
    </Card>
  );
}
