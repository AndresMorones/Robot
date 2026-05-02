"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { friendlyNodeLabel } from "@/lib/node-labels";

// Compact list view for the sales page's "In-flight calls" panel.
// Polls the same /api/calls/active proxy as <ActiveCallsIndicator /> every
// 10s and renders up to 5 rows. Operational info — kept utilitarian on
// purpose; the creative card is reserved for new bookings.

type ActiveRun = {
  run_id?: string | null;
  started_at?: string | null;
  duration_seconds?: number | null;
  current_node?: string | null;
  mc_number?: string | null;
};

type ActiveCallsResponse = {
  count: number;
  runs: ActiveRun[];
  status?: "ok" | "error" | "unconfigured";
};

const POLL_MS = 10_000;
const MAX_ROWS = 5;

function formatElapsed(run: ActiveRun): string {
  if (typeof run.duration_seconds === "number" && run.duration_seconds >= 0) {
    return formatSeconds(run.duration_seconds);
  }
  if (run.started_at) {
    const startedAt = Date.parse(run.started_at);
    if (!Number.isNaN(startedAt)) {
      return formatSeconds(Math.max(0, (Date.now() - startedAt) / 1000));
    }
  }
  return "—";
}

function formatSeconds(seconds: number): string {
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ActiveCallsMini(): React.JSX.Element {
  const [data, setData] = useState<ActiveCallsResponse>({
    count: 0,
    runs: [],
    status: "ok",
  });
  const aborter = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function tick(): Promise<void> {
      aborter.current?.abort();
      const ac = new AbortController();
      aborter.current = ac;
      try {
        const res = await fetch("/api/calls/active", {
          cache: "no-store",
          signal: ac.signal,
        });
        if (cancelled) return;
        if (!res.ok) {
          setData({ count: 0, runs: [], status: "error" });
          return;
        }
        const body = (await res.json()) as ActiveCallsResponse;
        if (cancelled) return;
        setData({
          count: body.count ?? 0,
          runs: Array.isArray(body.runs) ? body.runs : [],
          status: body.status ?? "ok",
        });
      } catch {
        if (cancelled) return;
        setData({ count: 0, runs: [], status: "error" });
      }
    }

    void tick();
    const interval = setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
      aborter.current?.abort();
    };
  }, []);

  const status = data.status ?? "ok";
  const isLive = status === "ok" && data.count >= 1;
  const runs = data.runs.slice(0, MAX_ROWS);

  return (
    <div className="rounded-lg border border-border bg-card">
      <header className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className={cn(
              "h-2 w-2 rounded-full",
              isLive
                ? "bg-emerald-500 animate-pulse motion-reduce:animate-none"
                : status === "error"
                  ? "bg-amber-500"
                  : "bg-muted-foreground/40",
            )}
          />
          <h2 className="text-sm font-semibold tracking-tight">
            In-flight calls
          </h2>
        </div>
        <span className="text-xs tabular-nums text-muted-foreground">
          {isLive ? `${data.count} live` : "Idle"}
        </span>
      </header>
      {runs.length === 0 ? (
        <p className="px-4 py-6 text-center text-xs text-muted-foreground">
          No live calls
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {runs.map((run, idx) => (
            <li
              key={run.run_id ?? `run-${idx}`}
              className="flex items-center gap-3 px-4 py-2.5 text-xs"
            >
              <span
                aria-hidden
                className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-emerald-500 motion-reduce:animate-none"
              />
              <span className="font-mono text-foreground">
                MC {run.mc_number ?? "—"}
              </span>
              <span className="truncate text-muted-foreground">
                {friendlyNodeLabel(run.current_node)}
              </span>
              <span className="ml-auto tabular-nums text-muted-foreground">
                {formatElapsed(run)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
