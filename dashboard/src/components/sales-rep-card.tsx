import Link from "next/link";
import { ArrowRight, MapPin, Truck } from "lucide-react";

import { fmtCurrency, fmtNumber, fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RecentBooking } from "@/types/api-types";

// Creative card for the "New Bookings" sales-rep view. Deliberately departs
// from the standard shadcn Card primitive used everywhere else on the
// dashboard so a sales rep glances at the page and immediately sees
// "delivery received" energy rather than "another KPI tile".
//
// Hybrid inspiration:
//   - Linear issue card     -> vertical accent bar, status pill, hover lift
//   - Stripe payment row    -> right-aligned mono amount, time-ago subtitle
//   - iOS notification      -> bold top line + muted secondary line
//   - Salesforce Lightning  -> horizontal multi-zone with ghost-button footer
//
// Built as a plain <article> + Tailwind, NOT <Card> from shadcn, so the
// border-radius, gradient, shadow and accent bar are unique to this surface.

function lane(
  oc: string | null | undefined,
  os: string | null | undefined,
  dc: string | null | undefined,
  ds: string | null | undefined,
): { origin: string; destination: string } {
  const origin = [oc, os].filter(Boolean).join(", ") || "—";
  const destination = [dc, ds].filter(Boolean).join(", ") || "—";
  return { origin, destination };
}

export function SalesRepCard({
  booking,
}: {
  booking: RecentBooking;
}): React.JSX.Element {
  const list = booking.load?.loadboard_rate ?? null;
  const apply = booking.apply_rate ?? null;
  const dollarDelta = apply !== null && list !== null ? apply - list : null;
  // Sign convention (T-6): negative dollarDelta = booked below list = margin
  // captured (good). Positive = booked above list = concession given (bad).
  // Matches EconomicsCards + EffectiveDeltaChart canonical framing.
  const marginCaptured = dollarDelta !== null && dollarDelta <= 0;
  const { origin, destination } = lane(
    booking.load?.origin_city,
    booking.load?.origin_state,
    booking.load?.destination_city,
    booking.load?.destination_state,
  );

  // Accent-bar tone — emerald=margin captured (booked at/below list, happy),
  // amber=concession given (booked above list), primary=no list for compare.
  const accent =
    dollarDelta === null
      ? "bg-primary"
      : marginCaptured
        ? "bg-success"
        : "bg-warning";

  const callOutcome = booking.call?.call_outcome ?? null;
  const sentiment = booking.call?.sentiment ?? null;

  return (
    <article
      className={cn(
        "group relative overflow-hidden rounded-xl border border-border",
        "bg-gradient-to-br from-card via-card to-card/60",
        "shadow-sm transition-all duration-200",
        "hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg",
      )}
    >
      {/* Vertical accent bar — left edge, full height. */}
      <div
        aria-hidden
        className={cn("absolute left-0 top-0 h-full w-1", accent)}
      />

      <div className="flex flex-col gap-3 pl-5 pr-4 py-4">
        {/* Top row — carrier wordmark on left, booked rate on right. */}
        <header className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex h-1.5 w-1.5 rounded-full",
                  accent,
                  // Subtle pulse for the freshest entries (under 5 min) — not
                  // mission-critical, just a touch of life on the page.
                  Date.now() - new Date(booking.booked_at).getTime() <
                    5 * 60_000
                    ? "animate-pulse motion-reduce:animate-none"
                    : "",
                )}
              />
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                New booking
              </span>
            </div>
            <h3 className="truncate text-base font-semibold leading-tight tracking-tight">
              MC{" "}
              <span className="font-mono text-foreground">
                {booking.mc_number}
              </span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Booked {fmtRelative(booking.booked_at)}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p
              className={cn(
                "font-mono text-2xl font-semibold leading-none tabular-nums",
                "tracking-tight",
              )}
            >
              {fmtCurrency(apply)}
            </p>
            {list !== null ? (
              <p className="mt-1 text-[11px] text-muted-foreground">
                List {fmtCurrency(list)}
              </p>
            ) : null}
            {dollarDelta !== null ? (
              <p
                className={cn(
                  "mt-0.5 text-[11px] font-medium tabular-nums",
                  marginCaptured ? "text-success" : "text-destructive",
                )}
              >
                {dollarDelta > 0 ? "+" : ""}
                {fmtCurrency(dollarDelta)} vs list
              </p>
            ) : null}
          </div>
        </header>

        {/* Lane row — origin ➝ destination, mono. */}
        <div className="flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2">
          <MapPin
            aria-hidden
            className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
          />
          <span className="truncate font-mono text-sm font-medium">
            {origin}
          </span>
          <ArrowRight
            aria-hidden
            className="h-3.5 w-3.5 shrink-0 text-primary"
          />
          <span className="truncate font-mono text-sm font-medium">
            {destination}
          </span>
        </div>

        {/* Equipment + miles + commodity in a single muted line. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {booking.load?.equipment_type ? (
            <span className="inline-flex items-center gap-1">
              <Truck aria-hidden className="h-3 w-3" />
              {booking.load.equipment_type}
            </span>
          ) : null}
          {booking.load?.miles !== null && booking.load?.miles !== undefined ? (
            <span className="tabular-nums">
              {fmtNumber(booking.load.miles)} mi
            </span>
          ) : null}
          {booking.load?.commodity_type ? (
            <span>{booking.load.commodity_type}</span>
          ) : null}
          {sentiment ? (
            <span
              className={cn(
                "ml-auto rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                sentiment === "positive"
                  ? "bg-success/15 text-success"
                  : sentiment === "negative"
                    ? "bg-destructive/15 text-destructive"
                    : "bg-info/15 text-info",
              )}
            >
              {sentiment}
            </span>
          ) : null}
        </div>

        {/* Footer ghost actions — link to the call detail and the carrier. */}
        <footer className="flex items-center gap-2 border-t border-border/70 pt-3">
          <Link
            href={`/dashboard/calls/${encodeURIComponent(booking.call_id)}`}
            className={cn(
              "inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs",
              "text-muted-foreground transition-colors",
              "hover:bg-secondary hover:text-foreground",
            )}
          >
            View call
            <ArrowRight aria-hidden className="h-3 w-3" />
          </Link>
          {callOutcome ? (
            <span className="ml-auto text-[10px] uppercase tracking-wider text-muted-foreground">
              {callOutcome.replace(/_/g, " ")}
            </span>
          ) : null}
        </footer>
      </div>
    </article>
  );
}
