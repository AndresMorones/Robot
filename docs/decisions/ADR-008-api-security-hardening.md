# ADR-008: API Security Hardening — Header-Only Auth, Logging Hygiene, Transcript Opt-In

- **Status:** Accepted
- **Date:** 2026-04-28
- **Supersedes:** None
- **Superseded by:** None

## 1. Context

The take-home spec requires "API key authentication on all endpoints + HTTPS." The deployed FastAPI at `https://robot-api-andres-morones.fly.dev` already satisfies the bare requirement (Bearer auth + Fly's Let's Encrypt TLS). The user reframed scope mid-build to "production-ready solution that handles real broker data — not financial-grade, but hardened against typical web attackers."

A focused security review on the API surface surfaced three credible exfiltration paths that the bare-minimum implementation did not close:

1. **Tokens-in-URLs.** `app/deps.py::require_bearer` accepted a `?token=<value>` query-string fallback alongside the `Authorization` header. The fallback was originally added defensively in case HappyRobot tool nodes could not set custom headers on every tier. URL-borne credentials propagate into Fly access logs, Cloudflare logs, browser history, `Referer` headers, error pages, and screenshots — once leaked there, they are functionally permanent.
2. **Secrets in structured logs.** The structlog pipeline bound the full request `Authorization` header into contextvars and rendered any string that downstream code chose to log. An accidental `log.info("debug", request_headers=request.headers)` call, or an exception message that included the header, would emit the raw token value to stdout and from there to Fly's log stream.
3. **Transcript dump on Bearer alone.** `GET /v1/calls/{call_id}` returned the full transcript by default. A leaked Bearer token was sufficient to exfiltrate every recorded conversation — carrier names, MC numbers, equipment specifics, negotiation history.

The user explicitly capped scope: no token-rotation script, no dual-key window (`api_bearer_token_previous`), no rotation endpoint. Static rotation via Fly secrets is acceptable for a single-tenant take-home that does not handle financial data.

## 2. Decision

**Adopt a three-item hardening bundle: header-only auth, four-layer logging hygiene, and transcript opt-in.** Each item is independent but composes as defense-in-depth.

### Item 1 — Strip query-string Bearer fallback

`app/deps.py::require_api_key` accepts only `Authorization: Bearer <token>` or `x-api-key: <token>` headers. The `?token=` query-string mode is removed entirely. Both header paths use `hmac.compare_digest` for constant-time comparison. If HR ever hits a tier limitation that requires query-string auth, that becomes a Tier-2 reversal under a freshly rotated token.

### Item 2 — Logging hygiene (four layers)

1. **Token scrubber processor** (`app/logging_security.py::scrub_secrets_processor`) — a structlog processor mounted immediately before the JSON renderer. Walks every `event_dict` value (recursing into dicts and lists) and replaces matches of three patterns with `<redacted>`: HR `sk_live_...` keys, `Bearer <token>` header values, and the literal configured `API_BEARER_TOKEN` string.
2. **500 handler** (`app/main.py::unhandled_exception_handler`) — catches every unhandled exception. Logs the full traceback through structlog (which scrubs en route) and returns a fixed shape `{"detail": "Internal server error", "request_id": "<uuid>"}`. The original exception message never reaches the response body — tracebacks can embed token values from headers, request bodies, or environment dumps.
3. **Request middleware** (`app/main.py::RequestContextMiddleware` + `app/logging_security.py::safe_headers`) — strips `authorization`, `x-api-key`, `cookie`, and `set-cookie` header values before they are bound into contextvars. Belt-and-suspenders with the scrubber: the raw secret never enters the structlog state in the first place.
4. **Transcript opt-in** (`app/routers/calls.py::get_call_endpoint`) — `GET /v1/calls/{call_id}` accepts `include_transcript: bool = False`. Default behavior strips the `transcript` field from the response entirely. Caller must pass `?include_transcript=true` to get the full conversation. Even with a leaked Bearer, the casual transcript-dump path is closed.

### Item 3 — Tests + this ADR

`api/tests/test_security.py` covers the seven scenarios named in the user's brief plus three pure unit cases for the scrubber. See section 5.

## 3. Consequences

### Positive

- Token values cannot reach Fly access logs, `Referer` headers, browser history, or screenshots via URL.
- Accidental `log.info(headers=request.headers)` calls are safe — the scrubber catches them at the renderer boundary, the middleware filter catches them at bind time.
- Production `500` errors are stable in shape and free of leaked credentials.
- Bulk transcript exfiltration via a leaked Bearer requires deliberate flag-setting per request; the default endpoint shape is metadata-only.
- No breaking change for HR: every HR webhook + tool node uses headers (`x-api-key` or `Authorization`), and the dashboard's server-side fetch uses `Authorization: Bearer`.

### Negative

- If HR ever hits a tier limitation that blocks custom headers on a webhook, we have to either reverse this decision under a rotated token or proxy the call through an intermediate.
- Transcript opt-in adds a query-string knob that callers must remember; the dashboard's call drilldown view must explicitly pass `include_transcript=true`. (One frontend touch point — already accounted for.)
- The scrubber regex set is a moving target — every new credential shape (e.g. an FMCSA API key) needs an explicit rule.

### Neutral

- No new runtime dependencies. structlog + a small `logging_security` module cover the entire surface.
- The 500 handler is generic enough to apply to all unhandled exceptions across all routers.

## 4. Alternatives Rejected

- **Full token rotation system (`api_bearer_token_previous` + dual-acceptance window + rotation endpoint).** Explicitly out of scope per user override. Rotation is manual via Fly secrets; the dual-acceptance window is unnecessary for a single-tenant take-home where downtime during rotation is acceptable.
- **Mutual TLS.** Overkill for a single-tenant take-home. HR tool nodes do not natively present client certificates.
- **JWT / OAuth2.** Overkill for a single-shared-token deployment. Adds key-management surface (signing keys, refresh tokens) without addressing the actual leakage paths above.
- **Removing the `x-api-key` header path.** Kept because HR webhooks default to `x-api-key` rather than `Authorization` — removing it would force a HR-side change with no security benefit (both headers go through the same constant-time compare).
- **Always returning the transcript and gating via a separate per-role permission.** No role system exists in MVP. Opt-in via query param is the lightest-weight equivalent.

## 5. References

- `api/app/deps.py` — `require_api_key` (lines 25-43): header-only auth with constant-time compare.
- `api/app/logging_security.py` — `scrub_secrets_processor` (lines 56-64), `safe_headers` (lines 73-83).
- `api/app/main.py` — `configure_logging` (lines 63-78) wires the scrubber before the JSON renderer; `RequestContextMiddleware` (lines 113-130) binds redacted headers; `unhandled_exception_handler` (lines 142-155) returns the generic 500 shape.
- `api/app/routers/calls.py` — `get_call_endpoint` (lines 71-94): `include_transcript: bool = False` default + post-fetch field strip.
- `api/.env.example` (lines 5-12) — documents the header-only posture.
- `api/tests/test_auth.py` + `api/tests/test_security.py` — coverage.
- Spec clause: "API key authentication on all endpoints. HTTPS deployment." (`docs/FDE-TECHNICAL-CHALLENGE.md`).
- Memory: `project_production_improvements_locked.md` — production-ready scope direction (2026-04-28).
