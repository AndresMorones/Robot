import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CallsSourceBadge } from "@/components/calls-table";
import { CallsListWithFilters } from "@/components/calls-filters/calls-list-with-filters";
import { SigmaKpiBand } from "@/components/sigma-kpi-band/sigma-kpi-band";
import {
  getCalls,
  getEconomics,
  getFunnel,
  getOperational,
  getQuality,
  parseFilterParams,
  type DashboardFilters,
} from "@/lib/api-client";

// Force fully-dynamic rendering. The calls list must feel "live" — soft-nav
// from another route (via <Link>) was reusing cached HTML and showing empty/
// stale data until a hard refresh. Going dynamic guarantees every visit
// produces a fresh server-render. The underlying fetch also opts out of the
// Next.js Data Cache via `cache: "no-store"` in `getCalls`.
export const dynamic = "force-dynamic";
export const revalidate = 0;

type Props = {
  searchParams: Promise<{
    from?: string;
    to?: string;
    outcome?: string;
    sentiment?: string;
    mc?: string;
  }>;
};

// Server forwards the global `from`/`to` URL params to FastAPI so the date
// picker actually narrows the row set. Outcome / sentiment / MC stay
// client-side (no API support for those server-side yet) — `CallsListWithFilters`
// reads them from the same URL and applies them in-browser over the
// server-filtered payload.
export default async function CallsPage({ searchParams }: Props) {
  const sp = await searchParams;
  const filters: DashboardFilters = parseFilterParams(sp);

  // Sigma KPI band (top of tab) needs aggregate metrics. Fetched in parallel
  // alongside the calls list so the page renders in a single round-trip.
  // `getCalls` is the only no-store fetch; the dashboard endpoints share the
  // 30s revalidate window per `lib/api-client`.
  const [{ calls, source }, funnel, economics, operational, quality] =
    await Promise.all([
      getCalls(200, filters),
      getFunnel(filters),
      getEconomics(filters),
      getOperational(filters),
      getQuality(filters),
    ]);

  return (
    <div className="space-y-6">
      <SigmaKpiBand
        funnel={funnel}
        economics={economics}
        operational={operational}
        quality={quality}
      />
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center text-sm">
            Call log
            <CallsSourceBadge source={source} />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CallsListWithFilters calls={calls} />
        </CardContent>
      </Card>
    </div>
  );
}
