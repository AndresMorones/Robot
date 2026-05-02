import "server-only";

import { NextResponse } from "next/server";

import { getCalls } from "@/lib/api-client";

// Server-side proxy for the Cmd-K palette's call-search source. Returns up to
// 50 most recent calls; the palette caches the response client-side for the
// session so subsequent ⌘K opens don't re-hit FastAPI.
export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse> {
  try {
    const { calls } = await getCalls(50);
    return NextResponse.json({ calls });
  } catch {
    return NextResponse.json({ calls: [] }, { status: 502 });
  }
}
