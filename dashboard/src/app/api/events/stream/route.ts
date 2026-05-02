import "server-only";

import type { NextRequest } from "next/server";

import { apiBaseUrl } from "@/lib/config";

// Server-side proxy for Server-Sent Events. The browser opens an EventSource
// at /api/events/stream?session=<opaque>, which the upstream /v1/events/stream
// validates as a one-shot session token. We pipe the upstream response body
// (a ReadableStream of `event: ... \ndata: ...` chunks) through unchanged.
//
// No Bearer is forwarded — the session token alone is sufficient on the
// FastAPI side; that's the whole reason the session-token mint endpoint
// exists (EventSource cannot set custom headers).
//
// `force-dynamic` is required because Next.js otherwise treats the Route
// Handler as static. `runtime: "nodejs"` is implied for streamed proxies.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: NextRequest): Promise<Response> {
  const session = req.nextUrl.searchParams.get("session");
  if (!session) {
    return new Response(
      JSON.stringify({ error: "missing session param" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(
      `${apiBaseUrl}/v1/events/stream?session=${encodeURIComponent(session)}`,
      {
        method: "GET",
        headers: { accept: "text/event-stream" },
        cache: "no-store",
        // Preserve client cancellation so the upstream connection closes when
        // the browser disconnects (otherwise the SSE generator leaks until
        // the keepalive timeout fires).
        signal: req.signal,
      },
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "stream proxy failed", detail: String(err) }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }

  // Non-200 upstream: forward status + JSON body so the client can react
  // (most commonly 401 on a reused / expired session token).
  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => "");
    return new Response(text || JSON.stringify({ error: "upstream error" }), {
      status: upstream.status || 502,
      headers: { "content-type": "application/json" },
    });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
      connection: "keep-alive",
      "x-accel-buffering": "no",
    },
  });
}
