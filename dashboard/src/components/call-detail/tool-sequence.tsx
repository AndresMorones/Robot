import { Wrench } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  CallTimelineEntry,
  CallTimelineResponse,
} from "@/types/api-types";

// Tool-call sequence — pipeline-style horizontal flow of every tool the agent
// invoked during the call (verify_carrier → query_loads → negotiate_rate →
// book_load). Distinct from ConversationTimeline (which renders the full
// per-turn flow): this widget is purely the tool-call sub-stream, with the
// args + result payload exposed via <details>.
//
// Server Component — the parent page already fetches `getCallTimeline()`
// once and passes the payload down. No extra request, no client interactivity
// beyond native <details> disclosure.
//
// Friendly tool-name labels keep the four MVP tools readable; anything else
// title-cases the snake_case input so unknown tools (e.g. `calculate_rate`)
// still render cleanly without a code change.

const FRIENDLY_TOOL_LABELS: Record<string, string> = {
  verify_carrier: "Verify carrier",
  query_loads: "Search loads",
  negotiate_rate: "Negotiate rate",
  book_load: "Book load",
};

function friendlyToolName(name: string): string {
  const known = FRIENDLY_TOOL_LABELS[name];
  if (known) return known;
  // Fallback: title-case the snake_case input ("calculate_rate" → "Calculate rate").
  const [first, ...rest] = name.split("_");
  if (!first) return name;
  const head = first.charAt(0).toUpperCase() + first.slice(1).toLowerCase();
  const tail = rest.join(" ").toLowerCase();
  return tail ? `${head} ${tail}` : head;
}

// Inline ms formatter — task spec wants compact "172ms" (no space) on the
// duration badge, distinct from `fmtMs`'s "172 ms" presentation. Falls back
// to "—" when the round-trip pairing failed (no `tool_result` for the call).
function compactMs(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value < 1000) return `${Math.round(value)}ms`;
  return `${(value / 1000).toFixed(2)}s`;
}

// Duration speed → color band. Matches the broader call-detail palette: green
// = fast, amber = warning, brick-red = slow. <300ms forest, <1000ms amber,
// >=1000ms brick. Null durations stay neutral.
function durationToneClass(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) {
    return "border-border bg-muted/30 text-muted-foreground";
  }
  if (ms < 300) {
    return "border-success/40 bg-success/10 text-success";
  }
  if (ms < 1000) {
    return "border-warning/40 bg-warning/10 text-warning";
  }
  return "border-destructive/40 bg-destructive/10 text-destructive";
}

// Heuristic: a tool result is "errored" if it carries an explicit
// `error` field, or if `success` is the literal boolean false. Tool-specific
// shapes vary (verify_carrier returns `verified`, book_load returns `booked`,
// etc.) so we stay deliberately conservative — false-negative is preferred to
// shouting on every call.
function isErrorResult(result: Record<string, unknown> | null | undefined): boolean {
  if (!result || typeof result !== "object") return false;
  if ("error" in result && result.error) return true;
  if ("success" in result && result.success === false) return true;
  return false;
}

// Pair each `assistant_tool_call` entry with the next matching `tool_result`
// of the same tool name. The backend already attaches `duration_ms` to the
// tool_result entry, so we read it from there. Args come from the call entry,
// result from the result entry. Unmatched calls (e.g. the agent invoked a
// tool but the call ended before the result arrived) still render — with
// `result === null` and `duration_ms === null`.
type ResolvedToolCall = {
  tool_name: string;
  args: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  duration_ms: number | null;
  errored: boolean;
};

function resolveToolCalls(timeline: CallTimelineEntry[]): ResolvedToolCall[] {
  const results: ResolvedToolCall[] = [];
  // Walk the timeline once; for each `assistant_tool_call`, scan forward for
  // the first matching `tool_result` with the same tool_name that has not
  // already been claimed by an earlier call (handles repeated tool use).
  const claimed = new Set<number>();
  for (let i = 0; i < timeline.length; i += 1) {
    const entry = timeline[i];
    if (entry.kind !== "assistant_tool_call") continue;
    const name = entry.tool_name ?? "tool";
    let matchedResult: CallTimelineEntry | null = null;
    let matchedIdx = -1;
    for (let j = i + 1; j < timeline.length; j += 1) {
      if (claimed.has(j)) continue;
      const cand = timeline[j];
      if (cand.kind === "tool_result" && cand.tool_name === name) {
        matchedResult = cand;
        matchedIdx = j;
        break;
      }
    }
    if (matchedIdx >= 0) claimed.add(matchedIdx);
    const result = matchedResult?.result ?? null;
    results.push({
      tool_name: name,
      args: entry.args ?? null,
      result,
      duration_ms: matchedResult?.duration_ms ?? null,
      errored: isErrorResult(result),
    });
  }
  return results;
}

function totalDurationMs(calls: ResolvedToolCall[]): number {
  return calls.reduce((acc, c) => acc + (c.duration_ms ?? 0), 0);
}

function ToolStepCard({ call }: { call: ResolvedToolCall }) {
  const label = friendlyToolName(call.tool_name);
  const tone = durationToneClass(call.duration_ms);
  return (
    <details
      className={cn(
        "group min-w-[180px] flex-shrink-0 rounded-md border bg-card p-3 transition-colors",
        call.errored
          ? "border-destructive/60 ring-1 ring-destructive/30"
          : "border-border hover:border-foreground/30",
      )}
    >
      <summary className="flex cursor-pointer list-none flex-col gap-1.5 [&::-webkit-details-marker]:hidden">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-foreground">
            {label}
          </span>
          <span className="text-[10px] text-muted-foreground transition-transform group-open:rotate-90">
            ▶
          </span>
        </div>
        <span
          className={cn(
            "inline-flex w-fit items-center rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold tabular-nums",
            tone,
          )}
        >
          {compactMs(call.duration_ms)}
        </span>
        {call.errored ? (
          <span className="text-[10px] font-medium uppercase tracking-wider text-destructive">
            Errored
          </span>
        ) : null}
      </summary>

      <div className="mt-3 space-y-2 border-t border-border pt-3">
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Args
          </p>
          <pre className="whitespace-pre-wrap break-all rounded bg-muted/40 p-2 font-mono text-xs">
            {call.args ? JSON.stringify(call.args, null, 2) : "—"}
          </pre>
        </div>
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Result
          </p>
          <pre className="whitespace-pre-wrap break-all rounded bg-muted/40 p-2 font-mono text-xs">
            {call.result ? JSON.stringify(call.result, null, 2) : "—"}
          </pre>
        </div>
      </div>
    </details>
  );
}

// Connector between two cards — a horizontal hairline + chevron drawn purely
// in CSS (no SVG, per task constraints). Hidden on narrow viewports where the
// pipeline reflows to a vertical stack via `flex-wrap`.
function StepArrow() {
  return (
    <div
      aria-hidden
      className="hidden flex-shrink-0 items-center text-muted-foreground sm:flex"
    >
      <span className="block h-px w-6 bg-border" />
      <span className="-ml-1 text-sm leading-none">›</span>
    </div>
  );
}

export function ToolSequence({
  data,
}: {
  data: CallTimelineResponse | null;
}) {
  // Resolve once per render — derives args/result/duration by pairing
  // `assistant_tool_call` and `tool_result` entries on the timeline. Falls
  // back to the summary's `tool_calls` array (which carries name + duration
  // only) if the timeline is empty but the summary listed any.
  const timeline = data?.timeline ?? [];
  const resolved = resolveToolCalls(timeline);
  const summaryFallback: ResolvedToolCall[] =
    resolved.length === 0
      ? (data?.summary.tool_calls ?? []).map((t) => ({
          tool_name: t.tool_name,
          args: null,
          result: null,
          duration_ms: t.duration_ms,
          errored: false,
        }))
      : [];
  const calls = resolved.length > 0 ? resolved : summaryFallback;
  const total = totalDurationMs(calls);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <span className="flex items-center gap-2">
            <Wrench className="h-3.5 w-3.5" />
            Tool calls
          </span>
          {calls.length > 0 ? (
            <span className="font-normal normal-case tracking-normal text-muted-foreground">
              {calls.length} {calls.length === 1 ? "call" : "calls"}
              {total > 0 ? ` · ${compactMs(total)} total` : ""}
            </span>
          ) : null}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {calls.length === 0 ? (
          <div className="flex h-24 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
            No tools were called during this conversation.
          </div>
        ) : (
          <div className="flex flex-wrap items-stretch gap-2 overflow-x-auto pb-1">
            {calls.map((c, i) => (
              <div key={i} className="flex items-stretch gap-2">
                <ToolStepCard call={c} />
                {i < calls.length - 1 ? <StepArrow /> : null}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
