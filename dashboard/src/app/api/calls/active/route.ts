import "server-only";

import { NextResponse } from "next/server";

import { apiBaseUrl, apiBearerToken } from "@/lib/config";

// Server-side proxy for the active-call indicator. Browser polls this every
// 10s (no Bearer); we forward to FastAPI with the long-lived token added
// server-side so it never enters the client bundle.
//
// FastAPI applies its own 10s TTLCache; this route is pure passthrough.
export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse> {
  if (!apiBearerToken) {
    return NextResponse.json(
      { count: 0, runs: [], status: "error", error: "API_BEARER_TOKEN unset" },
      { status: 500 },
    );
  }
  try {
    const upstream = await fetch(`${apiBaseUrl}/v1/calls/active`, {
      headers: {
        accept: "application/json",
        authorization: `Bearer ${apiBearerToken}`,
      },
      cache: "no-store",
    });
    if (!upstream.ok) {
      return NextResponse.json(
        { count: 0, runs: [], status: "error" },
        { status: upstream.status },
      );
    }
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { count: 0, runs: [], status: "error" },
      { status: 502 },
    );
  }
}
