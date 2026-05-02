import "server-only";

import { NextResponse } from "next/server";

import { getCarriers } from "@/lib/api-client";

// Server-side proxy for the Cmd-K palette's carrier-search source. Mirrors
// the pattern used by /api/calls/active — keeps the API_BEARER_TOKEN out of
// the client bundle while letting the palette fetch on first open.
export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse> {
  try {
    const rollup = await getCarriers();
    return NextResponse.json({ rows: rollup.top_carriers });
  } catch {
    return NextResponse.json({ rows: [] }, { status: 502 });
  }
}
