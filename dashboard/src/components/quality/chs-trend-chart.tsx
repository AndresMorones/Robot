// Quality tab — daily mean of case_health_score, rendered as the locked
// "C1 MA Band" variant (review chosen 2026-05-01):
//   • tier-colored scatter points (forest ≥85, amber 70-85, brick <70)
//   • forest 7-day MA spline through the daily means
//   • forest ±1 std-dev band around the spline (12% opacity)
//   • dashed amber/forest threshold lines at 70 and 85 with right-edge labels
//
// Pure SVG — no Recharts. The chart adapts to the active date window via the
// `series` prop (one point per day) and renders empty-state when no data
// lands inside the window.

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type ChsTrendPoint = {
  d: string;
  v: number | null;
  n?: number | null;
};

const PASS = 70;
const GOAL = 85;
const COLOR = {
  ink: "#E6EBF2",
  muted: "#8A93A3",
  forest: "#15803d",
  amber: "#b45309",
  brick: "#b91c1c",
} as const;

function tierColor(v: number): string {
  if (v >= GOAL) return COLOR.forest;
  if (v >= PASS) return COLOR.amber;
  return COLOR.brick;
}

function movingAvg7(xs: Array<number | null>): Array<number | null> {
  const out: Array<number | null> = [];
  for (let i = 0; i < xs.length; i++) {
    const window: number[] = [];
    for (let j = Math.max(0, i - 6); j <= i; j++) {
      const v = xs[j];
      if (typeof v === "number" && !Number.isNaN(v)) window.push(v);
    }
    out.push(window.length ? window.reduce((a, b) => a + b, 0) / window.length : null);
  }
  return out;
}

function movingStd7(xs: Array<number | null>): Array<number | null> {
  const out: Array<number | null> = [];
  for (let i = 0; i < xs.length; i++) {
    const window: number[] = [];
    for (let j = Math.max(0, i - 6); j <= i; j++) {
      const v = xs[j];
      if (typeof v === "number" && !Number.isNaN(v)) window.push(v);
    }
    if (!window.length) {
      out.push(null);
      continue;
    }
    const mean = window.reduce((a, b) => a + b, 0) / window.length;
    const variance = window.reduce((s, v) => s + (v - mean) ** 2, 0) / window.length;
    out.push(Math.sqrt(variance));
  }
  return out;
}

// Catmull-Rom-to-cubic-Bezier smooth path. Skips null gaps by emitting a Move.
function smoothPath(points: Array<{ x: number; y: number } | null>): string {
  let d = "";
  let prev: { x: number; y: number } | null = null;
  let preprev: { x: number; y: number } | null = null;
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    if (!p) {
      prev = null;
      preprev = null;
      continue;
    }
    if (!prev) {
      d += `${d ? " " : ""}M ${p.x.toFixed(2)} ${p.y.toFixed(2)}`;
    } else {
      const next = points[i + 1] ?? p;
      const p0 = preprev ?? prev;
      const p1 = prev;
      const p2 = p;
      const p3 = next;
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
    }
    preprev = prev;
    prev = p;
  }
  return d;
}

export function ChsTrendChart({
  series,
  height = 240,
}: {
  series: ChsTrendPoint[];
  height?: number;
}) {
  const N = series.length;
  const hasData = series.some((p) => p.v !== null && p.v !== undefined);

  if (!hasData || N === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Quality score trend Avg</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
            style={{ height }}
          >
            No quality data in the selected window.
          </div>
        </CardContent>
      </Card>
    );
  }

  // SVG geometry — viewBox stays fixed; SVG scales with container.
  const W = 700;
  const H = height;
  const M = { top: 18, right: 48, bottom: 36, left: 56 };
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const xAt = (i: number) => M.left + (innerW * i) / Math.max(1, N - 1);
  const yAt = (v: number) => M.top + innerH * (1 - v / 100);

  // Treat null AND non-positive values as "no data" — those days are excluded
  // from the moving-average and std-dev windows, and from the scatter render.
  const values: Array<number | null> = series.map((p) =>
    typeof p.v === "number" && p.v > 0 ? p.v : null,
  );
  const ma = movingAvg7(values);
  const sd = movingStd7(values);

  const upper = ma.map((m, i) =>
    m === null || sd[i] === null
      ? null
      : { x: xAt(i), y: yAt(Math.min(100, m + (sd[i] as number))) },
  );
  const lower = ma.map((m, i) =>
    m === null || sd[i] === null
      ? null
      : { x: xAt(i), y: yAt(Math.max(0, m - (sd[i] as number))) },
  );

  // Build the band polygon by walking upper forward and lower in reverse.
  // For simplicity (and to handle nulls), join the contiguous run.
  function buildBandPath(): string {
    const upperPts = upper.filter((p): p is { x: number; y: number } => p !== null);
    const lowerPts = lower.filter((p): p is { x: number; y: number } => p !== null);
    if (upperPts.length < 2 || lowerPts.length < 2) return "";
    const upPath = smoothPath(upperPts);
    const downPath = smoothPath(lowerPts.slice().reverse());
    // smoothPath starts with M; we want to L into the closing leg.
    const downAsLines = downPath.replace(/^M /, "L ");
    return `${upPath} ${downAsLines} Z`;
  }

  const bandD = buildBandPath();
  const maPoints = ma.map((m, i) => (m === null ? null : { x: xAt(i), y: yAt(m) }));
  const maD = smoothPath(maPoints);

  // X-axis tick stride — show ~7 labels max to avoid collision.
  const tickStride = Math.max(1, Math.ceil(N / 7));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">Quality score trend Avg</CardTitle>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          height={H}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Daily mean Quality Score with 7-day moving average and ±1 std-dev band"
        >
          {/* Faint amber graph-paper grid (behind everything) */}
          {Array.from({ length: 11 }).map((_, k) => {
            const v = k * 10;
            const y = yAt(v);
            return (
              <line
                key={`gh-${k}`}
                x1={M.left}
                x2={M.left + innerW}
                y1={y}
                y2={y}
                stroke={COLOR.amber}
                strokeOpacity={0.08}
                strokeWidth={1}
              />
            );
          })}
          {series.map((_, i) => (
            <line
              key={`gv-${i}`}
              x1={xAt(i)}
              x2={xAt(i)}
              y1={M.top}
              y2={M.top + innerH}
              stroke={COLOR.amber}
              strokeOpacity={0.05}
              strokeWidth={1}
            />
          ))}

          {/* ±1 std-dev band */}
          {bandD ? (
            <path d={bandD} fill={COLOR.forest} fillOpacity={0.06} stroke="none" />
          ) : null}

          {/* MA spline */}
          {maD ? (
            <path
              d={maD}
              fill="none"
              stroke={COLOR.forest}
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null}

          {/* Threshold lines */}
          <line
            x1={M.left}
            x2={M.left + innerW}
            y1={yAt(PASS)}
            y2={yAt(PASS)}
            stroke={COLOR.amber}
            strokeWidth={1}
            strokeDasharray="3 3"
          />
          <line
            x1={M.left}
            x2={M.left + innerW}
            y1={yAt(GOAL)}
            y2={yAt(GOAL)}
            stroke={COLOR.forest}
            strokeWidth={1}
            strokeDasharray="3 3"
          />

          {/* Right-edge threshold labels */}
          <text
            x={M.left + innerW + 6}
            y={yAt(PASS) + 6}
            fontSize={12}
            fill={COLOR.amber}
            style={{ fontFamily: "ui-monospace, 'JetBrains Mono', monospace", letterSpacing: "0.06em" }}
          >
            70
          </text>
          <text
            x={M.left + innerW + 6}
            y={yAt(GOAL) + 6}
            fontSize={12}
            fill={COLOR.forest}
            style={{ fontFamily: "ui-monospace, 'JetBrains Mono', monospace", letterSpacing: "0.06em" }}
          >
            85
          </text>

          {/* Daily-mean scatter points — drop null AND zero from the chart */}
          {series.map((p, i) =>
            typeof p.v === "number" && p.v > 0 ? (
              <circle
                key={p.d ?? i}
                cx={xAt(i)}
                cy={yAt(p.v)}
                r={5.2}
                fill={tierColor(p.v)}
                stroke="none"
              />
            ) : null,
          )}

          {/* Y-axis tick labels — 2x bigger */}
          {[0, 25, 50, 75, 100].map((v) => (
            <text
              key={v}
              x={M.left - 8}
              y={yAt(v) + 6}
              textAnchor="end"
              fontSize={12}
              fill={COLOR.muted}
              style={{ fontFamily: "ui-monospace, 'JetBrains Mono', monospace", letterSpacing: "0.06em" }}
            >
              {v}
            </text>
          ))}

          {/* X-axis tick labels (thinned) — 2x bigger */}
          {series.map((p, i) => {
            if (i % tickStride !== 0 && i !== N - 1) return null;
            const dt = new Date(p.d);
            const label = Number.isNaN(dt.getTime())
              ? p.d
              : dt.toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  timeZone: "UTC",
                });
            return (
              <text
                key={`x-${i}`}
                x={xAt(i)}
                y={H - 6}
                textAnchor="middle"
                fontSize={12}
                fill={COLOR.muted}
                style={{
                  fontFamily: "ui-monospace, 'JetBrains Mono', monospace",
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                }}
              >
                {label}
              </text>
            );
          })}
        </svg>
      </CardContent>
    </Card>
  );
}
