import { ActiveCallsMini } from "@/components/active-calls-mini";
import { AvailableLoadsList } from "@/components/available-loads-list";
import { KpiCard } from "@/components/kpi-card";
import { SalesRepCard } from "@/components/sales-rep-card";
import {
  getAvailableLoads,
  getRecentBookings,
  parseFilterParams,
  type DashboardFilters,
} from "@/lib/api-client";
import { fmtCurrency, fmtNumber } from "@/lib/format";

// 5-min ISR fallback; webhook+SSE still drives push freshness on this route
// the same way the other dashboard pages do (ADR-009).
export const dynamic = "force-dynamic";
export const revalidate = 0;

type Props = { searchParams: Promise<{ from?: string; to?: string }> };

// Default rolling-30-day window when the global date filter isn't engaged.
// Wider than 24h so demo data + slower call cadences both surface; user can
// narrow via the global date picker.
const DEFAULT_WINDOW_MS = 30 * 24 * 60 * 60 * 1000;

export default async function SalesPage({ searchParams }: Props) {
  const sp = await searchParams;
  // `parseFilterParams` handles the YYYY-MM-DD → inclusive UTC bounds fix; we
  // then fall back to a rolling-24h `from` only when neither bound is set.
  const parsed = parseFilterParams(sp);
  const filters: DashboardFilters = {
    from:
      parsed.from ??
      (parsed.to ? undefined : new Date(Date.now() - DEFAULT_WINDOW_MS)),
    to: parsed.to,
  };

  const [bookingsRes, loadsRes] = await Promise.all([
    getRecentBookings(filters),
    getAvailableLoads(filters),
  ]);

  const totalRevenue = bookingsRes.bookings.reduce(
    (acc, b) => acc + (b.apply_rate ?? 0),
    0,
  );
  // Sign convention (locked 2026-05-01): apply - list, negative = below list
  // = margin captured (good, success). Matches SalesRepCard /
  // EconomicsCards / EffectiveDeltaChart / CallBookingsTable RateDiff.
  const margins = bookingsRes.bookings
    .map((b) => {
      const apply = b.apply_rate;
      const list = b.load?.loadboard_rate ?? null;
      if (apply === null || apply === undefined || list === null) return null;
      return apply - list;
    })
    .filter((d): d is number => d !== null);
  const avgMargin =
    margins.length > 0
      ? margins.reduce((a, b) => a + b, 0) / margins.length
      : null;
  const marginToneClass =
    avgMargin === null || avgMargin === 0
      ? ""
      : avgMargin < 0
        ? "text-success"
        : "text-destructive";

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard
          label="Bookings"
          value={fmtNumber(bookingsRes.count)}
        />
        <KpiCard
          label="Revenue (booked)"
          value={fmtCurrency(totalRevenue)}
        />
        <KpiCard
          label="Avg margin vs list"
          value={
            <span className={marginToneClass}>{fmtCurrency(avgMargin)}</span>
          }
          hint={
            margins.length > 0
              ? `Across ${fmtNumber(margins.length)} priced bookings (negative = below list = captured)`
              : "No priced bookings yet"
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Left column — creative cards, ~60% width on lg+. */}
        <section className="space-y-3 lg:col-span-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              New bookings
            </h2>
            <span className="text-xs text-muted-foreground tabular-nums">
              {fmtNumber(bookingsRes.bookings.length)} shown
            </span>
          </div>
          {bookingsRes.bookings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card/40 p-8 text-center">
              <p className="text-sm text-muted-foreground">
                No bookings in the active window.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Bookings written by HR Twin will surface here as calls finish.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
              {bookingsRes.bookings.map((b) => (
                <SalesRepCard key={b.booking_id} booking={b} />
              ))}
            </div>
          )}
        </section>

        {/* Right column — compact operational panels. */}
        <aside className="space-y-4 lg:col-span-2">
          <ActiveCallsMini />
          <AvailableLoadsList loads={loadsRes.loads} />
        </aside>
      </div>
    </div>
  );
}
