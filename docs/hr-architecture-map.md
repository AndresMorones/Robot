HR ARCHITECTURE MAP — v19 (interim snapshot, several upgrades pending)

Tracking each HR component's current configuration as we wire it. Source of truth for "what's actually there" vs the design docs.

Last updated: 2026-04-30 — INTERIM. Several upgrades are queued (notes column, sales-rep operational view, real-time negotiation webhook, super-test, Postgres migration, field renames, load-status lifecycle) that will change the final architecture. Each is flagged inline as PENDING.

Companion doc: `docs/services-integration.md` (cross-service architecture + auth chain + per-call traces).

============================================

CURRENT STATE SUMMARY

- SHIPPED + VERIFIED: HR workflow at v19 (id `019ddc83-70c2-7f1e-bc03-b1232a6e07ed`, workflow id `019db77a-0548-741c-9ac8-d713bea1a51f`). All 4 custom tools (verify_carrier, query_loads, negotiate_rate, book_load) + HR built-in `_hangup` wired. Post-call chain (AI Extract → Case Health Score → Update Data in Record) writing calls_log. Twin tables loads (150 rows seeded), calls_log (15-col live shape), bookings (6-col live shape with UNIQUE(call_id, load_id)). Voice Agent Prompt v5.1 written; user has applied v5.2 edits on top of v5.1 in HR (the v5.2 patch set is not fully captured in repo). FastAPI surface at 18+ endpoints. Next.js 15 dashboard live with 4 KPI tabs + 2 feeds + sales-rep tab. Caching (ADR-007 + ADR-009): Next.js ISR `revalidate=300` + FastAPI TTLCache(ttl=30s) + webhook/SSE push. Auth header-only per ADR-008.
- VERIFIED LIVE 2026-04-30: `mc_number` was NULL on prior calls; user wired the @ picker fix to bind verify_carrier output correctly on 2026-04-30. CONFIRM via `SELECT mc_number FROM calls_log WHERE created_at > '2026-04-30'` next time Twin probe is available.
- INTERIM-PENDING UPGRADES (will change final architecture — see PENDING UPGRADES section): notes TEXT column, sales-rep operational view + dummy mimic-accept, real-time negotiation webhook + SSE counter/floor visibility, super-test workflow, Postgres migration, field renames pitched_loadboard_rate→original_rate / agreed_rate→apply_rate, load-status lifecycle.
- LAST VERIFIED AGAINST TWIN: 2026-04-28 (calls_log + bookings + loads). Live HR/Twin probe NOT possible from this session — facts below pulled from authoritative session brief + repo ground-truth.

============================================

WORKFLOW

Name: inbound-carrier-v19 (forked v18 → v17 → v16 → v15 → v14 → v13 of "Inbound Carrier Sales New")
Workflow ID: `019db77a-0548-741c-9ac8-d713bea1a51f`
Latest version: v19 (`019ddc83-70c2-7f1e-bc03-b1232a6e07ed`)
Status: Development environment (production publish gated on super-test workflow run)
Web call URL: see docs/references/happyrobot/web-call-url.txt
Languages enabled: 28 (intentionally KEEP all per user direction 2026-04-28; F10 will not be narrowed)

WORKFLOW VARIABLES

- agent_name (string, default "Paul")
- company_name (string, default "Acme Logistics")
- negotiation_floor_pct (number, default 0.10)
- max_negotiation_rounds (number, default 3)
- Time.Now (system, US Eastern, human format)

WORKFLOW WEBHOOKS (Option C push pipeline — ADR-009)

- Event: call.ended
  URL: https://robot-api-andres-morones.fly.dev/v1/events/call-ended
  Method: POST
  Body (JSON, "Preserve data types" ON):
    { "call_id": "<@ Voice Agent.call_id>", "run_id":  "<@ System.run_id>", "time": "<@ System.time.now_utc>" }
  Authorization: Bearer Token (value = API_BEARER_TOKEN Fly secret on robot-api)
  Error Handling: "Gracefully handle 5XX errors" ON; XSS protection ON; default retries (~100s envelope)
  Variable bindings: ALWAYS use the @ picker — hand-typed `{{var}}` renders empty.
  Effect: invalidates dashboard TTLCache + fans `call-ended` event to SSE subscribers.

PENDING (real-time channel — see PENDING UPGRADES § "Real-time negotiation webhook"): a second `negotiation.counter` event will fire mid-call from the negotiate_rate sidecar, surfacing counter offer + final_floor to the sales-rep dashboard via the same SSE bus.

DRIFT FROM PRIOR VERSIONS (v17 → v18 → v19)

The 2026-04-28 architectural review (against v17) flagged BLOCKING issues that were corrected in v18+. Re-verify each on v19 next live probe:

- F1 (book_load missing Write-to-Twin child) — RESOLVED in v18 fork; verify v19 still has the child wired.
- F2 (Voice Agent Prompt body duplicated) — RESOLVED in v18; v19 carries v5.1 + user v5.2 edits — verify no re-duplication on the latest paste.
- F3 (calculate_rate `now`/`now_iso` key mismatch) — RESOLVED 2026-04-28 (Python reads both keys); persists clean in v19.
- Log Event call_id binding (was wired to wrong @ picker on v17) — verify on v19; mc_number-NULL bug (resolved on 2026-04-30) was the same class of @-picker mis-binding.
- v18 → v19 fork: new fork may inherit stale bindings or persistent_id references from v18. Re-validate every @-picker on v19's Voice Agent + Update Data in Record + book_load nodes before production publish.

============================================

VOICE AGENT NODE

Initial message: "Thank you for calling {{ company_name }}, this is {{ agent_name }}. How can I help?" (Variables bound via @ picker.)

PROMPT CHILD NODE

Body (repo ground truth): `prompts/voice-agent-system-prompt-v5.1.md` (v5.1 RLHF-tuned synthesis written 2026-04-29).
Live HR state: v5.1 pasted + user has applied v5.2 edits on top inside the HR UI (not all v5.2 patches are captured in the repo file).
Status: PUBLISHED TO DEVELOPMENT ENV.
PENDING: production publish + a `<notes_capture>` section in the prompt (see PENDING UPGRADES § "notes column").

Earlier prompt revisions (kept in `prompts/` for diff history): v1 → v2 → v3 → v4 (v4.3 was the v15-shipping body) → v5 → v5.1 → user-edited v5.2 (HR-only).

============================================

TOOLS UNDER VOICE AGENT → PROMPT

1. verify_carrier
   Status: SHIPPED + VERIFIED ✓
   Type: Predefined Webhook → FMCSA mobile.fmcsa.dot.gov demo endpoint
   Params: mc_number (string)
   Note: F11 (FMCSA API key in plaintext URL) remains PENDING (Tier-2 security hardening).

2. query_loads
   Status: SHIPPED + VERIFIED ✓
   Type: Tool → Read-from-Twin child
   Params: load_id, origin_state, origin_city, destination_state, destination_city, equipment_type (enum), pickup_window (ISO 8601) — all optional
   Read-from-Twin filters: `equals` per param (skip if empty). Filter column is `load_id` (NOT `reference_number` — verified 2026-04-28).
   Sort: pickup_datetime ASC. Row cap: 25.
   PENDING: when load-status lifecycle ships, add `status equals 'available'` filter — see PENDING UPGRADES.

3. negotiate_rate
   Status: SHIPPED + VERIFIED ✓
   Type: Tool → Run Python child (calculate_rate)
   LLM-facing params: loadboard_rate (number), pickup_datetime (string)
   Python Input Data bindings: loadboard_rate, pickup_datetime, negotiation_floor_pct (workflow var), now (← Time.Now)
   Python: `scripts/hr-tools/calculate_rate.py`. Reads both `now` and `now_iso` keys (F3 fix retained).
   Output: final_floor, urgency_tier, hours_until_pickup, base_floor_pct, urgency_drop, final_floor_pct (capped 0.5)
   PENDING (real-time negotiation webhook): sidecar will additionally POST counter offer + final_floor to /v1/events/negotiation-counter so the sales-rep dashboard can surface live mid-call state.

4. book_load
   Status: SHIPPED + VERIFIED ✓ (4 rows on v15 E2E; UNIQUE(call_id, load_id) caught a duplicate insert)
   Type: Tool → Write-to-Twin child (direct Twin write, no external webhook)
   Tool params (3, all required): load_id (string), mc_number (string), apply_rate (integer)
   Write target: bookings table
   Column map (4 bindings): call_id ← @Voice Agent.call_id; mc_number ← @book_load.mc_number; load_id ← @book_load.load_id; apply_rate ← @book_load.apply_rate
   Idempotency: Twin UNIQUE(call_id, load_id) → duplicate inserts return DB error → tool failure → prompt retry/fallback path.
   PENDING (load-status lifecycle): book_load will additionally flip `loads.status = 'booked'` + stamp `booked_at` + `booked_by_call_id`.
   PENDING (field renames): tool param `apply_rate` will stay; column rename `pitched_loadboard_rate→original_rate` + `agreed_rate→apply_rate` for legacy paths is queued.

5. _hangup (HR built-in)
   Status: WIRED in v5.1 prompt (terminal-tool pattern) — agent calls `_hangup` after the closing line on every terminal path (booked + handoff, FMCSA decline, polite walk, fallback close, hostile end).

============================================

POST-CALL CHAIN (after Voice Agent ends)

Order: AI Extract → Case Health Score (CHS) → Update Data in Record (writes calls_log)

NODES:

A. AI Extract (post-call)
   Status: SHIPPED + VERIFIED ✓
   Mode: JSON Schema strict (Azure structured outputs — every property in `required`, optionals nullable, `additionalProperties: false`)
   Schema: `prompts/ai-extract-schema-v3.md` (v3.2)
   Fields (2): call_outcome, fmcsa_eligibility_failure_reason
   Input: @ Voice Agent.transcript
   PENDING: add `notes` field (free-form transcript-derived call notes) when the notes column lands.

B. Case Health Score
   Status: SHIPPED + VERIFIED ✓
   Schema: emits 3 fields — case_health_score (0–100), audit_remarks (string), sentiment (enum)
   Input: @ Voice Agent.transcript

C. Update Data in Record (calls_log) — was labelled "Write-to-Twin (calls_log)" in v15 design
   Status: SHIPPED + VERIFIED ✓
   Target: calls_log (15 cols — see TWIN TABLES below)
   Column map: call_id ← @Voice Agent.call_id; mc_number ← @verify_carrier.content.carrier.mc; call_outcome ← @Extract.response.call_outcome; sentiment ← @CHS.response.sentiment; case_health_score ← @CHS.response.case_health_score; audit_remarks ← @CHS.response.audit_remarks; fmcsa_eligibility_failure_reason ← @Extract.response.fmcsa_eligibility_failure_reason; callback_phone ← @Voice Agent.from_number; duration_seconds ← @Voice Agent.duration; transcript ← @Voice Agent.transcript; intermediate_response_count ← @Voice Agent.intermediate_response_count; p70_intermediate_fired ← @Voice Agent.p70_intermediate_fired; p90_intermediate_fired ← @Voice Agent.p90_intermediate_fired; created_at ← omit (DB default).
   PENDING: `notes` ← @Extract.response.notes mapping when the notes upgrade ships.

D. Transfer Popup (Initiate New Contact)
   Status: CONFIGURED (mock transfer per spec; v5.1 prompt scripts the sales-rep handoff line just before this fires).

============================================

TWIN TABLES (Postgres, in HR Twin REST gateway — fronted by Cloudflare WAF)

1. loads
   Status: RESEEDED 2026-04-28 — 150 rows from refreshed `data/loads.csv` (May 2026 → Oct 2030, weighted heavy May–Aug).
   Schema (18 cols): id, created_at, reference_number, origin_city, origin_state, destination_city, destination_state, pickup_datetime, delivery_datetime, equipment_type, loadboard_rate, weight, commodity_type, num_of_pieces, miles, dimensions, notes, posted_at
   Filter column for query_loads: `load_id` (renamed from `reference_number` 2026-04-28).
   Read by: query_loads (HR Read-from-Twin child) AND FastAPI /v1/loads/* (legacy + alias paths).
   PENDING (load-status lifecycle): `status` (TEXT, default 'available'), `booked_at` (TIMESTAMPTZ), `booked_by_call_id` (TEXT) columns will be added; query_loads will filter `status = 'available'`.

2. calls_log
   Status: SHIPPED + VERIFIED ✓
   Schema (15 cols, live as of 2026-04-30): id, created_at, call_id (UNIQUE), mc_number, call_outcome, sentiment, case_health_score, audit_remarks, fmcsa_eligibility_failure_reason, callback_phone, duration_seconds, transcript, intermediate_response_count, p70_intermediate_fired, p90_intermediate_fired
   Written by: Update Data in Record node in post-call chain.
   PENDING: `notes` TEXT column (column name LOCKED 2026-04-30) — paired Extract param + prompt `<notes_capture>` section.
   PENDING: re-verify `mc_number` is non-NULL on calls created after 2026-04-30 (the @ picker fix for the verify_carrier binding landed that day; prior calls had NULL mc_number).

3. bookings
   Status: SHIPPED + VERIFIED ✓ (idempotency constraint exercised live)
   Schema (6 cols + UNIQUE(call_id, load_id)): id, created_at, apply_rate, call_id, mc_number, load_id
   Written by: Write-to-Twin child under book_load tool (mid-call).
   Indexes: idx_bookings_created_at, idx_bookings_call_id, idx_bookings_mc_number, idx_bookings_load_id.

============================================

FASTAPI ENDPOINT SURFACE (Fly.io: robot-api-andres-morones.fly.dev)

App entry: `api/app/main.py`. Auth via `app/deps.py::require_api_key`: header-only — `Authorization: Bearer <token>` OR `x-api-key: <token>`, constant-time compare. The legacy `?token=` query-string fallback was REMOVED per ADR-008.

Loads (HR webhook + alias):
- GET /loads/{reference_number} — auth
- GET /loads/search — auth
- GET /v1/loads/{reference_number} — auth (alias)
- GET /v1/loads/search — auth (alias)

Calls (read-only Twin reflection):
- GET /v1/calls?limit=N — auth (transcript omitted in list view)
- GET /v1/calls/{call_id} — auth (single call + bookings + load lane)
- POST /v1/calls/log — 410 Gone (deprecated; HR Write-to-Twin owns writes)
- POST /calls — 410 Gone (legacy alias)
- GET /v1/calls/active — auth (in-flight call indicator, HR Monitor proxy)

Carriers (per-MC rollups):
- GET /v1/carriers?limit=N — auth
- GET /v1/carriers/{mc_number} — auth

Dashboard aggregations (TTLCache-wrapped):
- GET /v1/dashboard/funnel — auth
- GET /v1/dashboard/economics — auth
- GET /v1/dashboard/operational — auth
- GET /v1/dashboard/quality — auth
- GET /v1/dashboard/calls — auth
- GET /v1/dashboard/loads — auth

Push pipeline (ADR-009):
- POST /v1/events/call-ended — auth (Bearer; idempotent on call_id, 5-min window)
- POST /v1/events/session — auth (mints one-shot opaque session token, 60s TTL)
- GET /v1/events/stream — session-auth via `?session=<token>` (EventSource cannot send headers)

Infra / view:
- GET /healthz — no auth (Fly healthcheck)
- GET /docs — no auth (Swagger UI)
- GET /dashboard — no auth (legacy server-rendered HTML, no PII; retained as fallback per ADR-006)

PENDING: POST /v1/events/negotiation-counter — receives mid-call counter offer + final_floor from negotiate_rate sidecar, fans to SSE for sales-rep dashboard.

============================================

PYDANTIC MODELS (`api/app/models.py`)

- CallRecord — mirrors live calls_log shape; all fields nullable (abandoned calls / partial Extract leave columns NULL). PENDING: add `notes` field when calls_log.notes column lands.
- EconomicsMetrics — includes effective_delta_dollars + effective_delta_pct (avg_apply_rate − avg_loadboard_rate; negative = broker upside).
- OperationalMetrics — avg_duration_seconds, fmcsa_decline_pct, abandon_rate_pct.
- QualityMetrics — outcome_distribution + chs_distribution + sentiment_distribution.
- CarrierRollupRow / CarrierRollupMetrics — for /v1/carriers responses.

============================================

DASHBOARD ARCHITECTURE

A. Next.js 15 App Router (`dashboard/`, deploy target `robot-dashboard-andres-morones`) — PRODUCTION DELIVERABLE per ADR-006.
   Stack: Next.js 15 + Tailwind 4 + shadcn/ui (Radix primitives only, no Calendar/Popover) + Recharts + openapi-typescript. Vanilla `useSearchParams` URL-state filters; native `<input type="date">`. No Tremor / nuqs / react-day-picker / date-fns (ADR-011).
   Auth: `server-only` import in `dashboard/src/lib/api-client.ts` so `API_BEARER_TOKEN` never hits the browser bundle.

   Pages (live):
   - `/dashboard` — Overview: 6 KPI cards + Effective-Delta hero chart + 4 tabs (Funnel, Economics, Operational, Quality)
   - `/dashboard/calls` — recent-calls feed
   - `/dashboard/calls/[call_id]` — single-call drilldown
   - `/dashboard/carriers` — top-N MC rollup feed
   - `/dashboard/carriers/[mc]` — single-MC drilldown
   - `/dashboard/sales` — sales-rep persona view (rolling 24h default; recent bookings + available loads)

   Layout: shared header + DateRangePicker + `<LiveRefresh />` SSE subscription (calls `router.refresh()` on `call-ended`).

   PENDING (sales-rep operational view): expand the existing /dashboard/sales surface with a dummy mimic-accept widget — UI-only, NO backend write (Tier-1 demo polish).

B. HTML legacy view (`api/app/routers/dashboard_view.py`, served at /dashboard on the API app)
   Status: RETAINED as fallback / dev preview per ADR-006. Will be retired post-Next.js production verification.

============================================

CACHING + FRESHNESS LAYERS

Layer 1 — Next.js ISR (`export const revalidate = 300`): cached HTML at the Next.js edge for 5 minutes. ISR is the dropped-event fallback; webhook+SSE drives live freshness.

Layer 2 — FastAPI TTLCache (cachetools, ttl=30s, maxsize=128): wraps 9 aggregation functions in `api/app/services/dashboard_aggregations.py`. `invalidate_dashboard_cache()` is called from `POST /v1/events/call-ended` on every webhook receipt. Per-key asyncio.Lock prevents stampedes.

Layer 3 — Webhook + SSE push (ADR-009):
- HR `call.ended` workflow webhook → POST /v1/events/call-ended (Bearer; idempotent on call_id over 5-min window).
- In-process pubsub (`api/app/services/event_bus.py`) — module-level set of asyncio.Queue subscribers, maxsize=100 each.
- Browser → POST /api/events/session (Next.js Route Handler proxy adds Bearer) → opens `EventSource('/api/events/stream?session=<one-shot opaque token, 60s TTL>')`.
- `<LiveRefresh />` in `dashboard/src/app/dashboard/layout.tsx` subscribes once for all dashboard tabs; calls `router.refresh()` on each `call-ended` event.
- Multi-machine constraint: in-process pubsub doesn't fan across Fly machines. Single-machine MVP only; Tier-2 escape = Redis pubsub (~1 hr swap).

Combined effect: ~95–99% reduction in Twin query load on the dashboard hot path. Staleness ceiling: ~1–3s push, 5-min worst case if a webhook drops.

============================================

PENDING UPGRADES (will change final architecture — DEFERRED until triggered)

Each item below is queued. Status: DEFERRED unless otherwise noted.

1. `notes` TEXT column on calls_log (column name LOCKED 2026-04-30)
   - Schema: ALTER TABLE calls_log ADD COLUMN notes TEXT
   - Extract: add `notes` field to ai-extract-schema (string, nullable, derived from transcript)
   - Prompt: add `<notes_capture>` section to v5.1 (or v5.3 successor)
   - Mapping: notes ← @Extract.response.notes in Update Data in Record
   - Impact: extends calls_log to 16 cols; adds free-form per-call note for dashboard call drilldown.

2. Sales-rep operational dashboard view + dummy mimic-accept (NO backend)
   - Surface: extend /dashboard/sales with a "claim load" / "mark contacted" mimic widget — UI-only, optimistic-update only, no Twin write.
   - Purpose: demo polish for the sales-rep persona; no real lifecycle change.

3. Real-time negotiation webhook (counter offer + final_floor visible to sales rep via SSE)
   - HR webhook: new `negotiation.counter` event from negotiate_rate sidecar firing mid-call.
   - FastAPI: POST /v1/events/negotiation-counter receiver — fans into the same event_bus.
   - Dashboard: sales-rep tab subscribes; surfaces live counter + final_floor chip during active calls.
   - Impact: extends Layer 3 push pipeline to a second event class; the sidecar's `final_floor` becomes briefly visible to broker staff (read-only — agent stays the only authority on the floor).

4. Super-test workflow (cheap LLM, 10 edge tests per node, then 10 live HR calls)
   - Owner: Andres / Claude.
   - Pattern: cheap LLM scripted scenarios per node (per Critical Rules → adversarial suites in HR), 10 edge tests each, gated before production publish; followed by 10 live HR calls.
   - Impact: production-publish gate; no schema or surface change.

5. Postgres migration (Tier-2 production)
   - Replaces HR Twin REST gateway with a managed Postgres instance.
   - Removes the HR API key from the dashboard read path entirely (FastAPI talks Postgres directly; HR keeps its own write path).
   - Rationale: ADR-008 + ADR-009 already minimize key exposure; full removal needs a Postgres backend. (Cite the master plan's Tier-2 production ladder, not memory.)
   - Impact: backend-only; FastAPI surface unchanged; caching layers preserved; eliminates the WAF-block edge cases noted under Cloudflare WAF.

6. Field renames
   - `pitched_loadboard_rate → original_rate` (legacy v14 calls_log column from a now-dropped path; cleanup)
   - `agreed_rate → apply_rate` (v14 → v15 alignment; book_load already writes `apply_rate`, so this is doc/grep cleanup more than schema)
   - Trigger: bundle with the notes column upgrade if both ship together.

7. Load-status lifecycle (`status`, `booked_at`, `booked_by_call_id` on loads)
   - Schema: ALTER TABLE loads ADD COLUMN status TEXT NOT NULL DEFAULT 'available'; ADD COLUMN booked_at TIMESTAMPTZ; ADD COLUMN booked_by_call_id TEXT
   - book_load: additionally UPDATE loads SET status='booked', booked_at=NOW(), booked_by_call_id=@call_id WHERE load_id=@load_id
   - query_loads: add `status equals 'available'` filter
   - Plus: cancellation flow + expired auto-flip (cron on `pickup_datetime < NOW()`)
   - Impact: prevents double-booking the same load across calls; enables accurate "available loads" counts on dashboard.

============================================

SPEC COMPLIANCE (FDE-TECHNICAL-CHALLENGE.md)

| Spec clause | Implementation | Status |
|---|---|---|
| Inbound use case via HappyRobot platform | Workflow `inbound-carrier-v19` | ✓ |
| Loads served from API in file or DB | HR Twin Postgres `loads` table (+ FastAPI /v1/loads/*) | ✓ |
| All required load fields | 18 cols incl. notes, num_of_pieces, miles, dimensions | ✓ |
| Get MC + verify via FMCSA API | verify_carrier tool → FMCSA mobile.fmcsa.dot.gov demo | ✓ |
| Search load + pitch | query_loads tool + v5.1 prompt pitch beat | ✓ |
| Up to 3 negotiation rounds | negotiate_rate + max_negotiation_rounds workflow var | ✓ |
| Mock transfer to sales rep | Transfer Popup + v5.1 sales-rep handoff line | ✓ |
| Extract relevant offer data | AI Extract (call_outcome, fmcsa_eligibility_failure_reason; +notes PENDING) | ✓ |
| Classify call outcome | Extract.call_outcome (5-class enum) | ✓ |
| Classify carrier sentiment | CHS.sentiment (3-class enum) | ✓ |
| Dashboard / metrics | Next.js 15 dashboard, 4 KPI tabs + 2 feeds + sales tab | ✓ |
| Docker | api/Dockerfile + dashboard Dockerfile | ✓ |
| HTTPS | Fly.io Let's Encrypt on both apps | ✓ |
| API key auth all endpoints | Header-only Bearer / x-api-key (ADR-008) | ✓ |
| Cloud deploy | Fly.io IAD (robot-api + robot-dashboard) | ✓ |

No clauses dropped. No unresolved drift from the spec.

============================================

OPEN ISSUES / DRIFT

- HR API key revocation pattern: rotated twice in one day. Background monitor at `scripts/monitor_hr_key.py` running 12 hr to detect future rotations; if it detects another revoke, manual rekey + Fly secret update needed.
- `mc_number` was NULL on calls prior to 2026-04-30 (verify_carrier @ picker mis-binding). User wired the fix on 2026-04-30. PENDING re-verification on next live Twin probe: `SELECT call_id, mc_number FROM calls_log WHERE created_at > '2026-04-30'` — every row should have non-NULL mc_number.
- v18 → v19 fork inheritance: any persistent_id reference inside a forked node config carries over verbatim. Re-check every @ picker on v19's Voice Agent + book_load + Update Data in Record nodes against the v18 snapshot before production publish (HR fork can preserve UUID references that no longer resolve cleanly under the new version).
- F11 (FMCSA API key in plaintext URL): PENDING Tier-2 security hardening; production publish doesn't gate on this.
- Live HR/Twin probe was NOT possible from this session; node-list comparison v19 vs v17/v18 should run on next opportunity.

============================================

INFRASTRUCTURE NOTES

- Two Fly apps: `robot-api-andres-morones` (FastAPI) + `robot-dashboard-andres-morones` (Next.js).
- `fly.toml`: persistent volume mount stripped (HR Twin owns persistence).
- `LOADS_CSV_PATH=/app/loads.csv`, baked into image at build time.
- `HAPPYROBOT_API_KEY` is the Twin REST gateway credential (NOT the API_BEARER_TOKEN). Postgres migration (PENDING #5) eliminates this from the dashboard read path.

============================================

CHANGE LOG

2026-04-30 — Refresh to v19 interim snapshot. Workflow advanced v17 → v18 → v19. Voice Agent Prompt v5.1 in repo + user v5.2 edits applied in HR (not all captured in repo). calls_log schema confirmed at 15 cols (intermediate_response_count + p70_intermediate_fired + p90_intermediate_fired added since v15 Phase C). bookings unchanged at 6 cols. mc_number @-picker fix landed. Background HR-key rotation monitor running. PENDING UPGRADES section added: notes column, sales-rep view + mimic-accept, real-time negotiation webhook, super-test, Postgres migration, field renames, load-status lifecycle.
2026-04-28 (PM) — Phase C delivery: Voice Agent Prompt v4.3 published. FastAPI surface 8 → 12 → 18+ endpoints. Pydantic models realigned. Caching layers shipped (ADR-007 + ADR-009). loads.csv refreshed to 150 rows. Repo root cleaned. Next.js scaffold landed. ADR-006 + ADR-007 + ADR-008 + ADR-009 + ADR-011 added.
2026-04-28 (PM, earlier) — v15 E2E verified (8 calls_log rows, 4 bookings, idempotency caught duplicate). ADR-005 (two-table booking pattern) accepted.
2026-04-28 (AM) — Step 6 redo: book_load Write-to-Twin child wired. Step 5: query_loads merge (load_id filter [corrected from reference_number]).
2026-04-28 — Step 4: negotiate_rate + calculate_rate verified.
2026-04-27 — Step 3: v4.2 prompt pasted. Steps 1–2: Twin schema migrations (calls_log cleanup + bookings creation). v15 architecture pivot locked.
