import { cn } from "@/lib/utils";

// Sigma Spreadsheet KPI cell — one frozen merged-style spreadsheet cell.
// Renders as a flex column: tiny mono uppercase label, large mono numeric
// value, in-cell horizontal data bar at the bottom.
//
// The data bar is an overlay rendered via `::before` analogue (here a sibling
// absolute div) so it can sit *behind* the value text. Color flips on `pos`
// (true = success / green, false = destructive / red). `bar` is a 0..1
// magnitude; clamp at the call site before passing in.
//
// Cell background tint (CHS scale) is opt-in via `bgTone` — applied only on
// the CHS cell. All other cells inherit the band's transparent bg.

type Tone = "good" | "warn" | "bad" | null;

export type SigmaKpiCellProps = {
  label: string;
  value: string;
  // 0..1 magnitude for the bar. Clamp at the call site.
  bar: number;
  // true = green/positive, false = red/negative trend.
  pos: boolean;
  // Optional CHS-style cell-bg tint (applied at 14% opacity).
  bgTone?: Tone;
  // Optional sub-hint shown muted under the value (e.g. "/100 · ≥70 passes").
  hint?: string;
  // Last cell in the row drops the right border.
  isLast?: boolean;
  // Mobile: at sm breakpoint we wrap to 2 rows of 3. The 3rd cell of row 1
  // (index 2) should also drop its right border on mobile only.
  isMobileRowEnd?: boolean;
};

const TONE_BG: Record<Exclude<Tone, null>, string> = {
  bad: "bg-destructive/[0.14]",
  warn: "bg-warning/[0.14]",
  good: "bg-success/[0.14]",
};

export function SigmaKpiCell({
  label,
  value,
  bar,
  pos,
  bgTone,
  hint,
  isLast,
  isMobileRowEnd,
}: SigmaKpiCellProps): React.JSX.Element {
  const clamped = Math.max(0, Math.min(1, bar));
  const barColor = pos ? "bg-success/60" : "bg-destructive/60";
  const tintClass = bgTone ? TONE_BG[bgTone] : "";

  return (
    <div
      className={cn(
        "relative flex h-full min-h-[88px] flex-col justify-between px-3 py-2.5",
        // Cell gridline — right border on every cell except the last in the row.
        !isLast && "border-r border-border",
        // Mobile: cell 3 wraps to row 1 end; drop its right border at <sm.
        isMobileRowEnd && "sm:border-r sm:border-border",
        isMobileRowEnd && "max-sm:border-r-0",
        tintClass,
      )}
    >
      <div className="font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
        {label}
      </div>
      <div className="font-mono text-[26px] font-semibold leading-none tabular-nums tracking-tight">
        {value}
      </div>
      {hint && (
        <div className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground/80">
          {hint}
        </div>
      )}
      {/* In-cell horizontal data bar — pinned to the bottom. Track is the
          cell's natural background; fill width = clamped magnitude. */}
      <div className="mt-1 h-1 w-full overflow-hidden rounded-[1px] bg-border/40">
        <div
          className={cn("h-full transition-[width] duration-200", barColor)}
          style={{ width: `${(clamped * 100).toFixed(1)}%` }}
        />
      </div>
    </div>
  );
}
