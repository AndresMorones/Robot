import "server-only";

// All env reads are centralized here so the API client and any future
// server-only helper share one definition. Reading these from a Client
// Component would throw at import time thanks to `server-only`.

export const apiBaseUrl =
  process.env.API_BASE_URL?.replace(/\/$/, "") ??
  "https://robot-api-andres-morones.fly.dev";

export const apiBearerToken = process.env.API_BEARER_TOKEN ?? "";

// Soft warning at module-load time — Next.js will surface it in the server
// log. We don't throw because /healthz + the OpenAPI types still resolve
// without auth and we want partial failure modes to be inspectable.
if (!apiBearerToken && process.env.NODE_ENV === "production") {
  console.warn(
    "[dashboard] API_BEARER_TOKEN not set — /v1/dashboard/* fetches will 401",
  );
}
