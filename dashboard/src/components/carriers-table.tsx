"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fmtNumber, fmtPct, fmtRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CarrierRollupRow } from "@/types/api-types";

// Sortable per-MC rollup table. Mirrors the calls-table.tsx pattern: click a
// header to sort, click again to flip direction. Default sort is highest call
// count desc — surfaces the most active carriers first.
//
// Columns are intentionally limited to fields the API actually exposes on
// CarrierRollupRow (api/app/models.py). No row-link to a detail page — the
// /dashboard/carriers/[mc] route does not exist yet (out of scope for T-4).

type SortKey =
  | "mc_number"
  | "carrier_name"
  | "call_count"
  | "booked_count"
  | "booking_rate_pct"
  | "avg_booking_margin_pct"
  | "last_call_at";

type SortDir = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; align?: "right" }[] = [
  { key: "mc_number", label: "MC #" },
  { key: "carrier_name", label: "Carrier" },
  { key: "call_count", label: "Calls", align: "right" },
  { key: "booked_count", label: "Bookings", align: "right" },
  { key: "booking_rate_pct", label: "Booking rate", align: "right" },
  { key: "avg_booking_margin_pct", label: "(±) listed rate", align: "right" },
  { key: "last_call_at", label: "Last seen", align: "right" },
];

function pickValue(r: CarrierRollupRow, key: SortKey): string | number | null {
  switch (key) {
    case "mc_number":
      return r.mc_number ?? null;
    case "carrier_name":
      return r.carrier_name ?? null;
    case "call_count":
      return r.call_count;
    case "booked_count":
      return r.booked_count;
    case "booking_rate_pct":
      return r.booking_rate_pct;
    case "avg_booking_margin_pct":
      return r.avg_booking_margin_pct ?? null;
    case "last_call_at": {
      // Sort by epoch ms so chronological order is correct (string sort would
      // mostly work for ISO-8601 but breaks on null vs valid date).
      if (!r.last_call_at) return null;
      const t = new Date(r.last_call_at).getTime();
      return Number.isNaN(t) ? null : t;
    }
  }
}

export function CarriersTable({ rows }: { rows: CarrierRollupRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("call_count");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = pickValue(a, sortKey);
      const bv = pickValue(b, sortKey);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      let cmp = 0;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (k === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      setSortDir("desc");
    }
  }

  return (
    <div className="space-y-3 sigma-grid">
      <Table>
        <TableHeader>
          <TableRow>
            {COLUMNS.map((c) => (
              <TableHead
                key={c.key}
                className={cn(
                  "cursor-pointer select-none hover:bg-muted/40",
                  c.align === "right" && "text-right",
                )}
                onClick={() => toggleSort(c.key)}
              >
                <span
                  className={cn(
                    "inline-flex items-center gap-1",
                    c.align === "right" && "justify-end w-full",
                  )}
                >
                  {c.label}
                  {c.key === sortKey ? (
                    sortDir === "asc" ? (
                      <ChevronUp className="h-3 w-3" />
                    ) : (
                      <ChevronDown className="h-3 w-3" />
                    )
                  ) : (
                    <ChevronsUpDown className="h-3 w-3 opacity-40" />
                  )}
                </span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((r, i) => {
            // Sign convention locked 2026-05-01: negative pct = green
            // (booked below list), positive = red (concession). Matches
            // SalesRepCard / EconomicsCards / EffectiveDeltaChart.
            const marginPct = r.avg_booking_margin_pct ?? null;
            const marginToneClass =
              marginPct === null || marginPct === 0
                ? "text-muted-foreground"
                : marginPct < 0
                  ? "text-success"
                  : "text-destructive";
            const marginPrefix =
              marginPct === null || marginPct === 0
                ? ""
                : marginPct < 0
                  ? "−"
                  : "+";
            const marginValue =
              marginPct === null
                ? "—"
                : `${marginPrefix}${fmtPct(Math.abs(marginPct))}`;
            return (
              <TableRow key={r.mc_number ?? `row-${i}`}>
                <TableCell className="font-mono text-xs">
                  {r.mc_number ?? (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="max-w-[260px] truncate">
                  {r.carrier_name ?? (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtNumber(r.call_count)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtNumber(r.booked_count)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {fmtPct(r.booking_rate_pct)}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-right tabular-nums",
                    marginToneClass,
                  )}
                >
                  {marginValue}
                </TableCell>
                <TableCell className="text-right text-xs text-muted-foreground tabular-nums">
                  {r.last_call_at ? fmtRelative(r.last_call_at) : "—"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
