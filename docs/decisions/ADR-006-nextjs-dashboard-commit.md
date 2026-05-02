# ADR-006: Commit to Next.js for the Production Dashboard

- **Status:** Accepted
- **Date:** 2026-04-28
- **Supersedes:** Implicit "MVP-HTML-only" narrative; explicitly supersedes the "HTML is final" framing captured in `project_dashboard_html_decision.md` memory
- **Superseded by:** None

## 1. Context

The FDE take-home spec (`docs/FDE-TECHNICAL-CHALLENGE.md`, Objective 2 + Deliverable 3) requires a custom dashboard surfacing call-funnel, economics, operational, and quality KPIs. The spec is tech-stack-agnostic — both a server-rendered HTML view and a SPA satisfy the literal requirements.

Two days ago we shipped an HTML-only dashboard at `api/app/routers/dashboard_view.py` as the MVP path. That code is working, spec-compliant, and reads from the same FastAPI `/v1/dashboard/*` endpoints we'd consume from any client.

On 2026-04-28 PM, the user shifted scope from "MVP-minimum" to "production-ready" and committed to Next.js 15 + shadcn/ui + Recharts + openapi-typescript. The unwritten-but-real expectations now driving the dashboard:

- SaaS-grade visual polish (matters for FDE evaluation)
- Mobile responsive layout
- Component reuse (KPI cards, tables, drilldown panels)
- Charts via Recharts rather than hand-rolled SVG
- Type-safe end-to-end via `openapi-typescript` consuming the FastAPI OpenAPI schema
- Demo readiness for Carlos Becker + the HappyRobot review team

The HTML view stays in the codebase as a Tier-2 fallback / dev preview during the cutover and may be retired or repurposed as `/admin` after the Next.js deploy is verified live.

## 2. Decision

**Build the production dashboard as a Next.js 15 App Router project at `dashboard/`. Deploy as a separate Fly.io app named `robot-dashboard-andres-morones`.**

- React Server Components handle all data fetching; no client-side fetches against the FastAPI surface.
- Bearer auth uses a `server-only` import in `dashboard/src/lib/api-client.ts` so the token never reaches the browser bundle.
- The HTML view at `api/app/routers/dashboard_view.py` is retained temporarily as a legacy fallback / dev preview.
- Single source of truth for data remains the FastAPI `/v1/dashboard/*` endpoints reading the HR Twin Postgres tables (`calls_log`, `bookings`, `loads`).

## 3. Consequences

### Positive

- Production-grade visual quality matching the scope shift.
- Mobile responsive out of the box via Tailwind + shadcn defaults.
- Recharts gives funnel, economics, quality, and trend charts without custom SVG work.
- End-to-end type safety from `openapi-typescript` — schema drift surfaces at build time.
- Demo polish materially affects FDE evaluation (subjective but real).
- Clean architectural narrative: "FastAPI is JSON-first, Next.js consumes; one source of truth via Twin."

### Negative

- Two Fly apps to deploy and maintain — one extra deployment surface.
- `npm install` adds a build step and a Node toolchain dependency.
- Roughly 6-8 hours of additional Claude-time vs. an HTML-only path.
- HTML view still in code → temporary dual-dashboard state until cutover (small, time-bound tech debt).

### Neutral

- Bearer auth chain is unchanged: browser → Next.js Server → FastAPI → Twin. No security regression.
- Voice-agent 28-language coverage is a separate concern, unaffected.

## 4. Alternatives considered

**A. Stay with the HTML server-rendered view (`dashboard_view.py`).** Already built, working, spec-compliant; shortest time-to-ship. Rejected because the production-ready scope shift makes polish a soft requirement, and an HTML view reads as "internal admin tool" rather than "deployed SaaS product."

**B. Streamlit / Gradio.** Faster scaffold than Next.js. Rejected because the UX is not production-grade, the Bearer-auth integration is awkward, and the result reads as a prototype tool to a reviewer.

**C. Static HTML + HTMX.** Compromise between vanilla HTML and an SPA. Rejected because it still requires custom CSS work, loses end-to-end type safety, and the charts story remains weak.

## 5. Rollout plan

1. Scaffold Next.js 15 App Router at `dashboard/` — DONE 2026-04-28.
2. Wire 4 KPI tabs + calls list + carriers list + carrier drilldown — DONE 2026-04-28.
3. Add 3 missing FastAPI endpoints (calls list, call by id, carrier by mc) — IN PROGRESS (Agent 1).
4. Update Pydantic models to v15 schema — IN PROGRESS (Agent 2).
5. `npm install` + `npm run build` locally — pending user.
6. Deploy to Fly.io as `robot-dashboard-andres-morones` — pending user.
7. Smoke-test live with real Twin data — pending.
8. Demo prep + 5-min Loom walkthrough — pending.
9. Once Next.js is verified live, retire the HTML view at `dashboard_view.py` — Phase 7 polish.

## 6. Open questions / risks

- **First Next.js deploy could fail** on TypeScript drift or dependency resolution — mitigate with `npm run typecheck` + local `npm run build` pre-flight before `fly deploy`.
- **Missing FastAPI endpoints gate the calls + carriers pages** — coordinated with Agent 1; cutover blocked on those landing.
- **Bearer auth secret must match in both Fly apps** — easy to miss; documented in SPEC-005 deployment notes.
- **HTML view stays in code temporarily** — risk of confusion about which surface is canonical; this ADR is the resolution.

## 7. References

- FDE spec: `docs/FDE-TECHNICAL-CHALLENGE.md`
- Current architecture map: `docs/hr-architecture-map.md`
- ADR-005: two-table booking pattern (precursor decision)
- Memory: `project_dashboard_nextjs_committed.md`
- Memory: `project_dashboard_html_decision.md` (now superseded — historical reference)
