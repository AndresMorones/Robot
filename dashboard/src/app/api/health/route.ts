// Public healthcheck endpoint — bypasses signed-link middleware (see src/middleware.ts matcher).
// Used by Fly's HTTP healthcheck. Returns 200 + minimal JSON.

export const runtime = "nodejs";
export const dynamic = "force-static";

export function GET() {
  return Response.json({ status: "ok", service: "robot-dashboard" });
}
