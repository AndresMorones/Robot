// Tier-2 advanced filter for the calls page. Lets the operator build an
// arbitrary predicate tree across CallRecord fields, composed by AND/OR.
//
// URL shape: ?q=<encoded JSON>
//   { "m": "AND" | "OR", "p": [ { "f": <field>, "o": <op>, "v": <string> }, ... ] }
//
// Compact keys keep the URL short; we parse defensively and fall through to
// "no advanced filter" on any malformed payload (see `parseAdvancedQueryRaw`).

import type { CallRecord } from "@/types/api-types";

// Searchable fields. Excludes `transcript` (huge), `id`, and `created_at`
// (handled by the simple-bar date picker).
export const PREDICATE_FIELDS = [
  "mc_number",
  "carrier_name",
  "legal_name",
  "call_outcome",
  "sentiment",
  "case_health_score",
  "audit_remarks",
  "fmcsa_eligibility_failure_reason",
  "callback_phone",
  "load_id",
  "duration_seconds",
] as const;

export type PredicateField = (typeof PREDICATE_FIELDS)[number];

export const NUMERIC_FIELDS = new Set<PredicateField>([
  "case_health_score",
  "duration_seconds",
]);

export const ENUM_FIELD_VALUES: Partial<Record<PredicateField, readonly string[]>> = {
  call_outcome: [
    "load_booked",
    "no_match",
    "call_abandoned",
    "rate_disagreement",
    "carrier_not_qualified",
  ],
  sentiment: ["positive", "neutral", "negative", "frustrated"],
};

export const PREDICATE_OPS = ["LIKE", "EQUALS", "NOT_EQUALS", ">=", "<="] as const;
export type PredicateOp = (typeof PREDICATE_OPS)[number];

// String ops apply to every field; numeric ops only show up when the field is
// numeric. Enforced at UI render time + at evaluate time (numeric op against a
// non-numeric value short-circuits to false).
export const STRING_OPS: PredicateOp[] = ["LIKE", "EQUALS", "NOT_EQUALS"];
export const NUMERIC_OPS: PredicateOp[] = [">=", "<="];

export type Predicate = {
  field: PredicateField;
  op: PredicateOp;
  value: string;
};

export type AdvancedQueryMode = "AND" | "OR";

export type AdvancedQuery = {
  mode: AdvancedQueryMode;
  predicates: Predicate[];
};

export const EMPTY_QUERY: AdvancedQuery = { mode: "AND", predicates: [] };

// ----- evaluation ----------------------------------------------------------

function fieldValueOf(call: CallRecord, field: PredicateField): unknown {
  // CallRecord types are nullable on every field; coerce missing → undefined.
  return (call as Record<string, unknown>)[field];
}

function toNumber(x: unknown): number | null {
  if (typeof x === "number" && Number.isFinite(x)) return x;
  if (typeof x === "string" && x.trim() !== "") {
    const n = Number(x);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

export function evaluatePredicate(call: CallRecord, p: Predicate): boolean {
  const raw = fieldValueOf(call, p.field);

  switch (p.op) {
    case ">=":
    case "<=": {
      const lhs = toNumber(raw);
      const rhs = toNumber(p.value);
      if (lhs === null || rhs === null) return false;
      return p.op === ">=" ? lhs >= rhs : lhs <= rhs;
    }
    case "LIKE": {
      const lhs = raw == null ? "" : String(raw).toLowerCase();
      const rhs = p.value.toLowerCase();
      if (rhs === "") return true; // empty LIKE = no constraint (UI also blocks)
      return lhs.includes(rhs);
    }
    case "EQUALS":
    case "NOT_EQUALS": {
      const lhs = raw == null ? "" : String(raw).toLowerCase();
      const rhs = p.value.toLowerCase();
      const eq = lhs === rhs;
      return p.op === "EQUALS" ? eq : !eq;
    }
  }
}

export function evaluateQuery(call: CallRecord, q: AdvancedQuery): boolean {
  if (q.predicates.length === 0) return true;
  if (q.mode === "AND") {
    for (const p of q.predicates) if (!evaluatePredicate(call, p)) return false;
    return true;
  }
  // OR
  for (const p of q.predicates) if (evaluatePredicate(call, p)) return true;
  return false;
}

// ----- URL serialization ---------------------------------------------------

export function isPredicateRowComplete(p: Predicate): boolean {
  return !!p.field && !!p.op && p.value.trim() !== "";
}

export function serializeAdvancedQuery(q: AdvancedQuery): string | null {
  const complete = q.predicates.filter(isPredicateRowComplete);
  if (complete.length === 0) return null;
  const compact = {
    m: q.mode,
    p: complete.map((p) => ({ f: p.field, o: p.op, v: p.value })),
  };
  return encodeURIComponent(JSON.stringify(compact));
}

let parseErrorLogged = false;

export function parseAdvancedQueryRaw(raw: string | null): AdvancedQuery | null {
  if (!raw) return null;
  try {
    const decoded = decodeURIComponent(raw);
    const obj = JSON.parse(decoded) as { m?: unknown; p?: unknown };
    const mode: AdvancedQueryMode = obj.m === "OR" ? "OR" : "AND";
    if (!Array.isArray(obj.p)) return null;
    const fields = new Set<string>(PREDICATE_FIELDS as readonly string[]);
    const ops = new Set<string>(PREDICATE_OPS as readonly string[]);
    const predicates: Predicate[] = [];
    for (const r of obj.p) {
      if (!r || typeof r !== "object") continue;
      const row = r as { f?: unknown; o?: unknown; v?: unknown };
      if (typeof row.f !== "string" || !fields.has(row.f)) continue;
      if (typeof row.o !== "string" || !ops.has(row.o)) continue;
      if (typeof row.v !== "string") continue;
      predicates.push({
        field: row.f as PredicateField,
        op: row.o as PredicateOp,
        value: row.v,
      });
    }
    if (predicates.length === 0) return null;
    return { mode, predicates };
  } catch (err) {
    if (!parseErrorLogged) {
      parseErrorLogged = true;
      // eslint-disable-next-line no-console
      console.warn("[calls-filters] Ignoring malformed ?q= advanced query:", err);
    }
    return null;
  }
}
