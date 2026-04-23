# Robot — Inbound Carrier Voice Agent

Take-home for HappyRobot (prospect: Carlos Becker): an inbound carrier voice agent for a freight brokerage. Carrier calls via HappyRobot web-call trigger → agent verifies MC with FMCSA, searches loads, negotiates up to 3 rounds, mocks a transfer, logs the call. Custom dashboard shows funnel/economics/operational/quality KPIs. Docker + Fly.io, HTTPS, Bearer auth.

Master plan (strategic reference, not frozen spec): `C:\Users\Andre\.claude\plans\now-i-want-you-fizzy-eagle.md`.

## Stack

- Backend: Python 3.12, FastAPI, pydantic v2, httpx, structlog, `uv` for packages.
- Frontend: Next.js 15 App Router, shadcn/ui, Recharts, `openapi-typescript`.
- Infra: Docker, Fly.io (region IAD), GitHub Actions.
- Observability: structlog JSON logs, OpenTelemetry traces, `prometheus_client` metrics.
- Voice platform: HappyRobot (workflow + voice agent + post-call extraction — all configured in the HR UI by Andres; mirrored in `docs/references/happyrobot/`).

## Conventions (flexible preferences — deviate if there's a good reason)

**Architecture**
- Pydantic models in `api/app/models/` hold request/response shapes only. Internal DTOs live alongside their services.
- Routers are thin: parse, call a service, return. Business logic is in `api/app/services/`.
- Services are pure where feasible (negotiation engine is fully deterministic + unit-tested).

**Auth**
- All `/v1/*` endpoints require `Authorization: Bearer <token>` **or** `?token=<token>` query-string (defensive fallback — HR tool nodes may not support custom headers on every tier).
- `app/deps.py::require_bearer` handles both modes; constant-time compare.
- No JWT, no OAuth. Single shared token, rotatable via Fly secret.

**Logging + observability**
- structlog only for application logs. No `print`, no stdlib `logging` in business code.
- Every request binds `request_id` into contextvars. When available, also bind `call_id`, `mc_number`, `load_id`.
- Four manual OTel spans: `fmcsa.fetch`, `negotiation.evaluate`, `call_store.upsert`, `load_store.search`. Everything else is auto-instrumented.

**Tests**
- pytest + pytest-asyncio. One test file per router, one per service.
- FMCSA tests use fixtures in `data/fmcsa-fixtures/` — never the live API.
- Negotiation engine is covered by parametrized cases spanning every branch.

**Data stores**
- JSON files only — spec requirement, not a workaround.
- `data/loads.json` + `data/load-policies.json` are read-only at runtime.
- `data/calls.json` is appended by the API (file lock + atomic tmp-rename); in prod it lives on a Fly volume.

## Where things live

- Strategic plan (architecture, risks, resolved decisions) → `C:\Users\Andre\.claude\plans\now-i-want-you-fizzy-eagle.md`
- Running dev journal → `docs/activity-log.md`
- Decisions with rationale + references → `docs/decisions/ADR-*.md`
- HappyRobot platform reference material → `docs/references/happyrobot/`

## What NOT to do

- Don't add a database. JSON stores are the spec.
- Don't cache FMCSA beyond 48h — dormant/revoked authorities happen; freshness matters.
- Don't mutate a published HappyRobot workflow — create a `-v2` (HR workflows are immutable once published).
- Don't put the negotiation state machine in the HR workflow. It lives in `api/app/services/negotiation.py` so policy changes don't require republishing HR.
- Don't leak `API_BEARER_TOKEN` into the Next.js client bundle. Use `server-only` import in `dashboard/src/lib/api-client.ts`.
- Don't pre-bake `.claude/` infrastructure (hooks, subagents, skills). Add them only when concrete friction justifies each one.

## Workflow with Claude Code

- Claude and Andres work step by step. Each step is its own planning + deep-dive + execution cycle.
- Every substantive action is logged to `docs/activity-log.md`.
- Non-trivial decisions get an ADR in `docs/decisions/` with rationale + references.
- HappyRobot platform work is always user-driven: Claude provides click-by-click instructions and a code alternative when one exists; Andres executes in the HR UI.
- Commits are small, file-scoped, conventional-commit style (`feat(api): add fmcsa verify endpoint`). Claude's pair-author attribution stays visible in the commit log.
