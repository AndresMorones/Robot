"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

// Per Tier-1 dashboard improvements: vanilla URL-state hook for the
// /dashboard/carriers filter bar. Mirrors `use-calls-filters.ts` but is
// scoped to fields that exist on `CarrierRollupRow`.
//
// Date params (`?from`/`?to`) are intentionally NOT managed here — the
// global header `<DateRangePicker>` owns those and the carriers page already
// passes them server-side into `getCarriers(filters)`. This hook only manages
// the local URL params that are applied client-side over the rollup.
//
//   ?mc=12345              — case-insensitive substring match against mc_number
//   ?name=swift            — case-insensitive substring match against carrier_name
//   ?min_calls=3           — show only carriers with call_count >= N
//   ?min_rate=50           — show only carriers with booking_rate_pct >= N
//   ?margin_dir=below,unknown
//                          — comma-separated margin-direction enum values
//                            derived from avg_booking_margin_pct
//
// Per ADR-011 we use `router.replace` (not `push`) so filter tweaks don't
// pollute browser history.

export const MARGIN_DIR_VALUES = [
  "below_list",
  "at_list",
  "above_list",
  "unknown",
] as const;

export type MarginDirValue = (typeof MARGIN_DIR_VALUES)[number];

export type CarrierFiltersState = {
  mc: string;
  name: string;
  // Raw string from the URL — kept as-string so the input can show partial
  // / invalid drafts without snapping. Parsed numerically at filter time.
  minCalls: string;
  minRate: string;
  marginDir: MarginDirValue[];
};

function parseCsv<T extends string>(raw: string | null, allowed: readonly T[]): T[] {
  if (!raw) return [];
  const set = new Set(allowed as readonly string[]);
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s): s is T => set.has(s));
}

export function useCarrierFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const mcString = params.get("mc") ?? "";
  const nameString = params.get("name") ?? "";
  const minCallsString = params.get("min_calls") ?? "";
  const minRateString = params.get("min_rate") ?? "";
  const marginDirString = params.get("margin_dir") ?? "";

  const filters: CarrierFiltersState = useMemo(
    () => ({
      mc: mcString,
      name: nameString,
      minCalls: minCallsString,
      minRate: minRateString,
      marginDir: parseCsv(marginDirString, MARGIN_DIR_VALUES),
    }),
    [mcString, nameString, minCallsString, minRateString, marginDirString],
  );

  const hasAnyFilter =
    !!filters.mc ||
    !!filters.name ||
    !!filters.minCalls ||
    !!filters.minRate ||
    filters.marginDir.length > 0;

  const setFilters = useCallback(
    (next: Partial<CarrierFiltersState>) => {
      const sp = new URLSearchParams(params.toString());

      function setOrDelete(key: string, value: string | undefined) {
        if (value === undefined) return; // unchanged
        if (value) sp.set(key, value);
        else sp.delete(key);
      }

      if ("mc" in next) setOrDelete("mc", next.mc ?? "");
      if ("name" in next) setOrDelete("name", next.name ?? "");
      if ("minCalls" in next) setOrDelete("min_calls", next.minCalls ?? "");
      if ("minRate" in next) setOrDelete("min_rate", next.minRate ?? "");
      if ("marginDir" in next)
        setOrDelete("margin_dir", (next.marginDir ?? []).join(","));

      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname);
    },
    [router, pathname, params],
  );

  // Clear only this page's locally-managed filters. Leave `from`/`to` (and any
  // other URL params owned elsewhere) intact so the global date picker keeps
  // its selection across a "Clear all".
  const clearAll = useCallback(() => {
    const sp = new URLSearchParams(params.toString());
    sp.delete("mc");
    sp.delete("name");
    sp.delete("min_calls");
    sp.delete("min_rate");
    sp.delete("margin_dir");
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  }, [router, pathname, params]);

  return {
    filters,
    hasAnyFilter,
    setFilters,
    clearAll,
  };
}
