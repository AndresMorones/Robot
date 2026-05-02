"use client";

import * as React from "react";
import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { AdvancedQueryBuilder } from "./advanced-query-builder";
import { MultiSelectDropdown } from "./multiselect-dropdown";
import {
  OUTCOME_VALUES,
  SENTIMENT_VALUES,
  useCallsFilters,
  type OutcomeValue,
  type SentimentValue,
} from "./use-calls-filters";

// Tier-1 calls-list filter bar — outcome + sentiment + MC search.
// State syncs to URL query params (vanilla useSearchParams + router.replace,
// no nuqs per ADR-011). The page-level data fetch is server-side and date-
// filtered via the global `<DateRangePicker>` in the header (writes the same
// `?from`/`?to` URL keys); outcome / sentiment / MC are applied client-side
// over the server-fetched rows.

export function CallsFiltersBar({
  shownCount,
  totalCount,
  className,
}: {
  shownCount: number;
  totalCount: number;
  className?: string;
}) {
  const {
    filters,
    advancedQuery,
    hasAnyFilter,
    setFilters,
    setAdvancedQuery,
    clearAll,
  } = useCallsFilters();

  // MC search uses local state for typing latency, then commits to the URL on
  // change. Debounced so each keystroke doesn't `router.replace`.
  const [mcLocal, setMcLocal] = React.useState(filters.mc);

  // Sync local input with URL when URL changes externally (e.g. clear-all).
  React.useEffect(() => {
    setMcLocal(filters.mc);
  }, [filters.mc]);

  // Debounce commit. 200ms feels responsive without flooding history.
  React.useEffect(() => {
    if (mcLocal === filters.mc) return;
    const t = setTimeout(() => setFilters({ mc: mcLocal }), 200);
    return () => clearTimeout(t);
  }, [mcLocal, filters.mc, setFilters]);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-end gap-2">
        {/* Outcome multiselect */}
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Outcome</span>
          <MultiSelectDropdown<OutcomeValue>
            label="Outcome"
            options={OUTCOME_VALUES}
            selected={filters.outcome}
            onChange={(next) => setFilters({ outcome: next })}
          />
        </div>

        {/* Sentiment multiselect */}
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Sentiment</span>
          <MultiSelectDropdown<SentimentValue>
            label="Sentiment"
            options={SENTIMENT_VALUES}
            selected={filters.sentiment}
            onChange={(next) => setFilters({ sentiment: next })}
          />
        </div>

        {/* MC search */}
        <label className="flex flex-1 flex-col gap-1 text-xs text-muted-foreground sm:max-w-xs">
          MC #
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={mcLocal}
              onChange={(e) => setMcLocal(e.target.value)}
              placeholder="Filter by MC number..."
              className="pl-8 pr-8"
              aria-label="Filter by MC number"
              inputMode="numeric"
            />
            {mcLocal ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-9 w-9 text-muted-foreground hover:text-foreground"
                onClick={() => setMcLocal("")}
                aria-label="Clear MC filter"
              >
                <X className="h-4 w-4" />
              </Button>
            ) : null}
          </div>
        </label>
      </div>

      <AdvancedQueryBuilder
        query={advancedQuery}
        onApply={(q) => setAdvancedQuery(q)}
        onClear={() => setAdvancedQuery(null)}
      />

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing <span className="font-medium text-foreground">{shownCount}</span>{" "}
          of <span className="font-medium text-foreground">{totalCount}</span>{" "}
          {totalCount === 1 ? "call" : "calls"}
        </span>
        {hasAnyFilter ? (
          <Button
            type="button"
            variant="link"
            size="sm"
            onClick={clearAll}
            className="h-auto p-0 text-xs"
          >
            Clear all filters
          </Button>
        ) : null}
      </div>
    </div>
  );
}
