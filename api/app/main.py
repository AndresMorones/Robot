"""FastAPI application entry point.

Storage: HR Twin (managed Postgres) for loads + calls_log + bookings.
Reads via twin_client (HTTP) using HAPPYROBOT_API_KEY as Bearer.

Auth: every /v1/* endpoint accepts either `Authorization: Bearer <token>` OR
`x-api-key: <token>` (constant-time compare in app/deps.py::require_api_key).
Header-only — the legacy `?token=` query-string fallback was removed in
ADR-008 (tokens-in-URLs leak into logs / referer / browser history).

Architecture pivot (v15+): HR's Write-to-Twin component owns all call-log
writes — `bookings` mid-call via the book_load tool, `calls_log` post-call via
AI Extract → Case Health → Write-to-Twin. FastAPI is read-only for both
tables; POST /v1/calls/log returns 410 Gone for legacy callers.

Endpoints:
  /healthz                       — Fly healthcheck (no auth)
  /docs                          — Swagger UI (no auth)
  /dashboard                     — server-rendered HTML view (no auth, no PII)
  /loads/{reference_number}      — HR find_available_loads (auth)
  /loads/search                  — HR search_loads_by_lane (auth)
  /v1/loads/{reference_number}   — /v1-prefixed alias for /loads/{reference_number}
  /v1/loads/search               — /v1-prefixed alias for /loads/search
  /v1/calls (GET)                — recent calls list, no transcript (auth)
  /v1/calls/{call_id} (GET)      — single call + bookings + load lane (auth)
  /v1/calls (POST)               — 410 Gone (deprecated; see HR Write-to-Twin)
  /v1/calls/active               — in-flight call indicator (HR Monitor proxy, auth)
  /v1/carriers                   — top-N per-MC rollups (auth)
  /v1/carriers/{mc_number}       — single per-MC rollup (auth)
  /v1/dashboard/funnel           — funnel KPIs (auth)
  /v1/dashboard/economics        — economics KPIs (auth)
  /v1/dashboard/operational      — operational KPIs (auth)
  /v1/dashboard/quality          — quality KPIs (auth)
  /v1/dashboard/calls            — dashboard calls feed (auth)
  /v1/dashboard/loads            — dashboard loads feed (auth)
  /v1/events/call-ended (POST)   — HR webhook receiver, invalidates cache + SSE-fans (auth)
  /v1/events/session (POST)      — mints one-shot SSE session token (auth)
  /v1/events/stream (GET)        — SSE stream (session-auth via ?session=...)
"""

import logging
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.logging_security import safe_headers, scrub_secrets_processor
from app.routers import (
    calls,
    calls_active,
    carriers,
    dashboard,
    dashboard_view,
    events,
    health,
    loads,
    telemetry,
    transcript_timeline,
)
from app.services.twin_client import twin_client


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Last line of defense — runs immediately before the renderer so
            # everything (event message, kwargs, contextvars) is scrubbed.
            scrub_secrets_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info(
        "startup",
        backend="twin",
        hr_base_url=settings.hr_base_url,
        api_key_configured=bool(settings.happyrobot_api_key),
    )
    yield
    twin_client.close()
    await twin_client.aclose()
    log.info("shutdown")


app = FastAPI(
    title="Robot API",
    version="0.0.2",
    description="Inbound carrier voice-agent backend (HappyRobot integration). Twin-backed.",
    lifespan=lifespan,
)


# --- request id middleware -------------------------------------------------
# Binds a `request_id` into structlog contextvars + scrubs sensitive headers
# before any other context is bound. Belt-and-suspenders with the structlog
# `scrub_secrets_processor`: raw `Authorization` / `x-api-key` values never
# reach the logger in the first place.

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            # Headers go through the safe_headers filter so Authorization /
            # x-api-key are redacted at bind time.
            headers=safe_headers(dict(request.headers)),
        )
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        return response


app.add_middleware(RequestContextMiddleware)


# --- 500 handler -----------------------------------------------------------
# Catches every unhandled exception. Logs the full traceback via structlog
# (which scrubs secrets en route) and returns a generic JSON body to the
# client. NEVER includes the original exception message — tracebacks can
# embed token values from headers, request bodies, or environment dumps.

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or "unknown"
    log.exception(
        "unhandled_exception",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


app.include_router(health.router)
app.include_router(loads.router)
# calls_active mounts /v1/calls/active — must register BEFORE calls.router
# (which has /v1/calls/{call_id}) so the literal path wins over the param.
app.include_router(calls_active.router)
# transcript_timeline mounts /v1/calls/{call_id}/timeline — register before
# calls.router for symmetry; FastAPI matches longest path first regardless,
# but ordering keeps the route table readable.
app.include_router(transcript_timeline.router)
app.include_router(calls.router)
app.include_router(carriers.router)
app.include_router(dashboard.router)
app.include_router(dashboard_view.router)
app.include_router(events.router)
app.include_router(telemetry.router)
