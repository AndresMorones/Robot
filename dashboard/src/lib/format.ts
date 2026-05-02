// Pure formatting helpers — safe in both Server and Client Components.

export function fmtCurrency(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v.toFixed(digits)}%`;
}

export function fmtNumber(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

// Compact millisecond formatter for the Telemetry tab. Sub-second values stay
// in ms ("843 ms"); >=1000ms flips to seconds with a single decimal ("1.2 s").
export function fmtMs(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return "—";
  }
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m > 0 ? `${m}m ${r}s` : `${r}s`;
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const diff = Date.now() - d.getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

// Best-effort label of a (from, to) range as "Last 1 day" / "Last 7 days" /
// "Last 1 month" / "Last 6 months" / "Last 1 year" / "Custom range". Matches
// the date picker presets (1d / 7d / 1m / 6m / 1y); anything else falls back
// to "Custom range".
export function fmtDateRangeLabel(from: Date, to: Date): string {
  const now = new Date();
  // Both endpoints must end "today" (within ~1 day) for a preset to match.
  const endDelta = Math.abs(now.getTime() - to.getTime());
  if (endDelta > 36 * 60 * 60 * 1000) return "Custom range";

  const spanDays = Math.round((to.getTime() - from.getTime()) / 86400000);
  if (spanDays <= 1) return "Last 1 day";
  if (spanDays <= 7) return "Last 7 days";
  if (spanDays <= 31) return "Last 1 month";
  if (spanDays <= 186) return "Last 6 months";
  if (spanDays <= 366) return "Last 1 year";
  return "Custom range";
}

export function titleCase(s: string | null | undefined): string {
  if (!s) return "—";
  return s
    .replace(/_/g, " ")
    .split(" ")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(" ");
}
