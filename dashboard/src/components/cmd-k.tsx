"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { cn } from "@/lib/utils";

// Loadboard Live Cmd-K palette (per locked theme spec §1.5).
// 640px floating panel, 12px radius, primary glow shadow. Fuzzy-matched results
// over: tabs (overview / outcomes / economics / etc.), pages (calls / carriers
// / sales / bookings), and MC numbers / lanes / call IDs (added later via
// data prop). ⌘K opens, Esc closes, arrow keys navigate, Enter executes.

export type CmdKItem = {
  id: string;
  label: string;
  hint?: string;
  group: "Navigate" | "Tabs" | "Carriers" | "Calls" | "Lanes";
  href: string;
};

// Static navigation surface — extended at runtime with dynamic carrier / call
// items if the consumer passes them via props. Keep this list short; fuzzy
// matching is O(n) per keystroke.
const STATIC_ITEMS: CmdKItem[] = [
  { id: "nav-overview", label: "Overview", group: "Navigate", href: "/dashboard" },
  { id: "nav-calls", label: "Calls", group: "Navigate", href: "/dashboard/calls" },
  { id: "nav-sales", label: "New Bookings", group: "Navigate", href: "/dashboard/sales" },
  // Tabs route to the dashboard root with a hash so the user knows which one.
  { id: "tab-outcomes", label: "Outcomes tab", group: "Tabs", href: "/dashboard#outcomes" },
  { id: "tab-economics", label: "Economics tab", group: "Tabs", href: "/dashboard#economics" },
  { id: "tab-operational", label: "Operational tab", group: "Tabs", href: "/dashboard#operational" },
  { id: "tab-quality", label: "Quality tab", group: "Tabs", href: "/dashboard#quality" },
  { id: "tab-telemetry", label: "Telemetry tab", group: "Tabs", href: "/dashboard#telemetry" },
  // Common range presets — wires into the Telemetry tab's URL state.
  { id: "range-1h", label: "Telemetry · last 1 hour", hint: "?range=1h", group: "Tabs", href: "/dashboard?range=1h#telemetry" },
  { id: "range-1d", label: "Telemetry · last 1 day", hint: "?range=1d", group: "Tabs", href: "/dashboard?range=1d#telemetry" },
  { id: "range-1w", label: "Telemetry · last 1 week", hint: "?range=1w#telemetry", group: "Tabs", href: "/dashboard?range=1w#telemetry" },
];

function score(item: CmdKItem, query: string): number {
  if (!query) return 0;
  const q = query.toLowerCase();
  const label = item.label.toLowerCase();
  if (label === q) return 1000;
  if (label.startsWith(q)) return 500;
  if (label.includes(q)) return 100;
  // Sub-sequence match: every char in q appears in order in label.
  let i = 0;
  for (const c of label) {
    if (c === q[i]) i++;
    if (i === q.length) return 10;
  }
  return -1;
}

export type CmdKProps = {
  /** Optional dynamic items appended to the static list (e.g. carrier MCs, call IDs). */
  extraItems?: CmdKItem[];
};

export function CmdK({ extraItems = [] }: CmdKProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // ⌘K / Ctrl-K opens; Esc closes (when open).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape" && open) {
        e.preventDefault();
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Focus the input + reset state when opening.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIdx(0);
    queueMicrotask(() => inputRef.current?.focus());
  }, [open]);

  const items = useMemo(() => [...STATIC_ITEMS, ...extraItems], [extraItems]);

  const filtered = useMemo(() => {
    if (!query.trim()) return items.slice(0, 12);
    const scored = items
      .map((it) => ({ it, s: score(it, query.trim()) }))
      .filter(({ s }) => s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 12)
      .map(({ it }) => it);
    return scored;
  }, [items, query]);

  // Clamp active index when filtered shrinks.
  useEffect(() => {
    if (activeIdx >= filtered.length) setActiveIdx(Math.max(0, filtered.length - 1));
  }, [filtered.length, activeIdx]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = filtered[activeIdx];
      if (target) {
        router.push(target.href);
        setOpen(false);
      }
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]"
    >
      <button
        type="button"
        aria-label="Close palette"
        onClick={() => setOpen(false)}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />
      <div
        className={cn(
          "relative z-10 w-full max-w-[640px] overflow-hidden rounded-xl border border-border",
          "bg-popover text-popover-foreground shadow-2xl",
          // primary glow per spec §1.5
          "shadow-[0_0_0_1px_rgba(255,255,255,0.04),0_24px_72px_-12px_rgba(0,220,130,0.18)]",
        )}
      >
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            ⌘K
          </span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search tabs, carriers, calls, lanes…"
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            aria-label="Command query"
          />
          <kbd className="rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            Esc
          </kbd>
        </div>
        <ul className="max-h-[60vh] overflow-y-auto py-1" role="listbox">
          {filtered.length === 0 ? (
            <li className="px-3 py-4 text-center text-xs text-muted-foreground">
              No matches.
            </li>
          ) : (
            filtered.map((item, idx) => {
              const active = idx === activeIdx;
              return (
                <li
                  key={item.id}
                  role="option"
                  aria-selected={active}
                  onMouseEnter={() => setActiveIdx(idx)}
                  onClick={() => {
                    router.push(item.href);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm",
                    active && "bg-secondary text-secondary-foreground",
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      {item.group}
                    </span>
                    <span>{item.label}</span>
                  </div>
                  {item.hint ? (
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {item.hint}
                    </span>
                  ) : null}
                </li>
              );
            })
          )}
        </ul>
        <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-1.5 text-[10px] font-mono text-muted-foreground">
          <span>↑↓ navigate · ↵ open · esc close</span>
          <span>{filtered.length} matches</span>
        </div>
      </div>
    </div>
  );
}
