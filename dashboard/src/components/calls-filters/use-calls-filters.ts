"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  parseAdvancedQueryRaw,
  serializeAdvancedQuery,
  type AdvancedQuery,
} from "./predicate-types";

// Per Tier-1 dashboard improvements: vanilla URL-state hook that drives the
// calls-list filters (date / outcome / sentiment / MC search). Mirrors the
// shape of `lib/use-dashboard-filters.ts` but stays page-local so the global
// dashboard date-picker keeps using its own contract.
//
// All filter state is encoded as URL query params:
//   ?from=YYYY-MM-DD       — start date (inclusive, local-time)
//   ?to=YYYY-MM-DD         — end date (inclusive, local-time)
//   ?outcome=a,b,c         — comma-separated outcome enum values
//   ?sentiment=x,y         — comma-separated sentiment enum values
//   ?mc=12345              — case-insensitive substring match against mc_number
//   ?q=<encoded-json>      — Tier-2 advanced query (predicate tree, see predicate-types.ts)
//
// Multiselect values use comma-separation rather than repeated keys to keep
// the URL short and the parsing trivial. Empty/missing params mean "no filter".
//
// Per ADR-011 we use `router.replace` (not `push`) so filter tweaks don't
// pollute browser history — back-button still escapes the filtered view in
// one click.

export const OUTCOME_VALUES = [
  "load_booked",
  "no_match",
  "call_abandoned",
  "rate_disagreement",
  "carrier_not_qualified",
] as const;

export const SENTIMENT_VALUES = [
  "positive",
  "neutral",
  "negative",
  "frustrated",
] as const;

export type OutcomeValue = (typeof OUTCOME_VALUES)[number];
export type SentimentValue = (typeof SENTIMENT_VALUES)[number];

export type CallsFiltersState = {
  from: string; // raw YYYY-MM-DD (or "")
  to: string;
  outcome: OutcomeValue[];
  sentiment: SentimentValue[];
  mc: string;
};

function parseCsv<T extends string>(raw: string | null, allowed: readonly T[]): T[] {
  if (!raw) return [];
  const set = new Set(allowed as readonly string[]);
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s): s is T => set.has(s));
}

export function useCallsFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const fromString = params.get("from") ?? "";
  const toString = params.get("to") ?? "";
  const outcomeString = params.get("outcome") ?? "";
  const sentimentString = params.get("sentiment") ?? "";
  const mcString = params.get("mc") ?? "";
  const qString = params.get("q");

  const filters: CallsFiltersState = useMemo(
    () => ({
      from: fromString,
      to: toString,
      outcome: parseCsv(outcomeString, OUTCOME_VALUES),
      sentiment: parseCsv(sentimentString, SENTIMENT_VALUES),
      mc: mcString,
    }),
    [fromString, toString, outcomeString, sentimentString, mcString],
  );

  const advancedQuery = useMemo<AdvancedQuery | null>(
    () => parseAdvancedQueryRaw(qString),
    [qString],
  );

  const hasAnyFilter =
    !!filters.from ||
    !!filters.to ||
    filters.outcome.length > 0 ||
    filters.sentiment.length > 0 ||
    !!filters.mc ||
    !!advancedQuery;

  const setFilters = useCallback(
    (next: Partial<CallsFiltersState>) => {
      const sp = new URLSearchParams(params.toString());

      function setOrDelete(key: string, value: string | undefined) {
        if (value === undefined) return; // unchanged
        if (value) sp.set(key, value);
        else sp.delete(key);
      }

      if ("from" in next) setOrDelete("from", next.from ?? "");
      if ("to" in next) setOrDelete("to", next.to ?? "");
      if ("outcome" in next) setOrDelete("outcome", (next.outcome ?? []).join(","));
      if ("sentiment" in next)
        setOrDelete("sentiment", (next.sentiment ?? []).join(","));
      if ("mc" in next) setOrDelete("mc", next.mc ?? "");

      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname);
    },
    [router, pathname, params],
  );

  const setAdvancedQuery = useCallback(
    (q: AdvancedQuery | null) => {
      const sp = new URLSearchParams(params.toString());
      const encoded = q ? serializeAdvancedQuery(q) : null;
      if (encoded) sp.set("q", encoded);
      else sp.delete("q");
      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname);
    },
    [router, pathname, params],
  );

  const clearAll = useCallback(() => {
    router.replace(pathname);
  }, [router, pathname]);

  return {
    filters,
    advancedQuery,
    hasAnyFilter,
    setFilters,
    setAdvancedQuery,
    clearAll,
  };
}
