import "server-only";

import { NextResponse } from "next/server";

import { apiBaseUrl, apiBearerToken } from "@/lib/config";

// Server-side proxy: browser POSTs here (no Bearer); we forward to FastAPI's
// /v1/events/session with the Bearer added server-side. This keeps the long-
// lived API_BEARER_TOKEN out of the browser bundle while letting the client
// EventSource open `/api/events/stream?session=<token>` with a short-lived
// one-shot opaque token.
//
// Route Handler is intentionally dynamic — we never want this cached.
export const dynamic = "force-dynamic";

export async function POST(): Promise<NextResponse> {
  if (!apiBearerToken) {
    return NextResponse.json(
      { error: "API_BEARER_TOKEN not configured" },
      { status: 500 },
    );
  }
  try {
    const upstream = await fetch(`${apiBaseUrl}/v1/events/session`, {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: `Bearer ${apiBearerToken}`,
      },
      cache: "no-store",
    });
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch (err) {
    return NextResponse.json(
      { error: "session proxy failed", detail: String(err) },
      { status: 502 },
    );
  }
}
