// Calls stacked by outcome — Forest/Navy/Clay/Slate (locked palette #1,
// matches OutcomeStackedBar). Total count rendered ABOVE each bar in
// emphasized typography (per user lock 2026-05-01).
//
// Bucket width is set upstream by `bucketGranularity(filters.from, filters.to)`
// — bars are daily / weekly / monthly depending on the active window. Tick
// thinning below keeps the x-axis legible regardless of bucket count.

import type { DailyOutcomeBucket } from "@/lib/daily-buckets";

const COLORS = {
  load_booked: "#15803d",
  no_match: "#1e3a8a",
  carrier_not_qualified: "#92400e",
  call_abandoned: "#4b5563",
} as const;

const ORDER = [
  "load_booked",
  "no_match",
  "carrier_not_qualified",
  "call_abandoned",
] as const;

const LABELS: Record<(typeof ORDER)[number], string> = {
  load_booked: "Booked",
  no_match: "No match",
  carrier_not_qualified: "Not qualified",
  call_abandoned: "Abandoned",
};

const GRID = "#1f1f24";

// Minimum width per bucket — when the window has so many buckets that this
// minimum overflows the container, the chart becomes horizontally scrollable
// so daily granularity stays readable instead of getting squeezed/skipped.
const MIN_SLOT_W = 36;

export function CallsPerDayStacked({
  buckets,
  height = 260,
}: {
  buckets: DailyOutcomeBucket[];
  height?: number;
}) {
  if (!buckets.length || buckets.every((b) => b.total === 0)) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
        style={{ height }}
      >
        No calls in the selected window.
      </div>
    );
  }

  const max = Math.max(...buckets.map((b) => b.total), 1);
  const padL = 40;
  const padR = 12;
  const padT = 28; // extra room for the big number above each bar
  const padB = 28;
  const baseW = 700;
  const minInnerW = buckets.length * MIN_SLOT_W;
  const W = Math.max(baseW, padL + padR + minInnerW);
  const H = height;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const slotW = innerW / buckets.length;
  const barW = Math.min(slotW * 0.62, 36);

  const yTicks = 4;
  const tickStep = max / yTicks;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width={W > baseW ? W : "100%"}
        height={H}
        preserveAspectRatio="none"
        role="img"
        aria-label="Calls per day, stacked by outcome"
      >
        {/* gridlines */}
        {Array.from({ length: yTicks + 1 }).map((_, i) => {
          const v = i * tickStep;
          const y = padT + innerH - (v / max) * innerH;
          return (
            <g key={i}>
              <line
                x1={padL}
                x2={W - padR}
                y1={y}
                y2={y}
                stroke={GRID}
                strokeDasharray="3 3"
              />
              <text
                x={padL - 6}
                y={y + 3}
                textAnchor="end"
                fontSize="10"
                fill="currentColor"
                opacity="0.55"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {Math.round(v)}
              </text>
            </g>
          );
        })}

        {/* stacked bars */}
        {buckets.map((b, i) => {
          const cx = padL + slotW * i + slotW / 2;
          const stackTop = padT + innerH - (b.total / max) * innerH;
          let yOffset = padT + innerH;
          return (
            <g key={b.d}>
              {ORDER.map((key) => {
                const n = b[key] ?? 0;
                if (n === 0) return null;
                const segH = (n / max) * innerH;
                yOffset -= segH;
                return (
                  <rect
                    key={key}
                    x={cx - barW / 2}
                    y={yOffset}
                    width={barW}
                    height={segH}
                    fill={COLORS[key]}
                  >
                    <title>{`${b.label} · ${LABELS[key]}: ${n}`}</title>
                  </rect>
                );
              })}
              {/* BIG total label above bar */}
              {b.total > 0 ? (
                <text
                  x={cx}
                  y={stackTop - 8}
                  textAnchor="middle"
                  fontSize="14"
                  fontWeight="700"
                  fill="currentColor"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {b.total}
                </text>
              ) : null}
              {/* X-axis label — every bucket gets one (chart is scrollable when dense) */}
              <text
                x={cx}
                y={H - 10}
                textAnchor="middle"
                fontSize="10"
                fill="currentColor"
                opacity="0.55"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {b.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        {ORDER.map((key) => (
          <span key={key} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: COLORS[key] }}
            />
            {LABELS[key]}
          </span>
        ))}
      </div>
    </div>
  );
}
