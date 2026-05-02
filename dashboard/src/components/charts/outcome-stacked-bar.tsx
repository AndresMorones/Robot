// Single-row 100% stacked bar — Booked / No match / N/Q / Abandoned.
// Locked 2026-04-30 (palette #1, "Booked emphasized"):
//   Booked        — Forest  #15803d  (with larger label + %)
//   No match      — Navy    #1e3a8a
//   N/Q           — Clay    #92400e
//   Abandoned     — Slate   #4b5563
// Each segment shows its own % inside; Booked's typography is sized up so it
// reads as the headline outcome regardless of width.

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

// Twin can return either canonical outcome names ("load_booked") or
// colloquial aliases ("booked"). Merge each alias into its canonical bucket
// so neither variant is dropped from the bar.
const ALIASES: Record<string, (typeof ORDER)[number]> = {
  booked: "load_booked",
  abandoned: "call_abandoned",
  fmcsa_declined: "carrier_not_qualified",
  not_qualified: "carrier_not_qualified",
};

export function OutcomeStackedBar({
  byOutcome,
  emptyMessage,
}: {
  byOutcome: Record<string, number>;
  emptyMessage?: string;
}) {
  const merged: Record<(typeof ORDER)[number], number> = {
    load_booked: 0,
    no_match: 0,
    carrier_not_qualified: 0,
    call_abandoned: 0,
  };
  for (const [k, v] of Object.entries(byOutcome)) {
    const canonical = (ORDER as readonly string[]).includes(k)
      ? (k as (typeof ORDER)[number])
      : ALIASES[k];
    if (canonical) merged[canonical] += v ?? 0;
  }
  const counts = ORDER.map((k) => ({ key: k, n: merged[k] }));
  const total = counts.reduce((acc, d) => acc + d.n, 0);

  if (!total) {
    return (
      <div className="flex h-16 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
        {emptyMessage ?? "No calls in the selected window."}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex h-16 overflow-hidden rounded-md border border-border">
        {counts.map((d) => {
          if (d.n === 0) return null;
          const pct = (d.n / total) * 100;
          const isBooked = d.key === "load_booked";
          return (
            <div
              key={d.key}
              className="flex flex-col items-center justify-center text-white"
              style={{ flex: pct, background: COLORS[d.key] }}
              title={`${LABELS[d.key]}: ${d.n} (${pct.toFixed(1)}%)`}
            >
              <span
                className={
                  isBooked
                    ? "text-xl font-bold tabular-nums leading-none"
                    : "text-sm font-semibold tabular-nums leading-none"
                }
              >
                {pct.toFixed(1)}%
              </span>
              <span
                className={
                  isBooked
                    ? "mt-1 text-[11px] font-semibold uppercase tracking-wider"
                    : "mt-1 text-[9px] uppercase tracking-wider opacity-90"
                }
              >
                {LABELS[d.key]}
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        {counts.map((d) => (
          <span key={d.key} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: COLORS[d.key] }}
            />
            {LABELS[d.key]} · <span className="tabular-nums">{d.n}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
