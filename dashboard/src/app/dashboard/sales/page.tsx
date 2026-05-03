import { PipelineBoard } from "@/components/sales-pipeline/pipeline-board";
import { getRecentBookings, parseFilterParams } from "@/lib/api-client";

// ADR-007: 30s ISR. Webhook+SSE drives push freshness on top (ADR-009).
export const revalidate = 30;

type Props = { searchParams: Promise<{ from?: string; to?: string }> };

export default async function SalesPage({ searchParams }: Props) {
  const sp = await searchParams;
  // Default 7-day window comes from `parseFilterParams` — unified across
  // every page in the app (locked 2026-05-02). The Telemetry tab is the
  // only exception and uses its own range chip.
  const filters = parseFilterParams(sp);

  const bookingsRes = await getRecentBookings(filters);

  return (
    <div className="space-y-4">
      <PipelineBoard bookings={bookingsRes.bookings} />
    </div>
  );
}
