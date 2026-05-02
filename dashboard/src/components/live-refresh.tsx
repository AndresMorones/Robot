"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Subscribes to the FastAPI Server-Sent Events stream (proxied through
 * /api/events/stream) and triggers `router.refresh()` on every `call-ended`
 * event. This is the push half of the Option C hybrid freshness pipeline:
 *
 *   HR call.ended -> POST /v1/events/call-ended (FastAPI)
 *     -> invalidate_dashboard_cache() + event_bus.publish()
 *     -> SSE fans out -> this component -> router.refresh()
 *     -> Server Components re-fetch (FastAPI cache cleared) -> Twin queried.
 *
 * The 5-minute Next.js ISR fallback (`revalidate=300` on each dashboard page)
 * catches any event we drop on the floor (network blip, slow consumer queue
 * full, machine restart). Push for latency; pull for guarantee.
 *
 * Auth split (see ADR-009):
 *   1. POST /api/events/session  -> server-side proxy adds Bearer -> FastAPI
 *      mints a one-shot opaque session token (60s TTL).
 *   2. EventSource('/api/events/stream?session=<opaque>') opens the stream;
 *      no custom headers are sent (EventSource cannot set them).
 *   3. FastAPI consumes the token (one-shot) and opens the stream.
 *
 * Reconnect strategy: exponential backoff capped at 30s. Resets to 1s on
 * successful open. Aborted on unmount via the captured `cancelled` flag.
 */
export function LiveRefresh(): null {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    let eventSource: EventSource | null = null;
    let backoff = 1000;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function connect(): Promise<void> {
      if (cancelled) return;
      try {
        const res = await fetch("/api/events/session", { method: "POST" });
        if (!res.ok) throw new Error(`session ${res.status}`);
        const { session_token: token } = (await res.json()) as {
          session_token: string;
        };
        if (cancelled) return;

        eventSource = new EventSource(
          `/api/events/stream?session=${encodeURIComponent(token)}`,
        );

        eventSource.addEventListener("call-ended", () => {
          // Re-fetch all Server Components in the current route segment.
          // FastAPI's TTLCache was already invalidated by the webhook receiver,
          // so this fetch goes all the way to Twin.
          router.refresh();
        });

        eventSource.onopen = () => {
          backoff = 1000;
        };

        eventSource.onerror = () => {
          eventSource?.close();
          eventSource = null;
          if (cancelled) return;
          retryTimer = setTimeout(connect, backoff);
          backoff = Math.min(backoff * 2, 30_000);
        };
      } catch {
        if (cancelled) return;
        retryTimer = setTimeout(connect, backoff);
        backoff = Math.min(backoff * 2, 30_000);
      }
    }

    void connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      eventSource?.close();
    };
  }, [router]);

  return null;
}
