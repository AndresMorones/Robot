// Maps internal HR workflow node names to broker-friendly labels surfaced
// in the dashboard's active-calls indicators. The `current_node` value
// returned by HR's runs API is an engineer-oriented identifier (e.g.
// `negotiate_evaluate`, `verify_carrier`); brokers don't know what those
// mean. This lookup keeps the live indicator informative without leaking
// internal workflow vocabulary.
//
// Add new entries here as the workflow grows — anything not matched falls
// back to a humanized version of the raw node name.

const NODE_LABELS: Record<string, string> = {
  inbound_voice_agent: "On call",
  prompt: "On call",
  verify_carrier: "Verifying carrier",
  query_loads: "Searching loads",
  search_loads: "Searching loads",
  search_loads_by_lane: "Searching loads",
  find_available_loads: "Searching loads",
  negotiate_evaluate: "Negotiating",
  calculate_rate: "Negotiating",
  book_load: "Booking load",
  finalize_call: "Wrapping up",
  transfer_popup: "Transferring",
  ai_extract: "Logging call",
  classify_outcome: "Logging call",
  classify_sentiment: "Logging call",
  case_health_score: "Logging call",
  carrier_sales_auditor: "Logging call",
  write_to_twin: "Logging call",
};

function humanize(raw: string): string {
  // negotiate_evaluate → Negotiate evaluate; carrier-sales → Carrier sales.
  const cleaned = raw.replace(/[_-]+/g, " ").trim();
  if (!cleaned) return "In progress";
  return cleaned[0].toUpperCase() + cleaned.slice(1);
}

export function friendlyNodeLabel(raw: string | null | undefined): string {
  if (!raw) return "In progress";
  const key = raw.toLowerCase().trim();
  return NODE_LABELS[key] ?? humanize(raw);
}
