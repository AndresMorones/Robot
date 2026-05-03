// Client-side aggregation from per-call rows.
// API doesn't yet expose a daily/weekly/monthly series for outcome /
// booking-rate / sentiment; we compute them by bucketing CallRecord.created_at
// locally. Cheap because we already fetch the rows for other widgets
// (getCalls(200, filters)).
//
// Adaptive granularity: short windows render one bar per day; medium windows
// collapse to ISO weeks; long windows collapse to months. This keeps the
// x-axis readable when users pick "6 months" or "1 year" filters.

import type { CallRecord } from "@/types/api-types";

export type Granularity = "day" | "week" | "month";

export type DailyOutcomeBucket = {
  d: string; // canonical key: YYYY-MM-DD | YYYY-Www | YYYY-MM
  label: string; // x-axis display label (e.g. "Apr 30", "W17", "Apr 26")
  load_booked: number;
  no_match: number;
  carrier_not_qualified: number;
  call_abandoned: number;
  total: number;
};

export type DailyBookingRatePoint = {
  d: string;
  rate_pct: number | null;
  n: number;
};

export type DailySentimentBucket = {
  d: string;
  label: string;
  positive: number;
  neutral: number;
  negative: number;
  total: number;
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * Pick a bucket size based on window length.
 *  - ≤ 21 days   → "day" (one bar per day)
 *  - 22-180 days → "week" (Monday-anchored ISO weeks, label = "Week of MMM DD")
 *  - > 180 days  → "month"
 *
 * Missing bound → "day" with the existing 14-day implicit window behavior.
 */
export function bucketGranularity(
  from: Date | undefined,
  to: Date | undefined,
): Granularity {
  if (!from || !to) return "day";
  const days = Math.max(0, (to.getTime() - from.getTime()) / MS_PER_DAY);
  if (days <= 21) return "day";
  if (days <= 180) return "week";
  return "month";
}

function dayKey(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function monthKey(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

/** Monday-anchored start of the ISO week containing `d` (in UTC). */
function startOfIsoWeekUTC(d: Date): Date {
  const x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  // getUTCDay: Sun=0, Mon=1, ..., Sat=6. Shift so Mon=0.
  const dow = (x.getUTCDay() + 6) % 7;
  x.setUTCDate(x.getUTCDate() - dow);
  return x;
}

/** ISO week-number key like "2026-W17" (Thursday rule). */
function isoWeekKey(d: Date): string {
  // Copy to UTC, set to Thursday of current ISO week.
  const x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const dow = (x.getUTCDay() + 6) % 7; // Mon=0
  x.setUTCDate(x.getUTCDate() - dow + 3); // Thursday of this week
  const isoYear = x.getUTCFullYear();
  const yearStart = new Date(Date.UTC(isoYear, 0, 1));
  const yearStartDow = (yearStart.getUTCDay() + 6) % 7;
  // Thursday of week 1
  const week1Thu = new Date(yearStart);
  week1Thu.setUTCDate(yearStart.getUTCDate() + ((3 - yearStartDow + 7) % 7));
  const weekNo =
    1 + Math.round((x.getTime() - week1Thu.getTime()) / (7 * MS_PER_DAY));
  return `${isoYear}-W${String(weekNo).padStart(2, "0")}`;
}

function bucketKey(d: Date, g: Granularity): string {
  if (g === "day") return dayKey(d);
  if (g === "week") return isoWeekKey(d);
  return monthKey(d);
}

function md(d: Date): string {
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function bucketLabel(d: Date, g: Granularity): string {
  if (g === "day") return md(d);
  if (g === "week") {
    const mon = startOfIsoWeekUTC(d);
    const sun = new Date(mon);
    sun.setUTCDate(mon.getUTCDate() + 6);
    return `${md(mon)} - ${md(sun)}`;
  }
  // month: full month + 4-digit year (e.g., "May 2026")
  return d.toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function parseISO(s: string | null | undefined): Date | null {
  if (!s) return null;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Walk the active window, granularity-stepped, emitting every bucket key/label
 * pair so the chart shows continuous time even for empty buckets. When window
 * bounds are missing we fall back to the span actually present in `keysSeen`.
 */
function* iterateBuckets(
  from: Date,
  to: Date,
  g: Granularity,
): Generator<{ key: string; label: string }> {
  // Normalize iteration start to the bucket containing `from`.
  let cursor: Date;
  if (g === "day") {
    cursor = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate()));
  } else if (g === "week") {
    cursor = startOfIsoWeekUTC(from);
  } else {
    cursor = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), 1));
  }

  while (cursor.getTime() <= to.getTime()) {
    yield { key: bucketKey(cursor, g), label: bucketLabel(cursor, g) };
    if (g === "day") cursor.setUTCDate(cursor.getUTCDate() + 1);
    else if (g === "week") cursor.setUTCDate(cursor.getUTCDate() + 7);
    else cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
}

/**
 * Build the ordered list of bucket {key,label} pairs covering the window. If
 * window bounds are missing we infer them from `seenDates` and pad to a 14-day
 * minimum window — keeps the empty-state path looking sensible.
 */
function buildBucketAxis(
  g: Granularity,
  from: Date | undefined,
  to: Date | undefined,
  seenDates: Date[],
): { key: string; label: string }[] {
  let lo: Date;
  let hi: Date;
  if (from && to) {
    lo = from;
    hi = to;
  } else if (seenDates.length > 0) {
    const sorted = [...seenDates].sort((a, b) => a.getTime() - b.getTime());
    lo = sorted[0];
    hi = sorted[sorted.length - 1];
    // Implicit 14-day floor when bounds were not provided (legacy behavior).
    const minSpan = 13 * MS_PER_DAY;
    if (hi.getTime() - lo.getTime() < minSpan) {
      lo = new Date(hi.getTime() - minSpan);
    }
  } else {
    return [];
  }
  return [...iterateBuckets(lo, hi, g)];
}

export function bucketByOutcome(
  calls: CallRecord[],
  granularity: Granularity = "day",
  from?: Date,
  to?: Date,
): DailyOutcomeBucket[] {
  const map = new Map<string, DailyOutcomeBucket>();
  const seen: Date[] = [];
  for (const c of calls) {
    const dt = parseISO(c.created_at);
    if (!dt) continue;
    seen.push(dt);
    const key = bucketKey(dt, granularity);
    let b = map.get(key);
    if (!b) {
      b = {
        d: key,
        label: bucketLabel(dt, granularity),
        load_booked: 0,
        no_match: 0,
        carrier_not_qualified: 0,
        call_abandoned: 0,
        total: 0,
      };
      map.set(key, b);
    }
    // Normalize outcome aliases — Twin can return either the canonical name
    // ("load_booked") or the colloquial form ("booked"); count both as the
    // same bucket so the bar chart renders the segment instead of a phantom
    // total with no visible bar.
    const o = c.call_outcome;
    if (o === "load_booked" || o === "booked") b.load_booked += 1;
    else if (o === "no_match") b.no_match += 1;
    else if (
      o === "carrier_not_qualified" ||
      o === "fmcsa_declined" ||
      o === "not_qualified"
    )
      b.carrier_not_qualified += 1;
    else if (o === "call_abandoned" || o === "abandoned") b.call_abandoned += 1;
    b.total += 1;
  }

  const axis = buildBucketAxis(granularity, from, to, seen);
  if (!axis.length) return [];
  return axis.map(({ key, label }) => {
    const existing = map.get(key);
    if (existing) {
      // Prefer canonical axis label so empty/non-empty buckets line up.
      existing.label = label;
      return existing;
    }
    return {
      d: key,
      label,
      load_booked: 0,
      no_match: 0,
      carrier_not_qualified: 0,
      call_abandoned: 0,
      total: 0,
    };
  });
}

export function bookingRateSeries(
  buckets: DailyOutcomeBucket[],
): DailyBookingRatePoint[] {
  return buckets.map((b) => ({
    d: b.d,
    n: b.total,
    rate_pct: b.total > 0 ? Math.round((b.load_booked / b.total) * 1000) / 10 : null,
  }));
}

export function bucketBySentiment(
  calls: CallRecord[],
  granularity: Granularity = "day",
  from?: Date,
  to?: Date,
): DailySentimentBucket[] {
  const map = new Map<string, DailySentimentBucket>();
  const seen: Date[] = [];
  for (const c of calls) {
    const dt = parseISO(c.created_at);
    if (!dt) continue;
    seen.push(dt);
    const key = bucketKey(dt, granularity);
    let b = map.get(key);
    if (!b) {
      b = {
        d: key,
        label: bucketLabel(dt, granularity),
        positive: 0,
        neutral: 0,
        negative: 0,
        total: 0,
      };
      map.set(key, b);
    }
    const s = (c.sentiment ?? "").toLowerCase();
    if (s === "positive") b.positive += 1;
    else if (s === "neutral") b.neutral += 1;
    else if (s === "negative") b.negative += 1;
    if (s) b.total += 1;
  }

  const axis = buildBucketAxis(granularity, from, to, seen);
  if (!axis.length) return [];
  return axis.map(({ key, label }) => {
    const existing = map.get(key);
    if (existing) {
      existing.label = label;
      return existing;
    }
    return {
      d: key,
      label,
      positive: 0,
      neutral: 0,
      negative: 0,
      total: 0,
    };
  });
}

export function favorableSentimentPct(buckets: DailySentimentBucket[]): number | null {
  let pos = 0;
  let neu = 0;
  let total = 0;
  for (const b of buckets) {
    pos += b.positive;
    neu += b.neutral;
    total += b.total;
  }
  if (!total) return null;
  return Math.round(((pos + neu) / total) * 1000) / 10;
}
