import "server-only";

import Link from "next/link";

import { Breadcrumbs } from "@/components/breadcrumbs";
// Import each sub-component by path. We deliberately avoid the bare
// `@/components/call-detail` specifier because the old `call-detail.tsx`
// (legacy monolith) sits next to the new `call-detail/` directory; module
// resolution would prefer the file and silently shadow our index.
import { CallAuditRemarks } from "@/components/call-detail/call-audit-remarks";
import { CallBookingsTable } from "@/components/call-detail/call-bookings-table";
import { CallHeader, shortCallId } from "@/components/call-detail/call-header";
import { CallKpiCards } from "@/components/call-detail/call-kpi-cards";
import { CallTelemetry } from "@/components/call-detail/call-telemetry";
import { CallTranscriptToggle } from "@/components/call-detail/call-transcript-toggle";
import { ConversationTimeline } from "@/components/call-detail/conversation-timeline";
import { ToolSequence } from "@/components/call-detail/tool-sequence";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getCallTimeline } from "@/lib/api-client";
import { apiBaseUrl, apiBearerToken } from "@/lib/config";
import type { CallBookingRow, CallDetailRecord } from "@/lib/api-client";
import type { CallRecord } from "@/types/api-types";

// 5-min ISR fallback; webhook+SSE drives push freshness (ADR-009).
export const revalidate = 300;

// Inline server-side fetch — bypasses `lib/api-client::getCallById` because we
// want to control the `include_transcript` flag from this surface. The list
// endpoint client unconditionally sets it to true; here we default to false
// so the initial paint never carries transcript bytes. The transcript is
// re-fetched via the `loadTranscript` server action below.
async function fetchCallDetail(
  callId: string,
  includeTranscript: boolean,
): Promise<{ call: CallDetailRecord; bookings: CallBookingRow[] } | null> {
  const url =
    `${apiBaseUrl}/v1/calls/${encodeURIComponent(callId)}` +
    `?include_transcript=${includeTranscript ? "true" : "false"}`;
  const headers: Record<string, string> = { accept: "application/json" };
  if (apiBearerToken) headers.authorization = `Bearer ${apiBearerToken}`;
  const res = await fetch(
    url,
    includeTranscript
      ? { headers, cache: "no-store" } // never cache transcript bytes
      : { headers, next: { revalidate: 300 } },
  );
  if (!res.ok) {
    if (res.status === 404) return null;
    return null; // degrade gracefully — page renders the not-found shell
  }
  const data = (await res.json()) as {
    call: CallRecord;
    bookings: CallBookingRow[];
  };
  if (!data?.call) return null;
  const call: CallDetailRecord = { ...data.call, bookings: data.bookings ?? [] };
  return { call, bookings: data.bookings ?? [] };
}

export default async function CallDetailPage({
  params,
}: {
  params: Promise<{ call_id: string }>;
}) {
  const { call_id } = await params;
  const decoded = decodeURIComponent(call_id);
  const result = await fetchCallDetail(decoded, /* includeTranscript */ false);

  if (!result) {
    return (
      <div className="space-y-6">
        <Breadcrumbs
          items={[
            { label: "Dashboard", href: "/dashboard" },
            { label: "Calls", href: "/dashboard/calls" },
            { label: "Not found" },
          ]}
        />
        <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
          We couldn&apos;t find that call. It may have been deleted or never
          existed.
        </div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/dashboard/calls">← Back to calls</Link>
        </Button>
      </div>
    );
  }

  const { call, bookings } = result;
  const callIdStr = call.call_id ?? decoded;

  const timeline = await getCallTimeline(callIdStr);

  // Server action — re-fetches the same call with `include_transcript=true`.
  // Wrapped in a closure that captures only the call_id string (action args
  // must be JSON-serializable). Returning `null` lets the client distinguish
  // "fetched + empty" from "never fetched".
  async function loadTranscript(): Promise<string | null> {
    "use server";
    const res = await fetchCallDetail(callIdStr, /* includeTranscript */ true);
    return res?.call?.transcript ?? null;
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Calls", href: "/dashboard/calls" },
          { label: shortCallId(callIdStr) },
        ]}
      />

      <CallHeader call={call} />

      <CallKpiCards call={call} />

      <CallAuditRemarks remarks={call.audit_remarks} />

      <CallBookingsTable bookings={bookings} />

      <ToolSequence data={timeline} />

      <ConversationTimeline data={timeline} />

      <CallTelemetry call={call} timeline={timeline} />

      <CallTranscriptToggle fetchTranscript={loadTranscript} />

    </div>
  );
}
