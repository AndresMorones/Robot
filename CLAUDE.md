# Robot — Inbound Carrier Voice Agent

Take-home for HappyRobot (prospect: Carlos Becker): an inbound carrier voice agent for a freight brokerage. Carrier calls via HappyRobot web-call trigger → agent verifies MC with FMCSA, searches loads, negotiates up to 3 rounds, mocks a transfer, logs the call. Custom dashboard shows funnel/economics/operational/quality KPIs. Docker + Fly.io, HTTPS, Bearer auth.

Master plan (strategic reference, not frozen spec): `C:\Users\Andre\.claude\plans\now-i-want-you-fizzy-eagle.md`.

## Stack

- Backend: Python 3.12, FastAPI, pydantic v2, httpx, structlog, `uv` for packages.
- Frontend: Next.js 15 App Router, Tailwind 4, shadcn/ui (Radix primitives only — no Calendar/Popover), Recharts, `openapi-typescript`. Vanilla `useSearchParams` for URL-state filters; native `<input type="date">` for date picker. **No Tremor, no nuqs, no react-day-picker, no date-fns** — see ADR-011. Server-rendered HTML at `api/app/routers/dashboard_view.py` is legacy / fallback; Next.js (`dashboard/`) is the production deliverable as of 2026-04-28.
- Infra: Docker, Fly.io (region IAD), GitHub Actions.
- Observability: structlog JSON logs (live). OpenTelemetry traces + `prometheus_client` metrics — instrumented in code; backend wiring deferred to FastAPI/infra hardening pass (Tier-2).
- Voice platform: HappyRobot (workflow + voice agent + post-call extraction + negotiation logic — all configured in the HR UI by Andres; mirrored in `docs/references/happyrobot/`). Workflow: `inbound-carrier-v4` (forked from Version 3 of "Inbound Carrier Sales New").
- Our API endpoints (loads + dashboard): `GET /v1/loads/{reference_number}`, `GET /v1/loads/search`, `GET /v1/dashboard/{funnel,economics,operational,quality,observability,carriers}`. `POST /v1/calls/log` returns 410 Gone (HR Twin Write replaced it per ADR-005). `GET /v1/policy/defaults` + `GET /v1/carrier-profile/{mc}` are roadmap items, NOT implemented. All `/v1/*` endpoints Bearer-authed, HTTPS via Fly Let's Encrypt.

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
- Every request binds `request_id` into contextvars. When available, also bind `call_id`, `room_name`, `mc_number`, `load_id`.
- Manual OTel spans: `call_store.upsert`, `load_store.search`, `carrier_profile.aggregate`. FMCSA + negotiation are HR-side — no server-side span needed. Everything else is auto-instrumented.

**Tests**
- pytest + pytest-asyncio. One test file per router.
- Negotiation lives in HR's Python Code sidecar (`negotiate_evaluate` tool) — no server-side negotiation engine, no server-side tests for it.

**Data stores**
- HR Twin (Postgres-backed) is the canonical store for runtime per-call data; JSON files seed and mirror loads catalog.
- `data/loads.json` / `data/twin_seed_loads.sql` is the read-only seed for the `loads` table (20–30 loads covering all spec fields incl. `num_of_pieces`, `miles`, `dimensions`).
- `calls_log` (Twin) — one row per call, written post-call by HR Write-to-Twin (AI Extract → Case Health Score → Write-to-Twin chip). Read by `GET /v1/dashboard/*` + `GET /v1/carrier-profile/{mc}`.
- `bookings` (Twin, v15) — one row per booking, written mid-call by HR `book_load` tool fire → Write-to-Twin chip. Idempotency via `UNIQUE (call_id, load_id)`. Joined to `calls_log` on `call_id` and to `loads` on `load_id` at dashboard query time.
- `data/policy.json` (optional — for `GET /v1/policy/defaults`): tunable workflow policy values.
- `data/calls.json` is **no longer the canonical store** (legacy v13/v14 artifact). Twin `calls_log` + `bookings` replaced it post-v15.

**HR variable references**
- Use HR's `@` picker, never hand-type template references. HR needs the internal persistent_id UUID; hand-typed `{{var}}` or `{{trigger.var}}` silently renders as empty string at runtime.

## Where things live

- Strategic plan (architecture, risks, resolved decisions) → `C:\Users\Andre\.claude\plans\now-i-want-you-fizzy-eagle.md`
- Running dev journal → `docs/activity-log.md`
- Decisions with rationale + references → `docs/decisions/ADR-*.md`
- HappyRobot platform reference material (project-scoped) → `docs/references/happyrobot/`
- HappyRobot full-platform knowledge base (vendor-docs mirror, outside repo, never commit) → `C:\Users\Andre\happyrobot-kb\` (start at `MANIFEST.md`)

## What NOT to do

- Don't add a database. JSON stores are the spec.
- Don't mutate a published HappyRobot workflow — fork to a new version (Version 3 → `inbound-carrier-v4` done; HR workflows are immutable once published). Version 3 is the safe-rollback baseline.
- Don't re-implement FMCSA — use HR's demo endpoint at `https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}?webKey=...` directly from the `verify_carrier` webhook. We do NOT have our own `/v1/fmcsa/verify`.
- Don't put the negotiation state machine in Python-on-our-API. It lives in HR's `negotiate_evaluate` Python Code security sidecar (under the Prompt node). Sidecar pattern: the main Prompt cannot see floor/target/discount — prompt injection can't extract them. Policy is tunable via 4 HR workflow variables.
- Don't leak `API_BEARER_TOKEN` into the Next.js client bundle. Use `server-only` import in `dashboard/src/lib/api-client.ts`.
- Don't store prompts or negotiation policy in a database for MVP. HR workflow variables handle the 4 tunable values natively. Dynamic retrieval is a Tier-2 broker-doc roadmap item (optional `GET /v1/policy/defaults` endpoint as a minimal win).
- Don't hand-type HR variable references — use the `@` picker so HR inserts the correct persistent_id UUID.
- Don't pre-bake `.claude/` infrastructure (hooks, subagents, skills). Add them only when concrete friction justifies each one.

## Workflow with Claude Code

- Claude and Andres work step by step. Each step is its own planning + deep-dive + execution cycle.
- Every substantive action is logged to `docs/activity-log.md`.
- Non-trivial decisions get an ADR in `docs/decisions/` with rationale + references.
- HappyRobot platform work is always user-driven: Claude provides click-by-click instructions and a code alternative when one exists; Andres executes in the HR UI.
- Andres invites HR-platform questions at any point — ask rather than guess when the KB is silent or ambiguous, and record the answer into `C:\Users\Andre\happyrobot-kb\OPEN-QUESTIONS.md` (resolved section).
- Commits are small, file-scoped, conventional-commit style (`feat(api): add fmcsa verify endpoint`). Claude's pair-author attribution stays visible in the commit log.

## Developer setup

- Python 3.12 + `uv` for the API (`api/` package).
- Node 18+ for the HappyRobot MCP server (spawned via `npx` by Claude Code).
- `HAPPYROBOT_API_KEY` env var — generated at HR Settings → API Keys, set in the developer's local shell, **never committed**. Referenced by `.mcp.json` at repo root.
- `API_BEARER_TOKEN` env var — local test value for hitting `/v1/*`; real value lives in Fly secrets when deployed.
- `FMCSA_WEB_KEY` env var — obtained from FMCSA QCMobile portal; local `.env` in `api/`, Fly secret in prod.
