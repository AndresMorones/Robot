"use client";

import * as React from "react";

import { CarriersTable } from "@/components/carriers-table";
import type { CarrierRollupRow } from "@/types/api-types";

import { CarrierFiltersBar } from "./carrier-filters-bar";
import { useCarrierFilters, type MarginDirValue } from "./use-carrier-filters";

// Client-side wrapper: takes the full server-fetched carrier rollup and
// applies URL-driven filters before rendering. Filtering all-in-browser is
// fine here — the rollup endpoint returns at most a few dozen rows.

function classifyMargin(pct: number | null | undefined): MarginDirValue {
  if (pct === null || pct === undefined || Number.isNaN(pct)) return "unknown";
  if (pct < 0) return "below_list";
  if (pct > 0) return "above_list";
  return "at_list";
}

function parseNumeric(s: string): number | null {
  const trimmed = s.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

export function CarriersListWithFilters({
  rows,
}: {
  rows: CarrierRollupRow[];
}) {
  const { filters } = useCarrierFilters();

  const filtered = React.useMemo(() => {
    const mcQuery = filters.mc.trim().toLowerCase();
    const nameQuery = filters.name.trim().toLowerCase();
    const minCalls = parseNumeric(filters.minCalls);
    const minRate = parseNumeric(filters.minRate);
    const marginSet = new Set<MarginDirValue>(filters.marginDir);

    return rows.filter((r) => {
      if (mcQuery) {
        const v = (r.mc_number ?? "").toLowerCase();
        if (!v.includes(mcQuery)) return false;
      }

      if (nameQuery) {
        const v = (r.carrier_name ?? "").toLowerCase();
        if (!v.includes(nameQuery)) return false;
      }

      if (minCalls !== null && r.call_count < minCalls) return false;

      if (minRate !== null && r.booking_rate_pct < minRate) return false;

      if (marginSet.size > 0) {
        const cls = classifyMargin(r.avg_booking_margin_pct);
        if (!marginSet.has(cls)) return false;
      }

      return true;
    });
  }, [rows, filters]);

  return (
    <div className="space-y-4">
      <CarrierFiltersBar shownCount={filtered.length} totalCount={rows.length} />
      {filtered.length === 0 ? (
        <div className="flex h-32 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
          No carriers match the current filters.
        </div>
      ) : (
        <CarriersTable rows={filtered} />
      )}
    </div>
  );
}
