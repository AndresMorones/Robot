"use client";

import * as React from "react";

import { CallsTable } from "@/components/calls-table";
import type { CallRecord } from "@/types/api-types";

import { CallsFiltersBar } from "./calls-filters-bar";
import { evaluateQuery } from "./predicate-types";
import { useCallsFilters } from "./use-calls-filters";

// Client-side wrapper: takes the full server-fetched call list and applies
// URL-driven filters before rendering. Filtering all-in-browser is fine at
// MVP scale (Twin has < 100 rows; FastAPI returns up to 200 by default —
// see `getCalls(200, ...)` in the parent server component).
//
// For larger datasets the same filter shape can move server-side by
// forwarding the URL params to FastAPI; the page would then refetch on
// router.replace via Next.js searchParams change.

function parseDateInclusive(s: string, kind: "from" | "to"): Date | null {
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]) - 1;
  const d = Number(m[3]);
  const date =
    kind === "from"
      ? new Date(y, mo, d, 0, 0, 0, 0)
      : new Date(y, mo, d, 23, 59, 59, 999);
  return isNaN(date.getTime()) ? null : date;
}

function withinDateRange(
  iso: string | null | undefined,
  from: Date | null,
  to: Date | null,
): boolean {
  if (!from && !to) return true;
  if (!iso) return false; // calls without created_at can't satisfy a date filter
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  if (from && d.getTime() < from.getTime()) return false;
  if (to && d.getTime() > to.getTime()) return false;
  return true;
}

export function CallsListWithFilters({ calls }: { calls: CallRecord[] }) {
  const { filters, advancedQuery } = useCallsFilters();

  const filtered = React.useMemo(() => {
    const fromDate = filters.from ? parseDateInclusive(filters.from, "from") : null;
    const toDate = filters.to ? parseDateInclusive(filters.to, "to") : null;
    const outcomeSet = new Set<string>(filters.outcome);
    const sentimentSet = new Set<string>(filters.sentiment);
    const mcQuery = filters.mc.trim().toLowerCase();

    // Simple-bar filters first (cheaper, narrows down). Advanced query refines
    // the survivors. Skipping the advanced pass entirely when no query is set
    // avoids the per-row function-call overhead.
    const simpleBarFiltered = calls.filter((c) => {
      if (!withinDateRange(c.created_at, fromDate, toDate)) return false;

      if (outcomeSet.size > 0) {
        const v = (c.call_outcome ?? "").toLowerCase();
        if (!outcomeSet.has(v)) return false;
      }

      if (sentimentSet.size > 0) {
        const v = (c.sentiment ?? "").toLowerCase();
        if (!sentimentSet.has(v)) return false;
      }

      if (mcQuery) {
        const v = (c.mc_number ?? "").toLowerCase();
        if (!v.includes(mcQuery)) return false;
      }

      return true;
    });

    if (!advancedQuery) return simpleBarFiltered;
    return simpleBarFiltered.filter((c) => evaluateQuery(c, advancedQuery));
  }, [calls, filters, advancedQuery]);

  return (
    <div className="space-y-4">
      <CallsFiltersBar shownCount={filtered.length} totalCount={calls.length} />
      <CallsTable calls={filtered} showSearch={false} />
    </div>
  );
}
