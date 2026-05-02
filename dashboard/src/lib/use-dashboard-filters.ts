"use client";

import { useCallback, useMemo } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

// Default window: last 7 days, ending today (per UX IA §4 — "Default load is 1w").
const DAY_MS = 86400000;

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0);
}

function endOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999);
}

function parseISODate(s: string | null): Date | null {
  if (!s) return null;
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return isNaN(d.getTime()) ? null : d;
}

function toISODate(d: Date): string {
  // Local-time YYYY-MM-DD (matches the user's timezone, not UTC).
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

/**
 * Reads + writes the global date filter via URL searchParams. router.push()
 * triggers a full Server Component refetch so dashboard pages re-render with
 * the new `from`/`to` propagated to FastAPI. Unparseable params silently fall
 * back to defaults.
 *
 * `filters` is memoized on the raw param strings — without this, Date refs are
 * new every render and any consumer with `filters.from` in a useEffect dep
 * array infinite-loops.
 */
export function useDashboardFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const fromString = params.get("from") ?? "";
  const toString = params.get("to") ?? "";

  const filters = useMemo(() => {
    const fromParam = parseISODate(fromString || null);
    const toParam = parseISODate(toString || null);
    const now = new Date();
    return {
      from: fromParam
        ? startOfDay(fromParam)
        : startOfDay(new Date(now.getTime() - 7 * DAY_MS)),
      to: toParam ? endOfDay(toParam) : endOfDay(now),
    };
  }, [fromString, toString]);

  const setFilters = useCallback(
    (next: { from: Date; to: Date }) => {
      const sp = new URLSearchParams();
      if (fromString) sp.set("from", fromString);
      if (toString) sp.set("to", toString);
      sp.set("from", toISODate(next.from));
      sp.set("to", toISODate(next.to));
      router.push(`${pathname}?${sp.toString()}`);
    },
    [router, pathname, fromString, toString],
  );

  return { filters, setFilters };
}
