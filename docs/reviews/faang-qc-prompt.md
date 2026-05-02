# FAANG-grade QC review prompt

Run this against the dashboard build and any dashboard-touched FastAPI before signing off the production polish phase. **Non-skippable** per `memory/project_dashboard_qc_gate_faang.md`.

## Severity rubric

- **BLOCKING** — must fix before sign-off. Reviewer-visible defect, security gap, accessibility regression, or anti-pattern that compromises the demo or production trust.
- **SHOULD-FIX** — fix during this pass if cost is bounded; otherwise file to backlog with rationale.
- **NICE-TO-HAVE** — document and defer; do not block sign-off.

## Review surface

Audit `dashboard/src/**` (every file modified or created in the polish pass) plus any `api/app/{routers,services}/**` touched. Reference both registers as the source of truth for scope:
- `docs/dashboard-final-prod-register.md`
- `docs/hr-twin-pending-register.md`

## Review checklist (audit each section, surface findings)

### 1. Locked spec compliance

For every item in the master register §1 (locked theme), §2 (locked telemetry widgets), §3 (locked Call Logs tab spec):
- Was the spec implemented? Cite file + line.
- Are tokens / fonts / row heights / radii / accent colors all matching verbatim?
- Are the locked sub-question defaults (composite §1.9) all honored?

Findings format:
- `BLOCKING — TB-1: globals.css line 80 still uses --primary: 36 95% 56% (amber). Locked spec is --primary: #FFFFFF.`

### 2. Sign convention + numerical correctness

- Are `$ delta` signs consistent across `EconomicsCards`, `EffectiveDeltaChart`, `SalesRepCard`, `CallDetail` per CT-8?
- Is "negative = good" applied uniformly?
- Are percentages rendered to consistent precision (1 decimal in charts, 0 decimals in KPI tiles)?
- Is `$` formatted with thousand separators?
- Are nulls rendered as `—` (em-dash), not `null` / `undefined` / `0`?

### 3. ADR honesty contracts

- ADR-012: Is `<CallTelemetry>` reading dashboard-computed p70/p90 (NOT raw HR NULL columns)? Is the disclosure tooltip ("computed from transcript") present?
- ADR-009: Is `<LiveRefresh />` connected to SSE with 5min ISR fallback? Is `invalidate_dashboard_cache()` called from the webhook receiver?
- ADR-007: Is the FastAPI `cachetools.TTLCache` 30s? Is the Next.js `revalidate` aligned?
- ADR-008: Is the call detail endpoint stripping transcript by default (`include_transcript=true` opt-in)?
- ADR-011: No new dependencies (no nuqs, no Tremor, no react-day-picker, no popover, no date-fns)?
- ADR-013: Are aggregate reads going through the Twin SoT cache + REST API drilldown — NOT live HR REST API for aggregate metrics?

### 4. Accessibility (audit both light + dark mode)

- Color contrast ≥ 4.5:1 for all body text on intended background.
- Color is never the only signal — every conditional-color cell also carries an icon, a sign, or a label.
- Focus rings visible in both modes (AX-5).
- Skeletons on every chart that fetches (AX-2).
- Empty states: no blank tabs — explanatory copy present (AX-3).
- Keyboard navigation: tab order matches visual order; no traps; Cmd-K opens with `⌘K`.

### 5. Security

- No `Authorization: Bearer ...` token leaks into the client bundle. `api-client.ts` must `import "server-only"`.
- No PII (full transcripts, MC numbers, phone numbers) in `console.log`, in URLs, or in error responses.
- No raw SQL strings interpolated from user input.
- HR + FMCSA API keys never exposed in `.env.example` (only the env var name).
- Dashboard signed-link auth (the 30-day URL token) verified working.

### 6. Performance

- Server Components by default; `"use client"` only on Recharts components, Cmd-K, and other genuinely interactive surfaces.
- `Promise.all` parallelism in page.tsx data fetches.
- `<Suspense>` boundaries split the page into independent hydration zones.
- Recharts: `<ResponsiveContainer>` with explicit aspect ratio; no animation jank on tab switch.
- Empty-state and loading paths render in <50ms (no layout-shift).

### 7. Reviewer-readable polish (the "looks finished" tells)

- No docs-style copy ("This metric measures..."). Tight, operational prose.
- No raw variable names exposed in titles (`mc_number`, `case_health_score`, `pitched_loadboard_rate`).
- No "Why this matters" subtitles.
- No triple-duplicate metrics (per CT-9).
- Active-calls indicator says "Verifying carrier" / "Searching loads" — not raw `current_node` jargon.
- KPI `(median)` chip on aggregate metrics whose mean is fragile (per QO-4).
- Inline margin sub-line under Booked-rate-avg KPI (per QO-5).

### 8. State + interaction discipline

- All filter state is URL-encoded (per ADR-011 / KF-6) — refresh-stable.
- Cmd-K palette mounted as a portal at `app/layout.tsx`; opens with `⌘K`; closes on Esc + outside-click.
- Cross-filter on chart click (KF-4) is DEFERRED — verify it's not silently broken (no half-implemented click handlers).
- DateRangePicker uses native `<input type="date">` (no react-day-picker) per ADR-011.

### 9. Test coverage

- `cd api && uv run pytest tests/ -x` passes 138+ tests.
- `cd dashboard && npx tsc --noEmit` produces ONLY the 5 pre-existing `outcome` field errors (or zero).
- No new TS `any` types introduced.

### 10. Drift findings (D1-D18 from Phase B audit)

For each finding in master register §6, surface current status:
- D1-D7 (HIGH severity): explicitly mark RESOLVED / OPEN / VERIFY.
- Cite a file + line for each RESOLVED finding.

### 11. Comments + code hygiene

- No `// TODO` left in production paths without a register cross-ref.
- No commented-out code blocks ≥ 3 lines.
- No `console.log` / `print` debug breadcrumbs.
- All `noqa` / `# type: ignore` carries a one-line justification.

### 12. Submission readiness

- README accurately reflects the current architecture and deploy steps.
- `docker-compose.yml` at repo root (per `project_carlos_email_artifacts.md`).
- `.env.example` complete and current.
- `data/` seeds reproducible from a clean clone.
- Fresh signed link works against a freshly-deployed Fly app.

## Output format

Return a single markdown report `docs/reviews/faang-qc-findings-<date>.md` with:

1. **Executive summary** (≤ 5 lines): pass/fail status, BLOCKING count, surprising findings.
2. **BLOCKING findings** (must fix): one entry per finding, with `file:line`, severity rationale, suggested fix.
3. **SHOULD-FIX findings**: same shape, lighter rationale.
4. **NICE-TO-HAVE findings**: bullet list with file references.
5. **Sign-off block**: Either `✅ Sign-off — no BLOCKING findings` OR `❌ Sign-off blocked — N BLOCKING findings`.

Do not sign off until all BLOCKING findings are resolved or explicitly scope-cut by user direction.
